import streamlit as st

from database import DatabaseUnavailable
from i18n import display_error, localize_json, t
from quote_exports import fields
from workflow_service import decide, records


st.header(t("approval.title"))
st.caption(t("approval.caption"))
try:
    rows = [row for row in records() if row["status"] == "pending"]
except DatabaseUnavailable as error:
    st.error(display_error(error))
    st.stop()
if not rows:
    st.info(t("approval.no_pending"))
    st.stop()
st.metric(t("approval.pending_count"), len(rows))
st.dataframe([fields(row) for row in rows], hide_index=True)
identifier = st.selectbox(
    t("approval.select"), [row["id"] for row in rows],
    key="approval.quote_id",
)
row = next(item for item in rows if item["id"] == identifier)
st.json(localize_json(row["payload"]))
if st.session_state.demo_actor != "经理":
    st.info(t("approval.sales_view"))
    st.stop()
comment = st.text_area(t("approval.comment"), key="approval.comment")
approved = st.radio(
    t("approval.decision"), ["批准", "驳回"], key="approval.decision",
    format_func=lambda value: t("button.approve") if value == "批准" else t("button.reject"),
)
if st.button(t("button.confirm"), type="primary", key="approval.confirm"):
    try:
        decide(identifier, approved == "批准", comment, st.session_state.demo_actor)
        st.success(t("approval.saved"))
        st.page_link("records_page.py", label=t("approval.open_records"))
    except (ValueError, DatabaseUnavailable) as error:
        st.error(display_error(error))
