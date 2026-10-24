"""RunPod Serverless adapter for the project's existing trusted price model."""
from __future__ import annotations

from datetime import date
import math
from pathlib import Path
import sys
from typing import Any


# The image installs the project inference module next to this worker package.
APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from price_model import MODEL_DIR, load_bundle, predict_price  # noqa: E402


def _preload_trusted_model() -> None:
    """Warm the same cache used by predict_price before accepting jobs."""
    model_path = MODEL_DIR / "model.joblib"
    if not model_path.is_file():
        return
    try:
        load_bundle(str(model_path), model_path.stat().st_mtime_ns)
    except Exception:
        # Keep the worker available to return the model module's normal fallback
        # reason rather than failing startup when the artifact is absent/bad.
        return


_preload_trusted_model()

_REQUIRED_FIELDS = ("product", "currency", "unit", "quantity", "cost", "day")


def _unavailable(reason: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "prediction": None,
        "prediction_status": "unavailable",
        "model_version": (metadata or {}).get("data_version"),
        "error_reason": reason,
        "reason": reason,
        "metadata": metadata,
    }


def handler(job: dict[str, Any]) -> dict[str, Any]:
    """Handle one RunPod job and return a JSON-serializable prediction result."""
    job_input = job.get("input", {}) if isinstance(job, dict) else {}
    if not isinstance(job_input, dict):
        return _unavailable("input must be a JSON object")

    missing = [field for field in _REQUIRED_FIELDS if field not in job_input]
    if missing:
        return _unavailable(f"Missing required input fields: {', '.join(missing)}")

    try:
        quantity = float(job_input["quantity"])
        cost = float(job_input["cost"])
        if not math.isfinite(quantity) or not math.isfinite(cost):
            return _unavailable("quantity and cost must be finite numbers")
        # Validate ISO date shape here for a clear API response.
        prediction_day = date.fromisoformat(str(job_input["day"])[:10]).isoformat()
        product = str(job_input["product"])
        currency = str(job_input["currency"])
        unit = str(job_input["unit"])
        if not all((product, currency, unit)):
            return _unavailable("product, currency, and unit must be non-empty")
    except (TypeError, ValueError, OverflowError):
        return _unavailable("quantity, cost, or day has an invalid value")

    value, reason, metadata = predict_price(
        product, currency, unit, quantity, cost, prediction_day
    )
    if value is None:
        return _unavailable(reason, metadata)

    try:
        value = float(value)
        if not math.isfinite(value) or value <= 0:
            return _unavailable("Model returned a non-positive or non-finite prediction", metadata)
    except (TypeError, ValueError, OverflowError):
        return _unavailable("Model returned a malformed prediction", metadata)

    return {
        "prediction": value,
        "prediction_status": "available",
        "model_version": (metadata or {}).get("data_version"),
        "error_reason": None,
        "reason": reason,
        "metadata": metadata,
    }


if __name__ == "__main__":
    import runpod

    runpod.serverless.start({"handler": handler})
