import unittest
from pathlib import Path
import sys
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import i18n
import quote_exports
from quotation_rules import calculate


class LocalizationTests(unittest.TestCase):
    def test_catalogues_and_interpolation_are_consistent(self):
        self.assertEqual(i18n.validate_catalogues(), {})
        for locale, expected in (
            ("zh-CN", "中小制造企业报价辅助系统"),
            ("en", "Quotation Assistant for Small and Medium Manufacturers"),
            ("ms-MY", "Pembantu Sebut Harga untuk Pengilang Kecil dan Sederhana"),
        ):
            self.assertEqual(i18n.translate("app.title", lang=locale), expected)
            rendered = i18n.translate("data.current_count.other", lang=locale, count=3)
            self.assertIn("3", rendered)

    def test_myr_currency_validation_message_is_localized(self):
        reason = "仅支持 CNY、USD、EUR、MYR，不自动换汇"
        for locale in ("zh-CN", "en", "ms-MY"):
            with patch.object(i18n, "language", return_value=locale):
                self.assertEqual(
                    i18n._validation_reason(reason),
                    i18n.translate("data.error.currency", lang=locale),
                )

    def test_pluralization_and_display_formatting(self):
        self.assertEqual(i18n.t_plural("data.current_count", 1, lang="en"), "1 valid record")
        self.assertEqual(i18n.t_plural("data.current_count", 2, lang="en"), "2 valid records")
        self.assertEqual(i18n.t_plural("data.current_count", 2, lang="ms-MY"), "2 rekod sah")
        self.assertEqual(i18n.format_number("1234.5", 2, lang="en"), "1,234.50")
        self.assertEqual(i18n.format_date("2026-10-24", lang="zh-CN"), "2026-10-24")
        self.assertEqual(i18n.format_date("2026-10-24", lang="en"), "24 Oct 2026")
        self.assertEqual(i18n.format_date("2026-10-24", lang="ms-MY"), "24 Okt 2026")

    def test_missing_translation_falls_back_without_exposing_key(self):
        for locale in ("zh-CN", "en", "ms-MY"):
            rendered = i18n.translate("unknown.translation.key", lang=locale)
            fallback = i18n.translate("i18n.missing", lang=locale)
            self.assertEqual(rendered, fallback)
            self.assertNotIn("unknown.translation.key", rendered)

    def test_language_switch_preserves_widget_state_and_is_session_scoped(self):
        source = """
import streamlit as st
from i18n import LANGS, t
st.selectbox("Language", LANGS, key="ui_language")
st.text_input("Draft text", key="draft_text")
st.info(t("app.title"))
"""
        first = AppTest.from_string(source).run()
        second = AppTest.from_string(source).run()

        first.text_input(key="draft_text").set_value("unsaved draft text")
        first.run()
        first.selectbox(key="ui_language").select("en")
        first.run()

        self.assertEqual(first.session_state["ui_language"], "en")
        self.assertEqual(first.session_state["draft_text"], "unsaved draft text")
        self.assertEqual(first.info[0].value, i18n.translate("app.title", lang="en"))
        self.assertEqual(second.session_state["ui_language"], "zh-CN")

    def test_calculation_is_independent_of_selected_locale(self):
        costs = {
            "单位材料成本": "10", "单位人工成本": "2", "单位制造费用": "3",
            "整批固定费用": "100", "卖方承担的整批物流费用": "50",
        }
        results = [
            calculate("25", costs, "10", "20")
            for _locale in ("zh-CN", "en", "ms-MY")
        ]
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[1], results[2])

    def test_customer_quote_exports_use_selected_language(self):
        row = {
            "id": "QUO-DEMO",
            "inquiry_id": "INQ-DEMO",
            "version": 1,
            "status": "approved",
            "payload": {
                "customer_name": "Example Customer",
                "product_name": "Example Product",
                "quantity": "2",
                "unit": "pcs",
                "currency": "USD",
                "price": "12.50",
                "valid_until": "2026-10-31",
                "delivery_date": "2026-10-30",
                "snapshot": {"terms": {"prepayment_pct": 30, "term_days": 30, "annual_rate_pct": 8}},
            },
        }
        field_keys = i18n.FIELD_KEYS
        status_keys = i18n.STATUS_KEYS
        for locale, html_lang, expected_title, expected_csv_header in (
            ("en", "en", "Quotation", "Quote ID"),
            ("ms-MY", "ms-MY", "Sebut Harga", "ID sebut harga"),
        ):
            with (
                patch.object(quote_exports, "language", return_value=locale),
                patch.object(quote_exports, "t", side_effect=lambda key, _lang=locale, **values:
                             i18n.translate(key, lang=_lang, **values)),
                patch.object(quote_exports, "field_label", side_effect=lambda field, _lang=locale:
                             i18n.translate(field_keys[field], lang=_lang)),
                patch.object(quote_exports, "status_label", side_effect=lambda status, _lang=locale:
                             i18n.translate(status_keys[status], lang=_lang)),
                patch.object(quote_exports, "format_date", side_effect=lambda value, _lang=locale:
                             i18n.format_date(value, lang=_lang)),
                patch.object(quote_exports, "format_number", side_effect=lambda value, places=None, _lang=locale:
                             i18n.format_number(value, places, lang=_lang)),
            ):
                html = quote_exports.html_export(row).decode("utf-8")
                csv = quote_exports.csv_export(row).decode("utf-8-sig")
                self.assertIn(f'<html lang="{html_lang}">', html)
                self.assertIn(expected_title, html)
                self.assertIn(expected_csv_header, csv)


if __name__ == "__main__":
    unittest.main()
