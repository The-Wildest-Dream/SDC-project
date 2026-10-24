"""Streamlit application entry point, shared notices, and sidebar navigation."""
import streamlit as st
from i18n import t, LANGS, initialize_language, role_label

from pending_page import render_pending


initialize_language()
st.set_page_config(
    page_title=t("app.title"),
    layout="wide",
    initial_sidebar_state="expanded",
)
with st.sidebar:
    st.selectbox(
        t("lang.label"),
        LANGS,
        key="ui_language",
        format_func=lambda code: {
            "zh-CN": t("lang.zh"),
            "en": t("lang.en"),
            "ms-MY": t("lang.ms"),
        }[code],
    )
st.title(t("app.title"))
st.caption(t("app.subtitle"))
st.info(t("app.demo"))
with st.sidebar:
    st.selectbox(
        t("role.label"),
        ["销售甲", "销售乙", "经理"],
        key="demo_actor",
        format_func=lambda actor: role_label(actor),
    )
    st.warning(t("role.warning"))

pages = [
    st.Page("dashboard_page.py", title=t("nav.workbench"),
            url_path="workbench", default=True),
    st.Page("data_page.py", title=t("nav.data"),
            url_path="data"),
    st.Page("quote_page.py", title=t("nav.quote"), url_path="calculate"),
    st.Page("history_page.py",
            title=t("nav.history"), url_path="price-analysis"),
    st.Page("approval_page.py", title=t("nav.approvals"),
            url_path="approvals"),
    st.Page("records_page.py",
            title=t("nav.records"), url_path="records"),
]
navigation = st.navigation(pages, position="sidebar")
with st.sidebar:
    st.caption(t("app.scope"))
    st.caption(t("app.aux_scope"))
navigation.run()
