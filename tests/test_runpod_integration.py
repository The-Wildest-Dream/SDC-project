import json
from pathlib import Path
import importlib.util
import unittest
from decimal import Decimal
from unittest.mock import patch

import runpod_client
from price_model import predict_price as local_predict_price

_WORKER_PATH = Path(__file__).resolve().parents[1] / "runpod" / "handler.py"
_WORKER_SPEC = importlib.util.spec_from_file_location("runpod_price_worker", _WORKER_PATH)
_WORKER_MODULE = importlib.util.module_from_spec(_WORKER_SPEC)
_WORKER_SPEC.loader.exec_module(_WORKER_MODULE)
handler = _WORKER_MODULE.handler


SAMPLE = {
    "product": "P001",
    "currency": "CNY",
    "unit": "件",
    "quantity": 100,
    "cost": 50,
    "day": "2026-10-23",
}


class _FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload


class _RawResponse(_FakeResponse):
    def __init__(self, payload):
        self.payload = payload


class WorkerTests(unittest.TestCase):
    def test_worker_matches_existing_local_model(self):
        expected, _reason, _meta = local_predict_price(
            SAMPLE["product"], SAMPLE["currency"], SAMPLE["unit"],
            SAMPLE["quantity"], SAMPLE["cost"], SAMPLE["day"],
        )
        response = handler({"input": SAMPLE})
        self.assertEqual(response["prediction_status"], "available")
        self.assertAlmostEqual(response["prediction"], expected, places=10)
        self.assertIsNone(response["error_reason"])
        self.assertTrue(response["model_version"])

    def test_worker_preserves_model_fallback_reason(self):
        response = handler({"input": {**SAMPLE, "quantity": 100000}})
        self.assertEqual(response["prediction_status"], "unavailable")
        self.assertIsNone(response["prediction"])
        self.assertIn("超出", response["error_reason"])

    def test_worker_rejects_bad_payload(self):
        response = handler({"input": {"product": "P001"}})
        self.assertEqual(response["prediction_status"], "unavailable")
        self.assertIn("Missing required", response["error_reason"])

    def test_worker_supports_myr_model_group(self):
        payload = {
            "product": "P_MY_001",
            "currency": "MYR",
            "unit": "件",
            "quantity": 100,
            "cost": 22.1,
            "day": "2026-10-23",
        }
        response = handler({"input": payload})
        self.assertEqual(response["prediction_status"], "available")
        self.assertGreater(response["prediction"], 0)
        self.assertTrue(response["model_version"])


class ClientTests(unittest.TestCase):
    def _client(self, responses, **kwargs):
        sent = []

        def opener(request, timeout):
            sent.append((request, timeout))
            return _FakeResponse(responses.pop(0))

        result = runpod_client.predict_price(
            SAMPLE["product"], SAMPLE["currency"], SAMPLE["unit"],
            SAMPLE["quantity"], SAMPLE["cost"], SAMPLE["day"],
            env={
                "RUNPOD_API_KEY": "test-key",
                "RUNPOD_ENDPOINT_ID": "endpoint-test",
                "RUNPOD_TOTAL_TIMEOUT_SECONDS": "4",
                "RUNPOD_REQUEST_TIMEOUT_SECONDS": "2",
                "RUNPOD_POLL_INTERVAL_SECONDS": "0.01",
            },
            opener=opener,
            sleep=lambda _seconds: None,
            **kwargs,
        )
        return result, sent

    def test_client_handles_queue_then_completed(self):
        worker_output = handler({"input": SAMPLE})
        (value, _reason, meta), sent = self._client([
            {"id": "job-123", "status": "IN_QUEUE"},
            {"id": "job-123", "status": "COMPLETED", "output": worker_output},
        ], allow_local_fallback=False)
        self.assertAlmostEqual(value, worker_output["prediction"], places=10)
        self.assertEqual(meta["prediction_source"], "runpod")
        self.assertEqual(len(sent), 2)
        self.assertIn("/status/job-123", sent[1][0].full_url)
        self.assertEqual(sent[0][0].get_header("Authorization"), "Bearer test-key")

    def test_client_serializes_database_decimal_inputs(self):
        worker_output = handler({"input": SAMPLE})
        captured = {}

        def opener(request, timeout):
            captured.update(json.loads(request.data.decode("utf-8")))
            return _FakeResponse({
                "id": "job-decimal",
                "status": "COMPLETED",
                "output": worker_output,
            })

        value, _reason, meta = runpod_client.predict_price(
            SAMPLE["product"], SAMPLE["currency"], SAMPLE["unit"],
            Decimal("100"), Decimal("50"), SAMPLE["day"],
            env={
                "RUNPOD_API_KEY": "test-key",
                "RUNPOD_ENDPOINT_ID": "endpoint-test",
            },
            allow_local_fallback=False,
            opener=opener,
        )
        self.assertAlmostEqual(value, worker_output["prediction"], places=10)
        self.assertEqual(meta["prediction_source"], "runpod")
        self.assertEqual(captured["input"]["quantity"], 100.0)
        self.assertEqual(captured["input"]["cost"], 50.0)

    def test_client_uses_explicit_local_fallback_on_missing_config(self):
        value, _reason, meta = runpod_client.predict_price(
            SAMPLE["product"], SAMPLE["currency"], SAMPLE["unit"],
            SAMPLE["quantity"], SAMPLE["cost"], SAMPLE["day"],
            env={},
        )
        expected, _expected_reason, _expected_meta = local_predict_price(
            SAMPLE["product"], SAMPLE["currency"], SAMPLE["unit"],
            SAMPLE["quantity"], SAMPLE["cost"], SAMPLE["day"],
        )
        self.assertAlmostEqual(value, expected, places=10)
        self.assertEqual(meta["prediction_source"], "local_fallback")
        self.assertIn("runpod_error", meta)

    def test_client_can_disable_local_fallback(self):
        value, _reason, meta = runpod_client.predict_price(
            SAMPLE["product"], SAMPLE["currency"], SAMPLE["unit"],
            SAMPLE["quantity"], SAMPLE["cost"], SAMPLE["day"],
            env={}, allow_local_fallback=False,
        )
        self.assertIsNone(value)
        self.assertEqual(meta["prediction_source"], "unavailable")

    def test_unavailable_local_fallback_is_not_mislabeled(self):
        with patch("price_model.predict_price", return_value=(None, "not applicable", None)):
            value, _reason, meta = runpod_client.predict_price(
                SAMPLE["product"], SAMPLE["currency"], SAMPLE["unit"],
                SAMPLE["quantity"], SAMPLE["cost"], SAMPLE["day"],
                env={},
            )
        self.assertIsNone(value)
        self.assertEqual(meta["prediction_source"], "unavailable")

    def test_client_falls_back_after_worker_failure(self):
        (value, _reason, meta), _sent = self._client(
            [{"id": "job-123", "status": "FAILED"}],
            allow_local_fallback=True,
        )
        self.assertIsNotNone(value)
        self.assertEqual(meta["prediction_source"], "local_fallback")
        self.assertIn("FAILED", meta["runpod_error"])

    def test_client_rejects_malformed_worker_output(self):
        (value, _reason, meta), _sent = self._client(
            [
                {"id": "job-123", "status": "COMPLETED",
                 "output": {"prediction_status": "available", "prediction": "not-a-number"}},
            ],
            allow_local_fallback=False,
        )
        self.assertIsNone(value)
        self.assertEqual(meta["prediction_source"], "unavailable")

    def test_client_reports_wait_timeout(self):
        response = _FakeResponse({"id": "job-123", "status": "IN_QUEUE"})

        def opener(_request, timeout):
            return response

        clock = iter([0.0, 0.1, 0.1, 1.1])
        with patch("runpod_client.time.monotonic", side_effect=lambda: next(clock)):
            with self.assertRaisesRegex(runpod_client.RunPodRequestError, "wait timeout"):
                runpod_client._submit_and_wait(
                    SAMPLE,
                    "test-key",
                    "endpoint-test",
                    total_timeout=1,
                    request_timeout=2,
                    poll_interval=0.1,
                    opener=opener,
                    sleep=lambda _seconds: None,
                )

    def test_client_rejects_malformed_json_response(self):
        with self.assertRaisesRegex(runpod_client.RunPodRequestError, "malformed JSON"):
            runpod_client._request_json(
                "https://example.invalid",
                "test-key",
                opener=lambda *_args, **_kwargs: _RawResponse(b"not-json"),
            )


if __name__ == "__main__":
    unittest.main()
