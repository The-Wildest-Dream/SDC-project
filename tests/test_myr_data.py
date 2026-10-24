import json
import unittest
from pathlib import Path
from unittest.mock import patch

from data_service import SCHEMAS, comparable_transactions, parse_csv, prepare_import, csv_bytes
from generate_data import generate as generate_cny
from generate_myr_data import AS_OF, SEED, generate as generate_myr
from price_model import MODEL_DIR, predict_price
from quotation_rules import COSTS, calculate


ROOT = Path(__file__).resolve().parents[1]
MYR_CSV_DIR = ROOT / "sample_data"


class MYRSyntheticDataTests(unittest.TestCase):
    def test_generator_is_repeatable_and_has_isolated_references(self):
        bundle = generate_myr()
        self.assertEqual(bundle, generate_myr())
        self.assertEqual(SEED, 20261024)
        self.assertEqual(
            {kind: len(rows) for kind, rows in bundle.items()},
            {"产品": 4, "客户": 6, "历史交易": 320, "库存": 4},
        )
        self.assertTrue(all(product["币种"] == "MYR" for product in bundle["产品"]))
        self.assertTrue(all(row["币种"] == "MYR" for row in bundle["历史交易"]))
        self.assertTrue(
            {row["产品ID"] for row in bundle["产品"]}.isdisjoint(
                {row["产品ID"] for row in generate_cny()["产品"]}
            )
        )
        self.assertTrue(
            {row["客户ID"] for row in bundle["客户"]}.isdisjoint(
                {row["客户ID"] for row in generate_cny()["客户"]}
            )
        )

    def test_four_review_csvs_parse_and_validate_without_database(self):
        myr = {}
        for kind in SCHEMAS:
            path = MYR_CSV_DIR / f"MYR_模拟数据_{kind}.csv"
            self.assertTrue(path.is_file(), path)
            rows, errors = parse_csv(kind, path.read_bytes())
            self.assertEqual(errors, [])
            self.assertTrue(rows)
            myr[kind] = [{field: row[field] for field in SCHEMAS[kind]} for row in rows]

        cny = generate_cny()
        valid, errors = prepare_import(
            cny,
            {kind: csv_bytes(kind, rows) for kind, rows in myr.items()},
        )
        self.assertEqual(errors, [])
        self.assertIsNotNone(valid)
        self.assertEqual(len(valid["历史交易"]), 320)
        self.assertTrue(all(row["币种"] == "MYR" for row in valid["历史交易"]))

    def test_comparison_groups_never_mix_cny_and_myr(self):
        cny, myr = generate_cny(), generate_myr()
        bundle = {
            kind: [*cny[kind], *myr[kind]]
            for kind in SCHEMAS
        }
        myr_rows = comparable_transactions(bundle, "P_MY_001")
        cny_rows = comparable_transactions(bundle, "P001")
        self.assertEqual(len(myr_rows), 80)
        self.assertTrue(all(row["币种"] == "MYR" for row in myr_rows))
        self.assertTrue(all(row["币种"] == "CNY" for row in cny_rows))

    def test_model_supports_each_myr_product_and_existing_cny(self):
        evaluation = json.loads((MODEL_DIR / "evaluation.json").read_text("utf-8"))
        for product, quantity in zip(generate_myr()["产品"], (100, 300, 150, 80)):
            production_cost = sum(
                product[field]
                for field in ("单位材料成本", "单位人工成本", "单位制造费用")
            )
            value, _reason, _metadata = predict_price(
                product["产品ID"], "MYR", product["单位"], quantity,
                production_cost, AS_OF.isoformat(),
            )
            self.assertIsNotNone(value, product["产品ID"])
            key = json.dumps(
                [product["产品ID"], "MYR", product["单位"]],
                ensure_ascii=False,
            )
            self.assertEqual(evaluation["groups"][key]["status"], "已训练")
            self.assertGreaterEqual(evaluation["groups"][key]["train_count"], 20)
            self.assertGreaterEqual(evaluation["groups"][key]["test_count"], 5)

        for product in generate_cny()["产品"]:
            production_cost = sum(
                product[field]
                for field in ("单位材料成本", "单位人工成本", "单位制造费用")
            )
            value, _reason, _metadata = predict_price(
                product["产品ID"], "CNY", product["单位"], 100,
                production_cost, "2026-10-23",
            )
            self.assertIsNotNone(value, product["产品ID"])
        self.assertIsNone(
            predict_price("P_MY_001", "CNY", "件", 100, 22.1, "2026-10-23")[0]
        )

    def test_myr_cost_calculation_and_export_keep_currency_without_conversion(self):
        costs = dict(zip(COSTS, ["12.4", "6.2", "3.5", "0", "0"]))
        result = calculate(100, costs, 20, 30)
        self.assertEqual(str(result["unit_cost"]), "22.1")
        self.assertEqual(str(result["floor"]), "27.625")
        self.assertEqual(str(result["target"]), "31.57142857142857142857142857")

        import quote_exports

        row = {
            "id": "Q-MYR-DEMO",
            "inquiry_id": "I-MYR-DEMO",
            "version": 1,
            "status": "approved",
            "payload": {
                "price": "31.58",
                "quantity": "100",
                "customer_name": "模拟 Seri Maju Engineering Sdn. Bhd.",
                "product_name": "模拟MYR CNC铝制安装支架",
                "unit": "件",
                "currency": "MYR",
                "valid_until": AS_OF.isoformat(),
                "delivery_date": AS_OF.isoformat(),
                "snapshot": {"terms": {}},
            },
        }
        with (
            patch("quote_exports.field_label", side_effect=lambda value: value),
            patch("quote_exports.status_label", side_effect=lambda value: value),
            patch("quote_exports.t", side_effect=lambda key, **kwargs: kwargs.get("status", key)),
            patch("quote_exports.language", return_value="zh-CN"),
        ):
            exported_fields = quote_exports.fields(row)
            csv_text = quote_exports.csv_export(row).decode("utf-8-sig")
            html_text = quote_exports.html_export(row).decode("utf-8")
        self.assertEqual(exported_fields["币种"], "MYR")
        self.assertIn("MYR", csv_text)
        self.assertIn("MYR", html_text)


if __name__ == "__main__":
    unittest.main()
