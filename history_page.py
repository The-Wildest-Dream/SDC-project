from datetime import date
from decimal import ROUND_CEILING
import streamlit as st
from shared_data import get_data
from inquiry_service import list_inquiries
from workflow_service import create_draft
from database import DatabaseUnavailable
from quotation_rules import calculate, percentile, number, check_price, COSTS
from finance_rules import apply_funding
from quotation_ui import show_costs, reminders
from price_model import predict_price, group_key

st.header("历史价格与报价建议")
st.caption("模拟数据 · 成本规则、历史统计与离线训练的成交价预测分别展示，均不替代人工审批。")
try:
    rows = list_inquiries()
except DatabaseUnavailable as error:
    st.error(str(error))
    st.stop()
if not rows:
    st.info("请先保存一份询价。")
    st.page_link("quote_page.py", label="新建询价")
    st.stop()
ids = [r["id"] for r in rows]
current = st.session_state.get("current_inquiry", ids[0])
identifier = st.selectbox("当前询价", ids, index=ids.index(current) if current in ids else 0)
st.session_state.current_inquiry = identifier
r = next(r for r in rows if r["id"] == identifier)
s = r["snapshot"]
st.write(f"产品：{s['product_name']} · 客户：{r['customer_id']} · 数量：{r['quantity']} {r['unit']} · 币种：{r['currency']}")
st.write(f"交付日期：{r['delivery_date']} · 有效期至：{r['valid_until']} · 状态：{r['status']}")
result = calculate(r["quantity"], s["costs"], s["minimum"], s["target"])
terms = s.get("terms", {})
finance = terms.get("finance")
result = apply_funding(result, finance)
st.subheader("成本底线与目标报价（保存时的成本快照）")
show_costs(result, s["costs"], r["quantity"], s["minimum"], s["target"], r["currency"], r["unit"])
with st.expander("成本来源及修改理由"):
    st.dataframe([{"成本项": f, "原值": s["source_costs"].get(f, "无"),
                   "本次值": s["costs"][f] or "缺失", "来源": "产品库" if i < 3 else "人工录入",
                   "更新时间": s["source_updated"] if i < 3 else s["entered_at"]}
                  for i, f in enumerate(COSTS)], hide_index=True)
    st.write("修改理由：" + (s["reason"] or "未修改产品成本"))
data = get_data()
st.subheader("历史参考（同产品、币种、单位）")
base = [t for t in data["历史交易"] if (t["产品ID"], t["币种"], t["单位"]) ==
        (r["product_id"], r["currency"], r["unit"])]
start = st.date_input("历史开始日期", value=date.fromisoformat(min((t["订单日期"] for t in base), default=date.today().isoformat())))
end = st.date_input("历史结束日期", value=date.today())
low = st.number_input("历史数量下限", min_value=0.0, value=0.0)
high = st.number_input("历史数量上限", min_value=0.0, value=float(max([t["数量"] for t in base]+[r["quantity"]])))
if start > end or low > high:
    st.error("筛选起止范围无效。")
    matches = []
else:
    matches = [t for t in base if start.isoformat() <= t["订单日期"] <= end.isoformat() and low <= t["数量"] <= high]
st.metric("匹配交易数量", len(matches))
if matches:
    prices = [t["成交单价"] for t in matches]
    st.write({label: f"{percentile(prices, q):.4f}" for label, q in [("P25", .25), ("中位数P50", .5), ("P75", .75)]})
    st.caption("按订单等权、线性插值分位数，不按数量加权；历史参考不覆盖成本底线。")
    if len(matches) < 10:
        st.warning("可比交易少于10笔，样本不足，历史参考需谨慎使用。")
    st.dataframe(matches, hide_index=True)
else:
    st.info("暂无历史参考")
st.subheader("模型预测成交单价（独立辅助参考）")
model_value, model_reason, model_meta = None, "关键单位成本缺失，不能预测；继续使用历史参考及可用成本信息。", None
if all(s["costs"].get(f) not in ("", None) for f in COSTS[:3]):
    # 历史“当时单位成本”口径为三项生产成本合计，不混入整批固定/物流分摊。
    production_cost = sum(number(s["costs"][f]) for f in COSTS[:3])
    model_value, model_reason, model_meta = predict_price(
        r["product_id"], r["currency"], r["unit"], r["quantity"], production_cost, r["created_at"].date())
if model_value is None:
    st.warning("预测不可用：" + model_reason)
else:
    st.metric(f"模型预测价格（{r['currency']}/{r['unit']}）", f"{model_value:.4f}")
    st.caption(model_reason)
    if not result["missing"] and number(model_value) < result["floor"]:
        st.warning("预测低于最低允许单价，不可据此绕过底线提交。")
st.caption("成本底线是最低毛利率约束；历史参考是筛选交易的统计；模型预测是历史成交价估计。预测不会自动改写人工拟报价。")
if finance:
    st.subheader("付款条件与综合报价参考")
    st.write(f"预付款比例 {terms['prepayment_pct']}%，尾款账期 {terms['term_days']} 天，企业年资金成本率 {terms['annual_rate_pct']}%。")
    st.write(f"立即付款参考报价 {finance['immediate_unit']:.4f}；当前付款条件参考报价 {finance['conditional_unit']:.4f}；差额 {finance['difference_unit']:.4f} / 单位。")
    st.write(f"预计垫付金额 {finance['advance_amount']:.2f}；资金占用成本 {finance['funding_cost']:.2f}。费用已进入保存快照的成本底线一次，不会叠加到历史价或模型预测价。")
    st.write(f"有效期建议至 {terms['expiry_advice']['valid_until']}；" + "；".join(terms["expiry_advice"]["reasons"]))
st.warning("合成数据上的指标只验证原型流程，不证明真实商业收益。")
if model_meta:
    with st.expander("模型版本、特征及测试集评估"):
        st.write("训练时间：" + model_meta["trained_at_utc"])
        st.write("数据版本：" + model_meta["data_version"])
        st.write("输入字段：" + "、".join(model_meta["features"]))
        st.json(model_meta["groups"].get(group_key(r["product_id"], r["currency"], r["unit"]), {}))
        st.caption("MAE单位与本产品币种相同；基线与模型使用同一时间测试集。")
st.subheader("人工拟报价")
default = "" if result["missing"] else str(result["target"].quantize(number(".01"), rounding=ROUND_CEILING))
price = st.text_input(f"拟报价（{r['currency']}/{r['unit']}）", value=default, key=f"price_{identifier}")
blocked = None
try:
    p = number(price)
    st.metric("整单金额", f"{p*r['quantity']:.2f}")
    if not result["missing"] and p > 0:
        st.metric("实际毛利率", f"{(1-result['unit_cost']/p)*100:.4f}%")
    check_price(result, price)
    if r["status"] != "draft":
        raise ValueError("该询价已提交或关闭，不可重复提交。")
    if r["valid_until"] < date.today():
        raise ValueError("报价已过有效期，禁止提交。")
except ValueError as error:
    blocked = str(error)
    st.warning(blocked)
if st.button("保存报价草稿", type="primary"):
    try:
        reference = {"筛选开始日期": str(start), "筛选结束日期": str(end),
                     "数量下限": low, "数量上限": high, "匹配笔数": len(matches),
                     "订单ID": [t["订单ID"] for t in matches],
                     "历史价格快照": [str(t["成交单价"]) for t in matches],
                     "口径": "同产品/币种/单位，订单等权线性插值",
                     "模型预测": model_value, "模型说明": model_reason,
                     "模型数据版本": model_meta["data_version"] if model_meta else None}
        qid = create_draft(identifier, price, reference, st.session_state.demo_actor)
        st.session_state.selected_quote = qid
        st.success(f"报价草稿已保存：{qid}。请到报价记录修改或提交审批。")
    except (ValueError, DatabaseUnavailable) as error:
        st.error(str(error))
st.page_link("records_page.py", label="进入报价记录与下载")
reminders(data, r["customer_id"], r["product_id"], r["quantity"])
