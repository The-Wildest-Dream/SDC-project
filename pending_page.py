"""未实现页面的统一展示，不提供虚构数据或无效操作。"""
import streamlit as st


PAGE_DESCRIPTIONS = {
    "工作台": "业务概览待实现。当前可从侧边栏进入“新建询价与成本计算”使用报价计算器。",
    "审批中心": "报价审批流程待实现。当前不能提交、通过或驳回审批。",
    "报价记录与下载": "报价记录保存、查询与下载待实现。当前计算结果仅用于会话内展示，不是已保存的报价记录。",
}


def render_pending(title):
    st.header(title)
    st.info("待实现")
    st.write(PAGE_DESCRIPTIONS[title])
