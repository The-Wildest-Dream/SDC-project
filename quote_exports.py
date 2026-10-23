"""使用已保存快照导出，HTML转义防注入，CSV防公式执行。"""
import csv
import io
from html import escape
from quotation_rules import number
from workflow_service import LABELS


def fields(row):
    p = row["payload"]
    terms = p.get("snapshot", {}).get("terms", {})
    total = "" if p["price"] in ("", None) else str(number(p["price"])*number(p["quantity"]))
    return {"编号": row["id"], "询价编号": row["inquiry_id"], "版本": str(row["version"]),
            "状态": LABELS[row["status"]] if row["status"] == "approved" else "草稿/未批准 · "+LABELS[row["status"]],
            "客户": p["customer_name"], "产品": p["product_name"], "数量": p["quantity"],
            "单位": p["unit"], "币种": p["currency"], "单价": p["price"], "总价": total,
            "有效期": p["valid_until"], "交付日期": p["delivery_date"],
            "预付款比例": terms.get("prepayment_pct", "未设置"),
            "尾款账期天数": terms.get("term_days", "未设置"),
            "年资金成本率": terms.get("annual_rate_pct", "未设置"),
            "标记": "模拟演示 · 非真实交易凭证"}


def csv_export(row):
    values = fields(row)
    def safe(value):
        value = str(value)
        return "'" + value if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else value
    out = io.StringIO(newline="")
    writer = csv.writer(out)
    writer.writerow(values)
    writer.writerow([safe(v) for v in values.values()])
    return out.getvalue().encode("utf-8-sig")


def html_export(row):
    values = fields(row)
    body = "".join(f"<tr><th>{escape(k)}</th><td>{escape(str(v))}</td></tr>" for k, v in values.items())
    return ("""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>模拟演示报价单</title>
<style>body{font-family:sans-serif;max-width:850px;margin:40px auto;padding:20px}table{width:100%;border-collapse:collapse}
td,th{border:1px solid #ccc;padding:10px;text-align:left}h2{color:#994500}@media print{button{display:none}body{margin:0}}</style>
<h1>报价单</h1><h2>模拟演示 · 非真实交易凭证</h2>"""
            + f"<h2>{escape(values['状态'])}</h2><table>{body}</table>"
            + '<p>使用浏览器打印功能或按 Ctrl/P、Cmd/P 打印。本报价仅用于比赛演示。</p></html>').encode("utf-8")
