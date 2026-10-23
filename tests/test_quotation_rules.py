import unittest
from quotation_rules import COSTS, calculate, check_price, percentile


class RuleTests(unittest.TestCase):
    def test_prices(self):
        r = calculate(100, dict(zip(COSTS, ["30", "15", "5", "800", "200"])), 10, 20)
        self.assertEqual(r["unit_cost"], 60)
        self.assertEqual(r["target"], 75)
        with self.assertRaises(ValueError):
            check_price(r, "66.66")
        self.assertEqual(check_price(r, "75"), 75)

    def test_missing(self):
        r = calculate(100, dict(zip(COSTS, ["", "15", "5", "0", "0"])), 10, 20)
        self.assertEqual(r["missing"], [COSTS[0]])
        with self.assertRaises(ValueError):
            check_price(r, 999)

    def test_margins(self):
        for minimum, target in [(30, 20), (0, 100), (-1, 20)]:
            with self.assertRaises(ValueError):
                calculate(1, dict.fromkeys(COSTS, "0"), minimum, target)

    def test_percentile(self):
        self.assertEqual(percentile([10, 20, 30, 40], .5), 25)
        self.assertEqual(str(percentile([10, 20, 30, 40], .25)), "17.50")
        self.assertIsNone(percentile([], .5))
