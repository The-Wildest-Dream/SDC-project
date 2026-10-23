from datetime import date
import streamlit as st
from workflow_service import records, audit, edit_draft, submit_quote, revise, LABELS
from database import DatabaseUnavailable
from quotation_rules import COSTS, calculate, number
from quote_exports import csv_export, html_export, fields

st.header("报价记录与下载")
try:
    rows = records()
except DatabaseUnavailable as e:
    st.error(str(e)); st.stop()
if not rows:
    st.info("暂无报价记录。请保存询价后在历史价格页保存报价草稿。")
    st.page_link("quote_page.py", label="新建询价")
    st.stop()
customer = st.selectbox("客户筛选", ["全部"]+sorted({r["payload"]["customer_name"] for r in rows}))
product = st.selectbox("产品筛选", ["全部"]+sorted({r["payload"]["product_name"] for r in rows}))
state = st.selectbox("状态筛选", ["全部"]+list(LABELS.values()))
start = st.date_input("创建日期起", value=min(r["created_at"].date() for r in rows))
end = st.date_input("创建日期止", value=date.today())
filtered = [r for r in rows if (customer == "全部" or r["payload"]["customer_name"] == customer)
            and (product == "全部" or r["payload"]["product_name"] == product)
            and (state == "全部" or LABELS[r["status"]] == state)
            and start <= r["created_at"].date() <= end]
if not filtered:
    st.info("没有符合筛选条件的报价。"); st.stop()
st.dataframe([fields(r) for r in filtered], hide_index=True)
ids = [r["id"] for r in filtered]
selected = st.session_state.get("selected_quote", ids[0])
identifier = st.selectbox("查看报价版本", ids, index=ids.index(selected) if selected in ids else 0,
                         format_func=lambda k: f"{k} · V{next(r['version'] for r in filtered if r['id']==k)}")
st.session_state.selected_quote = identifier
r = next(r for r in filtered if r["id"] == identifier)
p = r["payload"]
st.write(f"状态：{LABELS[r['status']]} · 所属模拟销售：{r['owner']} · 创建：{r['created_at']} · 更新：{r['updated_at']}")
st.subheader("已保存快照")
st.json(p)
try:
    approvals, operations = audit(identifier)
    st.subheader("审批意见及操作时间")
    if approvals: st.dataframe(approvals, hide_index=True)
    else: st.caption("暂无审批记录。")
    if operations: st.dataframe(operations, hide_index=True)
except DatabaseUnavailable as e:
    st.error(str(e))
if r["status"] != "approved":
    st.warning("草稿/未批准：下载内容含明确标记，不可作为已批准报价。")
st.download_button("下载CSV报价单", csv_export(r), file_name=f"{identifier}_V{r['version']}.csv", mime="text/csv")
st.download_button("下载可打印HTML报价单", html_export(r), file_name=f"{identifier}_V{r['version']}.html", mime="text/html")
actor = st.session_state.demo_actor
if r["owner"] == actor and r["status"] == "draft":
    st.subheader("修改自己的草稿")
    with st.form(f"edit_{identifier}"):
        quantity = st.text_input("数量", value=p["quantity"])
        price = st.text_input("人工拟报价", value=p["price"])
        delivery = st.date_input("交付日期", value=date.fromisoformat(p["delivery_date"]))
        expiry = st.date_input("有效期", value=date.fromisoformat(p["valid_until"]))
        costs = {f: st.text_input(f, value=p["snapshot"]["costs"][f]) for f in COSTS}
        reason = st.text_area("本次成本修改理由", value=p["snapshot"]["reason"])
        minimum = st.number_input("最低毛利率", value=float(p["snapshot"]["minimum"]))
        target = st.number_input("目标毛利率", value=float(p["snapshot"]["target"]))
        save = st.form_submit_button("保存草稿修改")
    if save:
        try:
            edit_draft(identifier, dict(quantity=quantity, price=price, delivery_date=delivery,
                       valid_until=expiry, costs=costs, reason=reason, minimum=minimum, target=target), actor)
            st.rerun()
        except (ValueError, DatabaseUnavailable) as e: st.error(str(e))
    if st.button("提交审批", type="primary"):
        try:
            submit_quote(identifier, actor); st.rerun()
        except (ValueError, DatabaseUnavailable) as e: st.error(str(e))
elif r["owner"] == actor and r["status"] in ("approved", "rejected"):
    if st.button("创建修改版本（重新审批）"):
        try:
            st.session_state.selected_quote = revise(identifier, actor); st.rerun()
        except (ValueError, DatabaseUnavailable) as e: st.error(str(e))
else:
    if r["status"] == "pending":
        st.info("待审批版本的金额与成本已锁定，不能直接修改。")
    else:
        st.info(f"此版本状态为“{LABELS[r['status']]}”。当前角色只读；只有所属销售可编辑自己的草稿，或为已结束版本创建新版本。")
