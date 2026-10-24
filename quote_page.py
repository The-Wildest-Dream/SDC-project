from datetime import date, timedelta
import streamlit as st
from i18n import display_error, display_text, field_label, format_date, format_number, localize_records, t
from shared_data import get_data
from inquiry_service import save_inquiry
from database import DatabaseUnavailable
from quotation_rules import COSTS, calculate
from quotation_ui import show_costs, reminders
from finance_rules import funding, expiry_advice, apply_funding

st.header(t("quote.title"))
data = get_data()
products = {r["产品ID"]: r for r in data["产品"]}
customers = {r["客户ID"]: r for r in data["客户"]}
if not products or not customers:
    st.info(t("quote.need_master_data"))
    st.stop()
customer = st.selectbox(
    t("quote.select_customer"), list(customers),
    format_func=lambda k: f"{k} · {customers[k]['客户名称']}",
    key="quote.customer",
)
product = st.selectbox(
    t("quote.select_product"), list(products),
    format_func=lambda k: f"{k} · {products[k]['产品名称']}",
    key="quote.product",
)
p = products[product]
quantity = st.number_input(
    t("quote.quantity_unit", unit=p["单位"]), min_value=0.001, value=100.0,
    key="quote.quantity",
)
delivery = st.date_input(t("quote.delivery_date"), value=date.today()+timedelta(days=30), key="quote.delivery")
expiry = st.date_input(t("quote.valid_until"), value=date.today()+timedelta(days=7), key="quote.expiry")
st.subheader(t("quote.finance_policy"))
prepay = st.number_input(t("quote.prepayment_pct"), 0.0, 100.0, 30.0, key="quote.prepayment_pct")
term = st.number_input(t("quote.term_days"), 0, 3650, 30, key="quote.term_days")
annual_rate = st.number_input(t("quote.funding_rate"), 0.0, 100.0, 8.0, key="quote.funding_rate")
default_days = st.number_input(t("quote.default_validity"), 1, 365, 7, key="quote.default_validity")
max_days = st.number_input(t("quote.max_validity"), 1, 365, 30, key="quote.max_validity")
stale_threshold = st.number_input(t("quote.stale_days"), 1, 3650, 90, key="quote.stale_days")
material_change = st.number_input(
    t("quote.material_change"), -100.0, 1000.0, 0.0,
    key="quote.material_change",
)
material_unknown = st.checkbox(t("quote.material_unknown"), value=True, key="quote.material_unknown")
supplier_expiry_text = st.text_input(t("quote.supplier_expiry"), key="quote.supplier_expiry")
review_expiry = st.checkbox(t("quote.customer_review_policy"), value=False, key="quote.customer_review_policy")
st.subheader(t("quote.costs"))
st.caption(t("quote.cost_help"))
costs = {}
for i, field in enumerate(COSTS):
    costs[field] = st.text_input(
        field_label(field), value=str(p[field]) if i < 3 else "0",
        key=f"quote.cost.{i}",
    )
reason = st.text_area(t("quote.reason_label"), key="quote.cost_reason")
minimum = st.number_input(t("quote.minimum_margin"), value=10.0, key="quote.minimum_margin")
target = st.number_input(t("quote.target_margin"), value=20.0, key="quote.target_margin")
st.dataframe(localize_records([
    {"成本项": f,
     "来源": t("quote.cost_source_db") if i < 3 else t("quote.cost_source_manual"),
     "原值": str(p[f]) if i < 3 else "无",
     "本次值": costs[f] or t("quote.unknown"),
     "来源更新时间": p["成本更新时间"] if i < 3 else date.today().isoformat()}
    for i, f in enumerate(COSTS)
]), hide_index=True)
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
        st.subheader(t("finance.section"))
        st.write(t("finance.immediate_line", price=format_number(finance["immediate_unit"], 4), unit=p["单位"]))
        st.write(t("finance.conditional_line", price=format_number(finance["conditional_unit"], 4), unit=p["单位"]))
        st.write(t("finance.difference_line", price=format_number(finance["difference_unit"], 4), unit=p["单位"]))
        st.code(t("finance.formula"))
        st.write(t("finance.result", advance=format_number(finance["advance_amount"], 2),
                   cost=format_number(finance["funding_cost"], 2)))
        st.subheader(t("expiry.title"))
        st.write(t("expiry.recommended", date=format_date(advice["valid_until"]), days=advice["days"],
                   version=advice["rule_version"]))
        for reason_text in advice["reasons"]:
            st.caption(display_text(reason_text))
        st.caption(t("expiry.rule_note"))
except ValueError as error:
    st.error(display_error(error))
    result = None
reminders(data, customer, product, quantity)
if st.button(t("button.save"), type="primary", disabled=result is None, key="quote.save_inquiry"):
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
        st.success(t("quote.saved_inquiry", id=identifier))
    except (ValueError, DatabaseUnavailable) as error:
        st.error(display_error(error))
if st.session_state.get("current_inquiry"):
    st.caption(t("quote.current_inquiry", id=st.session_state.current_inquiry))
    st.page_link("history_page.py", label=t("quote.open_history"))
