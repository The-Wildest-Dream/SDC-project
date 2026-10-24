"""Streamlit application entry point, shared notices, and sidebar navigation."""
from functools import partial

import streamlit as st
from i18n import t, install, LANGS

from pending_page import render_pending


st.set_page_config(
    page_title="制造企业报价辅助系统",
    layout="wide",
    initial_sidebar_state="expanded",
)
with st.sidebar:
    st.selectbox("Language / 语言", LANGS, key="ui_language", index=0,
                 format_func=lambda x: {"zh-CN":"简体中文","en":"English","ms":"Bahasa Melayu"}[x])
install()
st.title(t("app.title"))
st.caption(t("app.subtitle"))
st.info(t("app.demo"))
with st.sidebar:
    st.selectbox(t("role.label"), ["销售甲", "销售乙", "经理"], key="demo_actor",
                 format_func=lambda x: f"{t('role.manager')} · {x}" if x == "经理" else f"{t('role.sales')} · {x}")
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
    st.caption("项目重点：价格分析与报价决策。")
    st.caption("库存和付款表现仅为辅助提醒，不自动采购、授信或承诺交期。")
navigation.run()
