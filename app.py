"""应用入口：公共说明与侧边栏导航。"""
from functools import partial

import streamlit as st

from pending_page import render_pending


st.set_page_config(
    page_title="制造企业报价辅助系统",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.title("中小制造企业报价辅助系统")
st.caption("学生比赛演示 · 价格分析与报价决策")
st.info("所有展示数据均为模拟数据，仅用于教学与比赛演示，不作为实际交易报价。")

pages = [
    st.Page(partial(render_pending, "工作台"), title="工作台",
            url_path="workbench", default=True),
    st.Page("data_page.py", title="数据中心",
            url_path="data"),
    st.Page("quote_page.py", title="新建询价与成本计算", url_path="calculate"),
    st.Page("history_page.py",
            title="历史价格与报价建议", url_path="price-analysis"),
    st.Page(partial(render_pending, "审批中心"), title="审批中心",
            url_path="approvals"),
    st.Page(partial(render_pending, "报价记录与下载"),
            title="报价记录与下载", url_path="records"),
]
navigation = st.navigation(pages, position="sidebar")
with st.sidebar:
    st.caption("项目重点：价格分析与报价决策。")
    st.caption("数据中心可查看模拟库存及客户付款表现；库存提醒待实现。")
navigation.run()
