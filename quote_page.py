from datetime import date, timedelta
import streamlit as st
from shared_data import get_data
from inquiry_service import save_inquiry
from database import DatabaseUnavailable
from quotation_rules import COSTS, calculate
from quotation_ui import show_costs, reminders

st.header("新建询价与成本计算")
data = get_data()
products = {r["产品ID"]: r for r in data["产品"]}
customers = {r["客户ID"]: r for r in data["客户"]}
if not products or not customers:
    st.info("请先在数据中心导入产品和客户。")
    st.stop()
customer = st.selectbox("选择客户", list(customers), format_func=lambda k: f"{k} · {customers[k]['客户名称']}")
product = st.selectbox("选择产品", list(products), format_func=lambda k: f"{k} · {products[k]['产品名称']}")
p = products[product]
quantity = st.number_input(f"采购数量（{p['单位']}）", min_value=0.001, value=100.0)
delivery = st.date_input("交付日期", value=date.today()+timedelta(days=30))
expiry = st.date_input("报价有效期至", value=date.today()+timedelta(days=7))
st.subheader("本次成本")
st.caption("留空表示关键成本尚未确认；0表示已确认零费用。物流仅输入卖方承担部分。所有金额使用所选产品币种。")
costs = {}
for i, field in enumerate(COSTS):
    costs[field] = st.text_input(field, value=str(p[field]) if i < 3 else "0",
                                key=f"{product}_{field}_{p['成本更新时间']}")
reason = st.text_area("成本修改理由（修改或清空产品成本时必填）")
minimum = st.number_input("最低毛利率（%）", value=10.0)
target = st.number_input("目标毛利率（%）", value=20.0)
st.dataframe([{"成本项": f, "来源": "数据库产品成本；本次可调整" if i < 3 else "本次人工录入",
               "原值": str(p[f]) if i < 3 else "无",
               "本次值": costs[f] or "缺失",
               "来源更新时间": p["成本更新时间"] if i < 3 else date.today().isoformat()}
              for i, f in enumerate(COSTS)], hide_index=True)
try:
    result = calculate(quantity, costs, minimum, target)
    show_costs(result, costs, quantity, minimum, target, p["币种"], p["单位"])
except ValueError as error:
    st.error(str(error))
    result = None
reminders(data, customer, product, quantity)
if st.button("保存询价草稿", type="primary", disabled=result is None):
    try:
        identifier = save_inquiry(customer, product, quantity, delivery, expiry, costs, reason, minimum, target,
                                  actor=st.session_state.demo_actor)
        st.session_state.current_inquiry = identifier
        st.success(f"已保存询价：{identifier}")
    except (ValueError, DatabaseUnavailable) as error:
        st.error(str(error))
if st.session_state.get("current_inquiry"):
    st.caption("当前询价：" + st.session_state.current_inquiry)
    st.page_link("history_page.py", label="进入历史价格与报价建议")
