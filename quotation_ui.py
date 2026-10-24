import streamlit as st
from datetime import date
from data_service import payment_summary
from i18n import display_text, field_label, format_date, format_number, localize_records, t
from quotation_rules import COSTS


def show_costs(result, costs, quantity, minimum, target, currency, unit):
    st.caption(t("quote.currency_unit", currency=currency, unit=unit))
    st.code(t("calc.formula"))
    if result["missing"]:
        st.warning(t("quote.missing_costs", fields="、".join(field_label(f) for f in result["missing"])))
        return
    st.write(t(
        "calc.unit_cost_line",
        material=costs[COSTS[0]], labor=costs[COSTS[1]], overhead=costs[COSTS[2]],
        fixed=costs[COSTS[3]], logistics=costs[COSTS[4]], quantity=quantity,
        result=f"{result['unit_cost']:.6f}",
    ))
    a, b, c = st.columns(3)
    a.metric(t("calc.unit_cost"), format_number(result["unit_cost"], 4))
    b.metric(t("calc.target_quote", margin=target), format_number(result["target"], 4))
    c.metric(t("calc.minimum_unit_price", margin=minimum), format_number(result["floor"], 6))


def reminders(data, customer, product, quantity):
    inventory = next((r for r in data["库存"] if r["产品ID"] == product), None)
    if inventory:
        available = inventory["现有数量"] - inventory["已预留数量"]
        st.write(t("quote.inventory_line", on_hand=format_number(inventory["现有数量"]),
                   reserved=format_number(inventory["已预留数量"]), available=format_number(available),
                   updated=format_date(inventory["更新时间"])))
        if quantity > available:
            st.warning(t("quote.stock_shortage"))
    else:
        st.warning(t("quote.stock_missing"))
    summary, _ = payment_summary(data, date.today())
    st.subheader(t("quote.customer_payment"))
    st.caption(t("quote.payment_summary_note", date=format_date(date.today())))
    st.dataframe(localize_records([r for r in summary if r["客户ID"] == customer]), hide_index=True)
    st.caption(t("quote.payment_notice"))
