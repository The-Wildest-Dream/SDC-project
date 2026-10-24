import json
import unittest
from decimal import Decimal
from unittest.mock import patch

from finance_rules import apply_funding, funding
from i18n import display_error
from quotation_rules import COSTS, calculate


def base_result():
    return calculate(
        Decimal("100"),
        dict(zip(COSTS, ["30", "15", "5", "800", "200"])),
        Decimal("10"),
        Decimal("20"),
    )


def finance_result(prepayment="30", term_days=30, annual_rate="8"):
    result = base_result()
    return funding(
        result["unit_cost"], Decimal("100"), Decimal("10"), Decimal("20"),
        Decimal(prepayment), term_days, Decimal(annual_rate),
    )


class FinanceRulesTests(unittest.TestCase):
    def test_fresh_decimal_finance_values_are_applied(self):
        result = base_result()
        finance = finance_result()
        self.assertIsInstance(result["unit_cost"], Decimal)
        self.assertIsInstance(finance["funding_unit"], Decimal)

        adjusted = apply_funding(result, finance)
        self.assertEqual(adjusted["unit_cost"], result["unit_cost"] + finance["funding_unit"])
        self.assertEqual(adjusted["floor"], adjusted["unit_cost"] / Decimal("0.9"))
        self.assertEqual(adjusted["target"], adjusted["unit_cost"] / Decimal("0.8"))

    def test_json_roundtrip_string_amounts_are_normalized(self):
        result = base_result()
        persisted = json.loads(json.dumps(finance_result(), default=str))
        self.assertIsInstance(persisted["funding_unit"], str)

        adjusted = apply_funding(result, persisted)
        self.assertIsInstance(adjusted["unit_cost"], Decimal)
        self.assertEqual(
            adjusted["unit_cost"],
            result["unit_cost"] + Decimal(persisted["funding_unit"]),
        )

    def test_zero_funding_cost_is_valid_and_does_not_change_unit_cost(self):
        result = base_result()
        finance = finance_result(prepayment="100", term_days=0, annual_rate="0")
        adjusted = apply_funding(result, finance)
        self.assertEqual(finance["funding_cost"], Decimal(0))
        self.assertEqual(finance["funding_unit"], Decimal(0))
        self.assertEqual(adjusted["unit_cost"], result["unit_cost"])

    def test_invalid_or_missing_amount_is_not_silently_replaced_with_zero(self):
        finance = finance_result()
        finance["funding_unit"] = "not-a-number"
        with self.assertRaisesRegex(ValueError, "funding_unit"):
            apply_funding(base_result(), finance)

        finance = finance_result()
        del finance["funding_cost"]
        with self.assertRaisesRegex(ValueError, "funding_cost"):
            apply_funding(base_result(), finance)

    def test_empty_finance_object_is_not_treated_as_no_financing(self):
        with self.assertRaisesRegex(ValueError, "缺少字段"):
            apply_funding(base_result(), {})

    def test_missing_costs_still_report_bad_persisted_finance(self):
        result = calculate(100, dict(zip(COSTS, ["", "15", "5", "0", "0"])), 10, 20)
        finance = finance_result()
        finance["funding_unit"] = "bad"
        with self.assertRaisesRegex(ValueError, "funding_unit"):
            apply_funding(result, finance)

    def test_finance_errors_are_localized_without_exposing_internal_field_names(self):
        for lang in ("zh-CN", "en", "ms-MY"):
            with self.subTest(language=lang), patch("i18n.language", return_value=lang):
                message = display_error(ValueError("资金占用计算字段无效：funding_unit。"))
                self.assertTrue(message)
                self.assertNotIn("funding_unit", message)
                missing = display_error(ValueError("资金占用计算数据不完整，缺少字段：funding_unit。"))
                self.assertNotIn("funding_unit", missing)


if __name__ == "__main__":
    unittest.main()
