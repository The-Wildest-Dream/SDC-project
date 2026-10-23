"""未实现页面的统一展示，不提供虚构数据或无效操作。"""
import streamlit as st


PAGE_DESCRIPTIONS = {
    "工作台": "业务概览待实现。当前可从侧边栏进入“新建询价与成本计算”使用报价计算器。",
    "审批中心": "审批处理界面待实现。历史价格页已可提交审批并保存记录；通过、驳回操作尚未实现。",
    "报价记录与下载": "独立记录列表及下载待实现。提交审批时已保存报价版本，可在数据库查看。",
}


def render_pending(title):
    st.header(title)
    st.info("待实现")
    st.write(PAGE_DESCRIPTIONS[title])
