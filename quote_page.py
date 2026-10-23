from datetime import date, timedelta
import streamlit as st
from shared_data import get_data
from inquiry_service import save_inquiry
from database import DatabaseUnavailable
from quotation_rules import COSTS, calculate
from quotation_ui import show_costs, reminders
from finance_rules import funding, expiry_advice, apply_funding

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
st.subheader("付款条件与有效期规则（模拟企业策略）")
prepay = st.number_input("预付款比例（%）", 0.0, 100.0, 30.0)
term = st.number_input("约定尾款账期（天）", 0, 3650, 30)
annual_rate = st.number_input("年资金成本率（%）", 0.0, 100.0, 8.0)
default_days = st.number_input("企业默认有效期（天）", 1, 365, 7)
max_days = st.number_input("企业最长有效期（天）", 1, 365, 30)
stale_threshold = st.number_input("成本过期阈值（天）", 1, 3650, 90)
material_change = st.number_input("近期原材料变化（%，未知填0并勾选未知）", -100.0, 1000.0, 0.0)
material_unknown = st.checkbox("没有可靠的原材料变化数据", value=True)
supplier_expiry_text = st.text_input("供应商报价到期日（YYYY-MM-DD，可空）")
review_expiry = st.checkbox("启用逾期客户有效期复核政策", value=False)
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
    finance = None
    advice = None
    if not result["missing"]:
        base = result["unit_cost"]
        finance = funding(base, quantity, minimum, target, prepay, term, annual_rate)
        advice = expiry_advice(date.today(), p["成本更新时间"], default_days, max_days,
                               supplier_expiry_text or None,
                               None if material_unknown else material_change,
                               stale_threshold, 10, False, review_expiry)
        expiry = date.fromisoformat(advice["valid_until"])
        result = apply_funding(result, finance)
    show_costs(result, costs, quantity, minimum, target, p["币种"], p["单位"])
    if finance:
        st.subheader("资金占用与付款条件报价")
        st.write(f"立即付款参考报价：{finance['immediate_unit']:.4f} / {p['单位']}")
        st.write(f"当前条件参考报价：{finance['conditional_unit']:.4f} / {p['单位']}")
        st.write(f"差额：{finance['difference_unit']:.4f} / {p['单位']}")
        st.code("垫付金额 = max(基础总成本 − 立即付款参考总价 × 预付款比例, 0)\n"
                "资金占用成本 = 垫付金额 × 年资金成本率 × 尾款账期天数 / 365\n"
                "延期参考价 = (基础单位成本 + 资金占用成本/数量) / (1 − 目标毛利率)")
        st.write(f"预计垫付 {finance['advance_amount']:.2f}，资金占用成本 {finance['funding_cost']:.2f}。"
                 "假设成本在交付时一次性垫付、预付款按立即付款参考总价抵扣、尾款在约定账期一次收回；"
                 "不将应收账款视作垫付成本。")
        st.subheader("有效期建议")
        st.write(f"建议有效期至 {advice['valid_until']}（{advice['days']} 天），规则 {advice['rule_version']}")
        for reason_text in advice["reasons"]: st.caption(reason_text)
        st.caption("原材料变化阈值10%为演示规则；客户逾期仅在明确启用企业复核规则时影响有效期。")
except ValueError as error:
    st.error(str(error))
    result = None
reminders(data, customer, product, quantity)
if st.button("保存询价草稿", type="primary", disabled=result is None):
    try:
        identifier = save_inquiry(customer, product, quantity, delivery, expiry, costs, reason, minimum, target,
                                  actor=st.session_state.demo_actor,
                                  terms={"prepayment_pct": prepay, "term_days": term,
                                         "annual_rate_pct": annual_rate, "finance": finance,
                                         "expiry_advice": advice, "material_change_pct": None if material_unknown else material_change,
                                         "supplier_expiry": supplier_expiry_text or None,
                                         "policy": {"version": "PAY-EXP-1", "default_days": default_days,
                                                    "max_days": max_days, "stale_days": stale_threshold,
                                                    "material_threshold_pct": 10, "customer_review_affects_expiry": review_expiry}})
        st.session_state.current_inquiry = identifier
        st.success(f"已保存询价：{identifier}")
    except (ValueError, DatabaseUnavailable) as error:
        st.error(str(error))
if st.session_state.get("current_inquiry"):
    st.caption("当前询价：" + st.session_state.current_inquiry)
    st.page_link("history_page.py", label="进入历史价格与报价建议")
