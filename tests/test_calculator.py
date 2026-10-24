"""Regression tests for calculation logic, independent of Streamlit pages."""
import unittest
from decimal import Decimal

from calculator import calculate_quote


class CalculatorTests(unittest.TestCase):
    def test_demo(self):
        result = calculate_quote(100, 30, 15, 5, 800, 200, 20)
        self.assertEqual(result["unit_cost"], Decimal("60"))
        self.assertEqual(result["unit_price"], Decimal("75"))
        self.assertEqual(result["total"], Decimal("7500"))

    def test_invalid_inputs(self):
        for quantity, margin in [(0, 20), (-1, 20), (1.5, 20),
                                 (100, 100), (100, 101), (100, -1)]:
            with self.subTest(quantity=quantity, margin=margin):
                with self.assertRaises(ValueError):
                    calculate_quote(quantity, 30, 15, 5, 800, 200, margin)

    def test_negative_cost(self):
        with self.assertRaises(ValueError):
            calculate_quote(100, -1, 15, 5, 800, 200, 20)

    def test_zero_margin_and_cost(self):
        result = calculate_quote(1, 0, 0, 0, 0, 0, 0)
        self.assertEqual(result["total"], 0)

    def test_no_early_rounding(self):
        result = calculate_quote(3, 0, 0, 0, 1, 0, 0)
        self.assertNotEqual(result["unit_price"], Decimal("0.33"))
        self.assertAlmostEqual(result["total"], Decimal("1"))


if __name__ == "__main__":
    unittest.main()
