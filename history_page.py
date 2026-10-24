from datetime import date
from decimal import ROUND_CEILING

import streamlit as st

from database import DatabaseUnavailable
from finance_rules import apply_funding
from i18n import (
    display_error, display_text, feature_label, field_label, format_date,
    format_number, inquiry_status_label,
    localize_json, localize_records, status_label, t,
)
from inquiry_service import list_inquiries
from price_model import group_key, predict_price
from quotation_rules import COSTS, calculate, check_price, number, percentile
from quotation_ui import reminders, show_costs
from shared_data import get_data
from workflow_service import create_draft


st.header(t("history.title"))
st.caption(t("history.caption"))
try:
    rows = list_inquiries()
except DatabaseUnavailable as error:
    st.error(display_error(error))
    st.stop()
if not rows:
    st.info(t("history.inquiry_prompt"))
    st.page_link("quote_page.py", label=t("history.open_new"))
    st.stop()

ids = [r["id"] for r in rows]
current = st.session_state.get("current_inquiry", ids[0])
identifier = st.selectbox(
    t("history.current_inquiry"), ids,
    index=ids.index(current) if current in ids else 0,
    key="history.current_inquiry",
)
st.session_state.current_inquiry = identifier
r = next(row for row in rows if row["id"] == identifier)
s = r["snapshot"]
st.write(t(
    "history.product_info", product=s["product_name"], customer=r["customer_id"],
    quantity=r["quantity"], unit=r["unit"], currency=r["currency"],
))
st.write(t(
    "history.schedule_info", delivery=format_date(r["delivery_date"]),
    expiry=format_date(r["valid_until"]),
    status=inquiry_status_label(r["status"]),
))
result = calculate(r["quantity"], s["costs"], s["minimum"], s["target"])
terms = s.get("terms", {})
finance = terms.get("finance")
result = apply_funding(result, finance)
st.subheader(t("history.base"))
show_costs(result, s["costs"], r["quantity"], s["minimum"], s["target"], r["currency"], r["unit"])
with st.expander(t("history.cost_sources")):
    st.dataframe(localize_records([
        {
            "成本项": field,
            "原值": s["source_costs"].get(field, "无"),
            "本次值": s["costs"][field] or t("quote.unknown"),
            "来源": t("history.cost_catalog") if index < 3 else t("history.cost_manual"),
            "更新时间": s["source_updated"] if index < 3 else s["entered_at"],
        }
        for index, field in enumerate(COSTS)
    ]), hide_index=True)
    st.write(t("history.reason", reason=s["reason"] or t("history.no_reason")))

data = get_data()
st.subheader(t("history.reference"))
base = [
    row for row in data["历史交易"]
    if (row["产品ID"], row["币种"], row["单位"]) == (r["product_id"], r["currency"], r["unit"])
]
start = st.date_input(
    t("history.start_date"),
    value=date.fromisoformat(min((row["订单日期"] for row in base), default=date.today().isoformat())),
    key="history.start_date",
)
end = st.date_input(t("history.end_date"), value=date.today(), key="history.end_date")
low = st.number_input(t("history.quantity_min"), min_value=0.0, value=0.0, key="history.quantity_min")
high = st.number_input(
    t("history.quantity_max"), min_value=0.0,
    value=float(max([row["数量"] for row in base] + [r["quantity"]])),
    key="history.quantity_max",
)
if start > end or low > high:
    st.error(t("history.invalid_range"))
    matches = []
else:
    matches = [
        row for row in base
        if start.isoformat() <= row["订单日期"] <= end.isoformat()
        and low <= row["数量"] <= high
    ]
st.metric(t("history.match_count"), len(matches))
if matches:
    prices = [row["成交单价"] for row in matches]
    st.write(t(
        "history.percentiles",
    p25=format_number(percentile(prices, .25), 4),
    p50=format_number(percentile(prices, .5), 4),
    p75=format_number(percentile(prices, .75), 4),
    ))
    st.caption(t("history.quantile_note"))
    if len(matches) < 10:
        st.warning(t("history.few_matches"))
    st.dataframe(localize_records(matches), hide_index=True)
else:
    st.info(t("history.no_reference"))

st.subheader(t("history.model"))
model_value, model_reason, model_meta = (
    None, "关键单位成本缺失，不能预测；继续使用历史参考及可用成本信息。", None
)
if all(s["costs"].get(field) not in ("", None) for field in COSTS[:3]):
    # Keep the existing feature definition: production costs exclude batch allocations.
    production_cost = sum(number(s["costs"][field]) for field in COSTS[:3])
    model_value, model_reason, model_meta = predict_price(
        r["product_id"], r["currency"], r["unit"], r["quantity"],
        production_cost, r["created_at"].date(),
    )
if model_value is None:
    st.warning(t("history.model_unavailable", reason=display_text(model_reason)))
else:
    st.metric(
        t("history.model_price", currency=r["currency"], unit=r["unit"]),
        format_number(model_value, 4),
    )
    st.caption(display_text(model_reason))
    if not result["missing"] and number(model_value) < result["floor"]:
        st.warning(t("history.model_below_floor"))
st.caption(t("history.distinction"))

if finance:
    st.subheader(t("history.finance"))
    st.write(t(
        "history.payment_terms",
        prepayment=terms["prepayment_pct"], days=terms["term_days"],
        rate=terms["annual_rate_pct"],
    ))
    st.write(t(
        "history.finance_line",
        immediate=format_number(finance["immediate_unit"], 4),
        conditional=format_number(finance["conditional_unit"], 4),
        difference=format_number(finance["difference_unit"], 4),
    ))
    st.write(t(
        "history.funding_line",
        advance=format_number(finance["advance_amount"], 2),
        cost=format_number(finance["funding_cost"], 2),
    ))
    advice = terms["expiry_advice"]
    st.write(t(
        "history.expiry_line", date=format_date(advice["valid_until"]),
        reasons="；".join(display_text(reason) for reason in advice["reasons"]),
    ))
st.warning(t("history.synthetic_metrics"))
if model_meta:
    with st.expander(t("history.model_meta")):
        st.write(t("history.trained_at", value=format_date(model_meta["trained_at_utc"])))
        st.write(t("history.data_version", value=model_meta["data_version"]))
        st.write(t(
            "history.input_features",
            value="、".join(feature_label(feature) for feature in model_meta["features"]),
        ))
        group = model_meta["groups"].get(group_key(r["product_id"], r["currency"], r["unit"]), {})
        st.json(localize_json(group))
        st.caption(t("history.mae_note"))

st.subheader(t("history.manual"))
default = "" if result["missing"] else str(
    result["target"].quantize(number(".01"), rounding=ROUND_CEILING)
)
price = st.text_input(
    t("history.manual_price", currency=r["currency"], unit=r["unit"]),
    value=default, key=f"history.manual_price.{identifier}",
)
blocked = None
try:
    proposed_price = number(price)
    st.metric(t("history.total_amount"), format_number(proposed_price*r["quantity"], 2))
    if not result["missing"] and proposed_price > 0:
        st.metric(
            t("history.realized_margin"),
            format_number((1-result["unit_cost"]/proposed_price)*100, 4) + "%",
        )
    check_price(result, price)
    if r["status"] != "draft":
        raise ValueError("该询价已提交或关闭，不可重复提交。")
    if r["valid_until"] < date.today():
        raise ValueError("报价已过有效期，禁止提交。")
except ValueError as error:
    blocked = display_error(error)
    st.warning(blocked)

if st.button(t("button.save"), key="history.save_quote"):
    try:
        reference = {
            "筛选开始日期": str(start), "筛选结束日期": str(end),
            "数量下限": low, "数量上限": high, "匹配笔数": len(matches),
            "订单ID": [row["订单ID"] for row in matches],
            "历史价格快照": [str(row["成交单价"]) for row in matches],
            "口径": "同产品/币种/单位，订单等权线性插值",
            "模型预测": model_value, "模型说明": model_reason,
            "模型数据版本": model_meta["data_version"] if model_meta else None,
        }
        qid = create_draft(identifier, price, reference, st.session_state.demo_actor)
        st.session_state.selected_quote = qid
        st.success(t("history.draft_saved", id=qid))
    except (ValueError, DatabaseUnavailable) as error:
        st.error(display_error(error))
st.page_link("records_page.py", label=t("history.open_records"))
reminders(data, r["customer_id"], r["product_id"], r["quantity"])
