"""Localized exports of saved quote snapshots; uploaded CSV schemas remain unchanged."""
import csv
import io
from html import escape

from i18n import field_label, format_date, format_number, language, status_label, t
from quotation_rules import number


def fields(row):
    payload = row["payload"]
    terms = payload.get("snapshot", {}).get("terms", {})
    total = "" if payload["price"] in ("", None) else format_number(
        number(payload["price"]) * number(payload["quantity"])
    )
    status = status_label(row["status"])
    if row["status"] != "approved":
        status = t("export.unapproved_prefix", status=status)
    labels = [
        "编号", "询价编号", "版本", "状态", "客户", "产品", "数量", "单位",
        "币种", "单价", "总价", "有效期", "交付日期", "预付款比例",
        "尾款账期天数", "年资金成本率", "标记",
    ]
    values = [
        row["id"], row["inquiry_id"], str(row["version"]), status,
        payload["customer_name"], payload["product_name"], format_number(payload["quantity"]),
        payload["unit"], payload["currency"],
        "" if payload["price"] in ("", None) else format_number(payload["price"]),
        total, format_date(payload["valid_until"]), format_date(payload["delivery_date"]),
        format_number(terms["prepayment_pct"]) if "prepayment_pct" in terms else t("common.not_set"),
        format_number(terms["term_days"]) if "term_days" in terms else t("common.not_set"),
        format_number(terms["annual_rate_pct"]) if "annual_rate_pct" in terms else t("common.not_set"),
        t("export.demo"),
    ]
    return dict(zip([field_label(key) for key in labels], values))


def csv_export(row):
    values = fields(row)

    def safe(value):
        value = str(value)
        return "'" + value if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else value

    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(values)
    writer.writerow([safe(value) for value in values.values()])
    return output.getvalue().encode("utf-8-sig")


def html_export(row):
    values = fields(row)
    body = "".join(
        f"<tr><th>{escape(key)}</th><td>{escape(str(value))}</td></tr>"
        for key, value in values.items()
    )
    locale = language()
    title = t("export.title")
    demo = t("export.demo")
    printing = t("export.print")
    status = values[field_label("状态")]
    return (
        f"""<!doctype html><html lang="{escape(locale)}"><meta charset="utf-8"><title>{escape(title)}</title>
<style>body{{font-family:sans-serif;max-width:850px;margin:40px auto;padding:20px}}table{{width:100%;border-collapse:collapse}}
td,th{{border:1px solid #ccc;padding:10px;text-align:left}}h2{{color:#994500}}@media print{{button{{display:none}}body{{margin:0}}}}</style>
<h1>{escape(title)}</h1><h2>{escape(demo)}</h2><h2>{escape(status)}</h2><table>{body}</table>
<p>{escape(printing)}</p></html>"""
    ).encode("utf-8")
