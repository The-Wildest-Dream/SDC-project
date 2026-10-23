import streamlit as st
from datetime import date
from data_service import payment_summary
from quotation_rules import COSTS


def show_costs(result, costs, quantity, minimum, target, currency, unit):
    st.caption(f"金额币种：{currency}；计量单位：{unit}。计算使用未舍入金额。")
    st.code("单位成本 = 材料 + 人工 + 制造 + (整批固定费用 + 卖方承担的整批物流费用) / 数量\n"
            "目标报价 = 单位成本 / (1 - 目标毛利率)\n"
            "最低允许单价 = 单位成本 / (1 - 最低毛利率)")
    if result["missing"]:
        st.warning("缺少关键成本：" + "、".join(result["missing"]) + "。可保存草稿，禁止提交审批。")
        return
    st.write(f"单位成本 = {costs[COSTS[0]]} + {costs[COSTS[1]]} + {costs[COSTS[2]]}"
             f" + ({costs[COSTS[3]]} + {costs[COSTS[4]]}) / {quantity}"
             f" = {result['unit_cost']:.6f}")
    a, b, c = st.columns(3)
    a.metric("单位成本", f"{result['unit_cost']:.4f}")
    b.metric(f"目标报价（毛利率 {target}%）", f"{result['target']:.4f}")
    c.metric(f"最低允许单价（毛利率 {minimum}%）", f"{result['floor']:.6f}")


def reminders(data, customer, product, quantity):
    inventory = next((r for r in data["库存"] if r["产品ID"] == product), None)
    if inventory:
        available = inventory["现有数量"] - inventory["已预留数量"]
        st.write(f"可用库存 = {inventory['现有数量']} − {inventory['已预留数量']} = {available}；更新日期：{inventory['更新时间']}")
        if quantity > available:
            st.warning("需求超过可用库存。仅提醒，不自动采购或承诺交期。")
    else:
        st.warning("暂无该产品库存数据，无法判断是否足够；不承诺交期。")
    summary, _ = payment_summary(data, date.today())
    st.subheader("所选客户付款表现（模拟数据）")
    st.caption(f"统计截至 {date.today()}；按时付款率=到期订单中按时支付笔数/到期订单数。历史逾期天数仅累计已付订单。")
    st.dataframe([r for r in summary if r["客户ID"] == customer], hide_index=True)
    st.caption("仅供参考，不作诚信判断，不自动决定授信、账期或先货后款。")
