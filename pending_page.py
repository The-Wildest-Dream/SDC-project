"""Shared display for unimplemented pages; do not show fabricated data or nonfunctional actions."""
import streamlit as st
from i18n import t


PAGE_DESCRIPTIONS = {
    "dashboard": "pending.dashboard",
    "approvals": "pending.approvals",
    "records": "pending.records",
}
PAGE_TITLES = {
    "dashboard": "dashboard.title",
    "approvals": "approval.title",
    "records": "records.title",
}


def render_pending(page_key):
    st.header(t(PAGE_TITLES[page_key]))
    st.info(t("common.pending"))
    st.write(t(PAGE_DESCRIPTIONS[page_key]))
