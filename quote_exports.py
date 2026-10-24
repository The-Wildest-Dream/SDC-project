"""使用已保存快照导出，HTML转义防注入，CSV防公式执行。"""
import csv
import io
from html import escape
from quotation_rules import number
from workflow_service import LABELS
from i18n import t, language


def fields(row):
    p = row["payload"]
    terms = p.get("snapshot", {}).get("terms", {})
    total = "" if p["price"] in ("", None) else str(number(p["price"])*number(p["quantity"]))
    if language() == "zh-CN":
        labels = ["编号","询价编号","版本","状态","客户","产品","数量","单位","币种","单价","总价","有效期","交付日期","预付款比例","尾款账期天数","年资金成本率","标记"]
        status = LABELS[row["status"]] if row["status"] == "approved" else "草稿/未批准 · "+LABELS[row["status"]]
        demo = "模拟演示 · 非真实交易凭证"
    elif language() == "en":
        labels = ["Quote ID","Inquiry ID","Version","Status","Customer","Product","Quantity","Unit","Currency","Unit price","Total","Valid until","Delivery date","Advance payment (%)","Balance term (days)","Annual cost of funds (%)","Demo notice"]
        status = {"draft":"Draft","pending":"Pending approval","approved":"Approved","rejected":"Rejected"}[row["status"]]
        if row["status"] != "approved": status = "DRAFT / NOT APPROVED · "+status
        demo = "DEMO ONLY · NOT A REAL TRANSACTION DOCUMENT"
    else:
        labels = ["ID Sebut Harga","ID Pertanyaan","Versi","Status","Pelanggan","Produk","Kuantiti","Unit","Mata wang","Harga seunit","Jumlah","Sah sehingga","Tarikh penghantaran","Bayaran pendahuluan (%)","Tempoh baki (hari)","Kos dana tahunan (%)","Notis demo"]
        status = {"draft":"Draf","pending":"Menunggu kelulusan","approved":"Diluluskan","rejected":"Ditolak"}[row["status"]]
        if row["status"] != "approved": status = "DRAF / BELUM DILULUSKAN · "+status
        demo = "DEMO SAHAJA · BUKAN DOKUMEN TRANSAKSI SEBENAR"
    vals=[row["id"],p["inquiry_id"] if "inquiry_id" in p else row["inquiry_id"],str(row["version"]),status,p["customer_name"],p["product_name"],p["quantity"],p["unit"],p["currency"],p["price"],total,p["valid_until"],p["delivery_date"],terms.get("prepayment_pct","Not set"),terms.get("term_days","Not set"),terms.get("annual_rate_pct","Not set"),demo]
    return dict(zip(labels, vals))


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
    lang={"zh-CN":"zh-CN","en":"en","ms":"ms"}[language()]
    title=t("export.title"); demo=t("export.demo"); printing=t("export.print")
    return (f"""<!doctype html><html lang="{lang}"><meta charset="utf-8"><title>{escape(title)}</title>
<style>body{{font-family:sans-serif;max-width:850px;margin:40px auto;padding:20px}}table{{width:100%;border-collapse:collapse}}
td,th{{border:1px solid #ccc;padding:10px;text-align:left}}h2{{color:#994500}}@media print{{button{{display:none}}body{{margin:0}}}}</style>
<h1>{escape(title)}</h1><h2>{escape(demo)}</h2>"""
            + f"<h2>{escape(next(v for k,v in values.items() if k in ('状态','Status')))}</h2><table>{body}</table>"
            + f"<p>{escape(printing)}</p></html>").encode("utf-8")
