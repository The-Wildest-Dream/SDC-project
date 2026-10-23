import streamlit as st
from workflow_service import records
from database import DatabaseUnavailable
from shared_data import get_data
from quote_exports import fields
from quotation_rules import number

st.header("工作台")
st.caption("模拟业务数据，以下指标实时读取数据库，不使用虚构统计值。")
st.page_link("quote_page.py", label="新建询价")
st.page_link("approval_page.py", label="进入审批中心")
try:
    rows = records()
except DatabaseUnavailable as e:
    st.error(str(e)); st.stop()
st.metric("待审批报价版本", sum(r["status"] == "pending" for r in rows))
st.subheader("近期报价（最近10个版本）")
if rows: st.dataframe([fields(r) for r in rows[:10]], hide_index=True)
else: st.info("暂无报价，请先创建询价。")
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
st.subheader("库存不足提醒")
st.caption("每份询价仅检查最新、非驳回报价版本；逐单比较现有量−预留量，不汇总承诺库存，不自动采购或承诺交期。")
if warnings: st.dataframe(warnings, hide_index=True)
else: st.info("暂无符合上述口径的库存不足提醒。")
