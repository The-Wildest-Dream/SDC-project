"""RunPod client used by the Streamlit historical price prediction page."""
from __future__ import annotations

import json
import math
import os
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_BASE = "https://api.runpod.ai/v2"
_WAITING_STATUSES = {"IN_QUEUE", "IN_PROGRESS", "INITIALIZING"}
_TERMINAL_FAILURE_STATUSES = {"FAILED", "TIMED_OUT", "CANCELLED"}
_COMPLETED_STATUSES = {"COMPLETED"}


class RunPodRequestError(RuntimeError):
    """Safe-to-display RunPod transport or response error."""


def _positive_float(env: dict[str, str], key: str, default: float) -> float:
    try:
        result = float(env.get(key, default))
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) and result > 0 else default


def _request_json(
    url: str,
    api_key: str,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    timeout: float = 30,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request = Request(
        url,
        data=payload,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with opener(request, timeout=timeout) as response:
            raw = response.read()
    except HTTPError as exc:
        # Do not pass provider response bodies into logs or user-facing errors.
        raise RunPodRequestError(f"RunPod returned HTTP {exc.code}") from None
    except (URLError, TimeoutError, OSError) as exc:
        raise RunPodRequestError(f"RunPod request failed ({type(exc).__name__})") from None

    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise RunPodRequestError("RunPod returned malformed JSON") from None
    if not isinstance(parsed, dict):
        raise RunPodRequestError("RunPod response must be a JSON object")
    return parsed


def _submit_and_wait(
    inputs: dict[str, Any],
    api_key: str,
    endpoint_id: str,
    *,
    total_timeout: float,
    request_timeout: float,
    poll_interval: float,
    opener: Callable[..., Any] = urlopen,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    base = f"{API_BASE}/{endpoint_id}"
    submitted = _request_json(
        f"{base}/run",
        api_key,
        method="POST",
        body={"input": inputs},
        timeout=request_timeout,
        opener=opener,
    )
    job_id = submitted.get("id")
    status = str(submitted.get("status", "")).upper()
    if status in _COMPLETED_STATUSES:
        result = submitted.get("output")
        if isinstance(result, dict):
            return result
        raise RunPodRequestError("RunPod completed without a valid output object")
    if status in _TERMINAL_FAILURE_STATUSES:
        raise RunPodRequestError(f"RunPod job ended with status {status}")
    if not isinstance(job_id, str) or not job_id.strip():
        raise RunPodRequestError("RunPod response did not include a valid job ID")

    deadline = time.monotonic() + total_timeout
    while time.monotonic() < deadline:
        sleep(min(poll_interval, max(0.0, deadline - time.monotonic())))
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        status_response = _request_json(
            f"{base}/status/{job_id}",
            api_key,
            timeout=min(request_timeout, remaining),
            opener=opener,
        )
        status = str(status_response.get("status", "")).upper()
        if status in _COMPLETED_STATUSES:
            result = status_response.get("output")
            if isinstance(result, dict):
                return result
            raise RunPodRequestError("RunPod completed without a valid output object")
        if status in _TERMINAL_FAILURE_STATUSES:
            raise RunPodRequestError(f"RunPod job ended with status {status}")
        if status not in _WAITING_STATUSES:
            raise RunPodRequestError("RunPod returned an unknown job status")

    raise RunPodRequestError("RunPod job exceeded the configured wait timeout")


def _local_result(
    args: tuple[Any, ...],
    *,
    runpod_error: str | None = None,
) -> tuple[float | None, str, dict[str, Any]]:
    from price_model import predict_price as local_predict_price

    value, reason, metadata = local_predict_price(*args)
    result_metadata = dict(metadata or {})
    result_metadata["prediction_source"] = (
        "local_fallback" if value is not None else "unavailable"
    )
    if runpod_error:
        result_metadata["runpod_error"] = runpod_error
    return value, reason, result_metadata


def _normalize_worker_result(
    result: dict[str, Any],
) -> tuple[float | None, str, dict[str, Any]]:
    raw_metadata = result.get("metadata")
    metadata = dict(raw_metadata) if isinstance(raw_metadata, dict) else {}
    metadata["prediction_source"] = "runpod"
    if result.get("prediction_status") != "available":
        reason = result.get("error_reason") or result.get("reason") or "RunPod prediction unavailable"
        return None, str(reason), metadata
    try:
        prediction = float(result["prediction"])
    except (KeyError, TypeError, ValueError, OverflowError):
        raise RunPodRequestError("RunPod output is missing a numeric prediction") from None
    if not math.isfinite(prediction) or prediction <= 0:
        raise RunPodRequestError("RunPod output contains an invalid prediction")
    if result.get("model_version") and not metadata.get("data_version"):
        metadata["data_version"] = result["model_version"]
    return prediction, str(result.get("reason") or ""), metadata


def predict_price(
    product: str,
    currency: str,
    unit: str,
    quantity: float,
    cost: float,
    day: str,
    *,
    allow_local_fallback: bool = True,
    env: dict[str, str] | None = None,
    opener: Callable[..., Any] = urlopen,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[float | None, str, dict[str, Any]]:
    """Predict via RunPod while keeping the existing app's 3-item return shape.

    Environment:
      RUNPOD_API_KEY, RUNPOD_ENDPOINT_ID
      RUNPOD_TOTAL_TIMEOUT_SECONDS (default 180)
      RUNPOD_REQUEST_TIMEOUT_SECONDS (default 30)
      RUNPOD_POLL_INTERVAL_SECONDS (default 2)
    """
    config = os.environ if env is None else env
    try:
        model_quantity = float(quantity)
        model_cost = float(cost)
    except (TypeError, ValueError, OverflowError):
        error = "RunPod prediction inputs must contain numeric quantity and cost"
        if allow_local_fallback:
            return _local_result(
                (product, currency, unit, quantity, cost, day), runpod_error=error
            )
        return None, error, {"prediction_source": "unavailable"}

    inputs = {
        "product": product,
        "currency": currency,
        "unit": unit,
        "quantity": model_quantity,
        "cost": model_cost,
        "day": str(day)[:10],
    }
    api_key = config.get("RUNPOD_API_KEY", "").strip()
    endpoint_id = config.get("RUNPOD_ENDPOINT_ID", "").strip()
    if not api_key or not endpoint_id:
        error = "RunPod is not configured: required environment settings are missing"
        if allow_local_fallback:
            return _local_result(
                (product, currency, unit, quantity, cost, day), runpod_error=error
            )
        return None, error, {"prediction_source": "unavailable"}

    try:
        worker_result = _submit_and_wait(
            inputs,
            api_key,
            endpoint_id,
            total_timeout=_positive_float(config, "RUNPOD_TOTAL_TIMEOUT_SECONDS", 180),
            request_timeout=_positive_float(config, "RUNPOD_REQUEST_TIMEOUT_SECONDS", 30),
            poll_interval=_positive_float(config, "RUNPOD_POLL_INTERVAL_SECONDS", 2),
            opener=opener,
            sleep=sleep,
        )
        value, reason, metadata = _normalize_worker_result(worker_result)
        if value is not None:
            return value, reason, metadata
        error = reason
    except RunPodRequestError as exc:
        error = str(exc)

    if allow_local_fallback:
        return _local_result(
            (product, currency, unit, quantity, cost, day), runpod_error=error
        )
    return None, error, {"prediction_source": "unavailable", "runpod_error": error}
