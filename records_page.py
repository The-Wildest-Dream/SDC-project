from datetime import date

import streamlit as st

from database import DatabaseUnavailable
from i18n import (
    display_error, field_label, localize_json, localize_records,
    format_date, role_label, status_label, t,
)
from quote_exports import csv_export, fields, html_export
from quotation_rules import COSTS
from workflow_service import audit, edit_draft, records, revise, submit_quote


st.header(t("records.title"))
try:
    rows = records()
except DatabaseUnavailable as error:
    st.error(display_error(error))
    st.stop()
if not rows:
    st.info(t("records.empty"))
    st.page_link("quote_page.py", label=t("button.new"))
    st.stop()

customer = st.selectbox(
    t("records.customer_filter"),
    [""] + sorted({row["payload"]["customer_name"] for row in rows}),
    format_func=lambda value: value or t("common.all"),
    key="records.customer_filter",
)
product = st.selectbox(
    t("records.product_filter"),
    [""] + sorted({row["payload"]["product_name"] for row in rows}),
    format_func=lambda value: value or t("common.all"),
    key="records.product_filter",
)
state = st.selectbox(
    t("records.status_filter"), ["", "draft", "pending", "approved", "rejected"],
    format_func=lambda value: t("common.all") if not value else status_label(value),
    key="records.status_filter",
)
start = st.date_input(
    t("records.date_from"), value=min(row["created_at"].date() for row in rows),
    key="records.date_from",
)
end = st.date_input(t("records.date_to"), value=date.today(), key="records.date_to")
filtered = [
    row for row in rows
    if (not customer or row["payload"]["customer_name"] == customer)
    and (not product or row["payload"]["product_name"] == product)
    and (not state or row["status"] == state)
    and start <= row["created_at"].date() <= end
]
if not filtered:
    st.info(t("records.no_match"))
    st.stop()
st.dataframe([fields(row) for row in filtered], hide_index=True)

ids = [row["id"] for row in filtered]
selected = st.session_state.get("selected_quote", ids[0])
identifier = st.selectbox(
    t("records.select_version"), ids,
    index=ids.index(selected) if selected in ids else 0,
    format_func=lambda quote_id: (
        f"{quote_id} · V{next(row['version'] for row in filtered if row['id'] == quote_id)}"
    ),
    key="records.selected_quote",
)
st.session_state.selected_quote = identifier
row = next(item for item in filtered if item["id"] == identifier)
payload = row["payload"]
st.write(t(
    "records.state_owner", status=status_label(row["status"]),
    owner=role_label(row["owner"]), created=format_date(row["created_at"]),
    updated=format_date(row["updated_at"]),
))
st.subheader(t("records.snapshot"))
st.json(localize_json(payload))
try:
    approvals, operations = audit(identifier)
    st.subheader(t("records.audit"))
    if approvals:
        st.dataframe(localize_records(approvals), hide_index=True)
    else:
        st.caption(t("records.no_approval_log"))
    if operations:
        st.dataframe(localize_records(operations), hide_index=True)
except DatabaseUnavailable as error:
    st.error(display_error(error))

if row["status"] != "approved":
    st.warning(t("records.unapproved"))
st.download_button(
    t("button.download.csv"), csv_export(row),
    file_name=f"{identifier}_V{row['version']}.csv",
    mime="text/csv", key=f"records.download_csv.{identifier}",
)
st.download_button(
    t("button.download.html"), html_export(row),
    file_name=f"{identifier}_V{row['version']}.html",
    mime="text/html", key=f"records.download_html.{identifier}",
)

actor = st.session_state.demo_actor
if row["owner"] == actor and row["status"] == "draft":
    st.subheader(t("records.edit_draft"))
    with st.form(f"records.edit.{identifier}"):
        quantity = st.text_input(t("records.quantity"), value=payload["quantity"], key="records.edit.quantity")
        price = st.text_input(t("records.manual_price"), value=payload["price"], key="records.edit.price")
        delivery = st.date_input(
            t("records.delivery"), value=date.fromisoformat(payload["delivery_date"]),
            key="records.edit.delivery",
        )
        expiry = st.date_input(
            t("records.validity"), value=date.fromisoformat(payload["valid_until"]),
            key="records.edit.validity",
        )
        costs = {
            field: st.text_input(
                field_label(field), value=payload["snapshot"]["costs"][field],
                key=f"records.edit.cost.{index}",
            )
            for index, field in enumerate(COSTS)
        }
        reason = st.text_area(
            t("records.change_reason"), value=payload["snapshot"]["reason"],
            key="records.edit.reason",
        )
        minimum = st.number_input(
            t("quote.minimum_margin"), value=float(payload["snapshot"]["minimum"]),
            key="records.edit.minimum",
        )
        target = st.number_input(
            t("quote.target_margin"), value=float(payload["snapshot"]["target"]),
            key="records.edit.target",
        )
        save = st.form_submit_button(t("records.save_changes"), key="records.edit.submit")
    if save:
        try:
            edit_draft(identifier, dict(
                quantity=quantity, price=price, delivery_date=delivery,
                valid_until=expiry, costs=costs, reason=reason,
                minimum=minimum, target=target,
            ), actor)
            st.rerun()
        except (ValueError, DatabaseUnavailable) as error:
            st.error(display_error(error))
    if st.button(t("button.submit"), type="primary", key=f"records.submit.{identifier}"):
        try:
            submit_quote(identifier, actor)
            st.rerun()
        except (ValueError, DatabaseUnavailable) as error:
            st.error(display_error(error))
elif row["owner"] == actor and row["status"] in ("approved", "rejected"):
    if st.button(t("records.create_revision"), key=f"records.revise.{identifier}"):
        try:
            st.session_state.selected_quote = revise(identifier, actor)
            st.rerun()
        except (ValueError, DatabaseUnavailable) as error:
            st.error(display_error(error))
else:
    if row["status"] == "pending":
        st.info(t("records.pending_locked"))
    else:
        st.info(t("records.read_only", status=status_label(row["status"])))
