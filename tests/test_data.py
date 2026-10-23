import unittest
from copy import deepcopy
from datetime import date
from data_service import csv_bytes, prepare_import, payment_summary, comparable_transactions
from generate_data import generate


class DataTests(unittest.TestCase):
    def setUp(self):
        self.data = generate()

    def test_repeatability(self):
        self.assertEqual(self.data, generate())
        self.assertEqual(len(self.data["历史交易"]), 300)

    def test_invalid_import_atomic(self):
        before = deepcopy(self.data)
        rows = deepcopy(self.data["历史交易"])
        rows[0]["数量"] = 0
        rows[1]["成交单价"] = -1
        rows[2]["订单ID"] = rows[3]["订单ID"]
        rows[4]["订单日期"] = "2026-02-30"
        result, errors = prepare_import(self.data, {"历史交易": csv_bytes("历史交易", rows)})
        self.assertIsNone(result)
        self.assertGreaterEqual(len(errors), 4)
        self.assertEqual(self.data, before)
        self.assertTrue(all("行号" in e and "字段" in e for e in errors))

    def test_foreign_keys_and_units(self):
        for field, value in [("产品ID", "missing"), ("客户ID", "missing"), ("单位", "吨"), ("币种", "USD")]:
            rows = deepcopy(self.data["历史交易"])
            rows[0][field] = value
            result, errors = prepare_import(self.data, {"历史交易": csv_bytes("历史交易", rows)})
            self.assertIsNone(result)
            self.assertEqual(errors[0]["字段"], field)

    def test_required_and_numeric(self):
        result, errors = prepare_import(self.data, {"客户": b"bad\n1\n"})
        self.assertIsNone(result)
        self.assertEqual(errors[0]["行号"], 1)
        for value in ("NaN", "inf", "abc", ""):
            rows = deepcopy(self.data["库存"])
            rows[0]["现有数量"] = value
            self.assertTrue(prepare_import(self.data, {"库存": csv_bytes("库存", rows)})[1])

    def test_parent_removal_rejected(self):
        result, errors = prepare_import(self.data, {"产品": csv_bytes("产品", self.data["产品"][1:])})
        self.assertIsNone(result)
        self.assertTrue(errors)

    def test_payment_cutoff(self):
        customer = self.data["客户"][0]
        row = deepcopy(self.data["历史交易"][0])
        row.update({"客户ID": customer["客户ID"], "订单日期": "2026-01-01",
                    "约定付款日期": "2026-02-01"})
        bundle = {"客户": [customer], "历史交易": [
            {**row, "订单ID": "1", "实际付款日期": "2026-02-01"},
            {**row, "订单ID": "2", "实际付款日期": "2026-02-04"},
            {**row, "订单ID": "3", "实际付款日期": ""},
            {**row, "订单ID": "4", "实际付款日期": "2026-03-01"},
        ]}
        summary, details = payment_summary(bundle, date(2026, 2, 10))
        self.assertEqual(summary[0]["已到期订单数"], 4)
        self.assertEqual(summary[0]["按时付款率"], "25.0%")
        self.assertEqual(summary[0]["当前逾期未付订单数"], 2)
        self.assertEqual(summary[0]["历史逾期天数（累计）"], 3)
        self.assertEqual(details[2]["当前逾期未付天数"], 9)

    def test_comparison_group(self):
        rows = comparable_transactions(self.data, "P001")
        self.assertTrue(rows)
        self.assertTrue(all(r["产品ID"] == "P001" and r["币种"] == "CNY" and r["单位"] == "件" for r in rows))
