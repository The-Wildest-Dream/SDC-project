"""新建询价与成本计算页面；业务计算委托给 calculator 模块。"""
import streamlit as st

from calculator import calculate_quote
from shared_data import get_data


st.header("新建询价与成本计算")
st.caption("当前可用：成本与报价计算。询价保存、提交审批待实现；计算不会生成报价记录。")
products = {p["产品ID"]: p for p in get_data()["产品"]}
selected = st.selectbox("读取有效产品成本（模拟数据）", ["手动输入", *products],
                        format_func=lambda key: key if key == "手动输入" else f"{key} · {products[key]['产品名称']}")
product = products.get(selected)
unit = product["单位"] if product else "件"
currency = product["币种"] if product else "CNY"
st.caption(f"计量单位：{unit}；币种：{currency}。成本可手动调整，不自动换汇或换算单位。")

with st.form(f"quote_{selected}"):
    st.subheader("一、产品与采购需求")
    left, right = st.columns(2)
    name = left.text_input("产品名称", value=product["产品名称"] if product else "精密铝合金支架", max_chars=100)
    quantity = right.number_input(f"采购数量（{unit}）", value=100, step=1,
                                  help="请输入大于 0 的整数。")

    st.subheader("二、单位生产成本")
    a, b, c = st.columns(3)
    material = a.number_input(f"单位材料成本（{currency}/{unit}）", min_value=0.0,
                              value=float(product["单位材料成本"]) if product else 30.0, step=1.0, format="%.2f")
    labor = b.number_input(f"单位人工成本（{currency}/{unit}）", min_value=0.0,
                           value=float(product["单位人工成本"]) if product else 15.0, step=1.0, format="%.2f")
    overhead = c.number_input(f"单位制造费用（{currency}/{unit}）", min_value=0.0,
                              value=float(product["单位制造费用"]) if product else 5.0, step=1.0, format="%.2f")

    st.subheader("三、整批费用与目标毛利率")
    a, b, c = st.columns(3)
    fixed = a.number_input(f"整批固定费用（{currency}）", min_value=0.0,
                           value=800.0, step=100.0, format="%.2f")
    logistics = b.number_input(f"整批物流费用（{currency}）", min_value=0.0,
                               value=200.0, step=50.0, format="%.2f")
    margin = c.number_input("目标毛利率（%）", value=20.0, step=1.0,
                            format="%.2f", help="毛利率 =（售价 − 成本）÷ 售价，并非成本加价率。")
    submitted = st.form_submit_button("计算报价", type="primary",
                                      use_container_width=True)

st.caption("修改参数后请重新点击“计算报价”；下方结果对应最近一次提交的数据。")

if submitted:
    st.session_state.pop("quote_result", None)
    try:
        if not name.strip():
            raise ValueError("请输入产品名称。")
        result = calculate_quote(quantity, material, labor, overhead,
                                 fixed, logistics, margin)
        st.session_state.quote_result = {
            "name": name.strip(), "unit": unit, "currency": currency, "quantity": quantity, "material": material,
            "labor": labor, "overhead": overhead, "fixed": fixed,
            "logistics": logistics, "margin": margin, **result,
        }
    except ValueError as error:
        st.error(str(error))

if "quote_result" in st.session_state:
    r = st.session_state.quote_result
    r.setdefault("unit", "件")
    r.setdefault("currency", "CNY")
    st.subheader("报价结果")
    st.write(f"产品：{r['name']} ｜ 采购数量：{r['quantity']:,} {r['unit']} ｜ "
             f"目标毛利率：{r['margin']:g}%")
    a, b, c = st.columns(3)
    a.metric(f"单位成本（{r['currency']}/{r['unit']}）", f"{r['unit_cost']:,.2f}")
    b.metric(f"参考单价（{r['currency']}/{r['unit']}）", f"{r['unit_price']:,.2f}")
    c.metric(f"整单报价（{r['currency']}）", f"{r['total']:,.2f}")
    st.caption("金额显示保留两位小数；计算过程中不提前舍入。整单报价可能与显示单价乘数量略有差异。")
    with st.expander("查看本次数据代入过程", expanded=True):
        st.text(
            f"单位成本 = {r['material']:.2f} + {r['labor']:.2f} + {r['overhead']:.2f}"
            f" + ({r['fixed']:.2f} + {r['logistics']:.2f}) / {r['quantity']}"
            f"\n         ≈ {r['unit_cost']:.6f} {r['currency']}/{r['unit']}\n\n"
            f"参考单价 = 单位成本 / (1 − {r['margin']:g}%)"
            f"\n         ≈ {r['unit_price']:.6f} {r['currency']}/{r['unit']}\n\n"
            f"整单报价 = 未舍入的参考单价 × {r['quantity']}"
            f"\n         ≈ {r['total']:.2f} {r['currency']}"
        )
else:
    st.info("填写以上模拟参数，点击“计算报价”查看单位成本、参考单价与整单报价。")

st.divider()
st.subheader("计算公式与口径")
st.code(
    "单位成本 = 单位材料成本 + 单位人工成本 + 单位制造费用\n"
    "         + (整批固定费用 + 整批物流费用) / 采购数量\n\n"
    "参考单价 = 单位成本 / (1 − 目标毛利率)\n\n"
    "整单报价 = 参考单价 × 采购数量", language=None
)
st.write("目标毛利率按百分比输入：例如输入 20，计算时使用 0.20。"
         "整批固定费用与物流费用按采购数量平均分摊。")
st.caption("产品成本来自数据库；本页计算结果仍是未保存草稿。询价及报价保存流程待实现，不涉及税费或机器学习。")
