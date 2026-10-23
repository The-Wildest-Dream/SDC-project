import unittest
from datetime import date, timedelta
from unittest.mock import patch
from pathlib import Path
import tempfile
import json
from price_model import FEATURES, MODEL_DIR, features, predict_price


class ModelTests(unittest.TestCase):
    def test_features_allowlist(self):
        self.assertEqual(set(features(100, 50, "2026-10-23")), set(FEATURES))
        self.assertEqual(len(FEATURES), 4)

    def test_temporal_evaluation(self):
        meta = json.loads((MODEL_DIR / "evaluation.json").read_text())
        for info in meta["groups"].values():
            if info["status"] == "已训练":
                self.assertLess(info["train_end"], info["test_start"])
                self.assertGreaterEqual(info["train_count"], 20)
                self.assertGreaterEqual(info["test_count"], 5)
                self.assertGreaterEqual(info["baseline_mae"], 0)
                self.assertGreaterEqual(info["model_mae"], 0)

    def test_in_scope_and_fallbacks(self):
        self.assertIsNotNone(predict_price("P001", "CNY", "件", 100, 50, "2026-10-23")[0])
        for args in [
            ("unknown", "CNY", "件", 100, 50, "2026-10-23"),
            ("P001", "USD", "件", 100, 50, "2026-10-23"),
            ("P001", "CNY", "件", 100000, 50, "2026-10-23"),
            ("P001", "CNY", "件", 100, 99999, "2026-10-23"),
            ("P001", "CNY", "件", 100, 50, "2030-01-01"),
        ]:
            self.assertIsNone(predict_price(*args)[0])
        with tempfile.TemporaryDirectory() as d, patch("price_model.MODEL_DIR", Path(d)):
            value, reason, _ = predict_price("P001", "CNY", "件", 100, 50, "2026-10-23")
            self.assertIsNone(value)
            self.assertIn("缺失", reason)
