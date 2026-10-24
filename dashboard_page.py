import streamlit as st
from i18n import display_error, localize_records, t
from workflow_service import records
from database import DatabaseUnavailable
from shared_data import get_data
from quote_exports import fields
from quotation_rules import number

st.header(t("dashboard.title"))
st.caption(t("dashboard.live_caption"))
st.page_link("quote_page.py", label=t("button.new"))
st.page_link("approval_page.py", label=t("button.approvals"))
try:
    rows = records()
except DatabaseUnavailable as e:
    st.error(display_error(e)); st.stop()
st.metric(t("dashboard.pending_count"), sum(r["status"] == "pending" for r in rows))
st.subheader(t("dashboard.recent"))
if rows:
    st.dataframe([fields(r) for r in rows[:10]], hide_index=True)
else:
    st.info(t("dashboard.no_quotes"))
data = get_data()
inventory = {r["产品ID"]: r for r in data["库存"]}
latest = {}
for r in rows:
    latest.setdefault(r["inquiry_id"], r)
warnings = []
for r in latest.values():
    if r["status"] == "rejected": continue
    p = r["payload"]
    stock = inventory.get(p["product_id"])
    available = stock["现有数量"]-stock["已预留数量"] if stock else None
    if available is None or number(p["quantity"]) > available:
        warnings.append({"编号": r["id"], "产品": p["product_name"], "需求": p["quantity"],
                         "可用库存": str(available) if available is not None else "缺少库存数据"})
st.subheader(t("dashboard.stock"))
st.caption(t("dashboard.stock_note"))
if warnings:
    st.dataframe(localize_records(warnings), hide_index=True)
else:
    st.info(t("dashboard.no_stock"))
