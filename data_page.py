"""Data Center: synthetic data browsing, CSV validation/import, and payment summaries."""
import streamlit as st

from i18n import kind_label, localize_records, t, t_plural
from data_service import SCHEMAS, csv_bytes, payment_summary
from generate_data import AS_OF, generate
from shared_data import get_data, import_data

st.header(t("data.title"))
st.warning(t("data.warning"))
st.caption(t("data.persisted_note"))
kind = st.selectbox(
    t("data.view_type"), list(SCHEMAS), key="data.kind",
    format_func=kind_label,
)
data = get_data()
st.write(t_plural("data.current_count", len(data[kind])))
st.dataframe(localize_records(data[kind]), use_container_width=True, hide_index=True)
st.download_button(
    t("data.download_sample"), csv_bytes(kind, generate()[kind]),
    file_name=t("data.sample_filename", kind=kind_label(kind)) + ".csv",
    mime="text/csv", key="data.download_sample",
)
st.caption(t("data.sample_note"))

st.subheader(t("data.import_section"))
st.write(t("data.upload_help"))
st.caption(t("data.format_note"))
uploads = {}
for table in SCHEMAS:
    file = st.file_uploader(
        t("data.upload_label", kind=kind_label(table)),
        type=["csv"], key=f"csv_{table}",
    )
    if file is not None:
        uploads[table] = file.getvalue()
confirmed = st.checkbox(t("data.confirm_simulated"), key="data.confirm_simulated")
st.warning(t("data.commit_warning"))
if st.button(
    t("data.validate_save"), disabled=not uploads or not confirmed,
    key="data.validate_save",
):
    errors = import_data(uploads)
    if errors:
        st.error(t("data.import_failed"))
        st.dataframe(localize_records(errors), hide_index=True, use_container_width=True)
        st.caption(t("data.line_note"))
    else:
        st.session_state.import_notice = True
        st.rerun()
if st.session_state.pop("import_notice", False):
    st.success(t("data.import_saved"))

st.subheader(t("data.payments"))
as_of = st.date_input(t("data.as_of"), value=AS_OF, key="data.analysis_date")
st.write(t("data.due_definition"))
st.write(t("data.overdue_definition"))
st.caption(t("data.payment_sample_note"))
summary, detail = payment_summary(get_data(), as_of)
st.dataframe(localize_records(summary), hide_index=True, use_container_width=True)
with st.expander(t("data.order_details")):
    st.dataframe(localize_records(detail), hide_index=True, use_container_width=True)
st.warning(t("data.payment_notice"))
