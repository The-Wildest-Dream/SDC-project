import streamlit as st
from workflow_service import records, decide, LABELS
from database import DatabaseUnavailable
from quote_exports import fields

st.header("审批中心")
st.caption("模拟角色审批，仅用于比赛流程演示，不构成真实认证或生产权限。")
try:
    rows = [r for r in records() if r["status"] == "pending"]
except DatabaseUnavailable as e:
    st.error(str(e)); st.stop()
if not rows:
    st.info("暂无待审批报价。"); st.stop()
st.metric("待审批版本数", len(rows))
st.dataframe([fields(r) for r in rows], hide_index=True)
identifier = st.selectbox("选择待审批版本", [r["id"] for r in rows])
r = next(r for r in rows if r["id"] == identifier)
st.json(r["payload"])
if st.session_state.demo_actor != "经理":
    st.info("销售人员仅可查看；请切换模拟经理角色进行审批。"); st.stop()
comment = st.text_area("审批意见（必填）")
approved = st.radio("审批决定", ["批准", "驳回"])
if st.button("确认审批", type="primary"):
    try:
        decide(identifier, approved == "批准", comment, st.session_state.demo_actor)
        st.success("审批已保存，状态与日志已在同一事务提交。")
        st.page_link("records_page.py", label="查看报价与下载")
    except (ValueError, DatabaseUnavailable) as e: st.error(str(e))
