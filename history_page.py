"""仅提供有效历史数据读取，不实现自动报价建议。"""
import streamlit as st
from data_service import comparable_transactions
from shared_data import get_data

st.header("历史价格与报价建议")
st.caption("模拟数据 · 当前仅提供历史交易读取，价格分析与报价建议待实现。")
data = get_data()
products = {p["产品ID"]: p for p in data["产品"]}
if not products:
    st.info("数据库暂无产品。请先在数据中心导入模拟产品数据。")
    st.stop()
product_id = st.selectbox("选择产品", list(products),
                         format_func=lambda key: f"{key} · {products[key]['产品名称']}")
product = products[product_id]
st.info(f"仅显示同一产品ID、币种（{product['币种']}）和计量单位（{product['单位']}）的交易；不换汇、不换算单位。")
st.dataframe(comparable_transactions(data, product_id), hide_index=True, use_container_width=True)
