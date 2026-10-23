"""学生比赛演示：中小制造企业报价辅助系统。"""
import streamlit as st

from calculator import calculate_quote


st.set_page_config(page_title="制造企业报价辅助系统", layout="wide")
st.title("中小制造企业报价辅助系统")
st.caption("学生比赛演示 · 第一阶段 / 报价计算器")
st.info("所有展示数据均为模拟数据，仅用于教学与比赛演示，不作为实际交易报价。")

with st.form("quote"):
    st.subheader("一、产品与采购需求")
    left, right = st.columns(2)
    name = left.text_input("产品名称", value="精密铝合金支架", max_chars=100)
    quantity = right.number_input("采购数量（件）", value=100, step=1,
                                  help="请输入大于 0 的整数。")

    st.subheader("二、单位生产成本")
    a, b, c = st.columns(3)
    material = a.number_input("单位材料成本（元/件）", min_value=0.0,
                              value=30.0, step=1.0, format="%.2f")
    labor = b.number_input("单位人工成本（元/件）", min_value=0.0,
                           value=15.0, step=1.0, format="%.2f")
    overhead = c.number_input("单位制造费用（元/件）", min_value=0.0,
                              value=5.0, step=1.0, format="%.2f")

    st.subheader("三、整批费用与目标毛利率")
    a, b, c = st.columns(3)
    fixed = a.number_input("整批固定费用（元）", min_value=0.0,
                           value=800.0, step=100.0, format="%.2f")
    logistics = b.number_input("整批物流费用（元）", min_value=0.0,
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
            "name": name.strip(), "quantity": quantity, "material": material,
            "labor": labor, "overhead": overhead, "fixed": fixed,
            "logistics": logistics, "margin": margin, **result,
        }
    except ValueError as error:
        st.error(str(error))

if "quote_result" in st.session_state:
    r = st.session_state.quote_result
    st.subheader("报价结果")
    st.write(f"产品：{r['name']} ｜ 采购数量：{r['quantity']:,} 件 ｜ "
             f"目标毛利率：{r['margin']:g}%")
    a, b, c = st.columns(3)
    a.metric("单位成本（元/件）", f"¥ {r['unit_cost']:,.2f}")
    b.metric("参考单价（元/件）", f"¥ {r['unit_price']:,.2f}")
    c.metric("整单报价（元）", f"¥ {r['total']:,.2f}")
    st.caption("金额显示保留两位小数；计算过程中不提前舍入。整单报价可能与显示单价乘数量略有差异。")
    with st.expander("查看本次数据代入过程", expanded=True):
        st.text(
            f"单位成本 = {r['material']:.2f} + {r['labor']:.2f} + {r['overhead']:.2f}"
            f" + ({r['fixed']:.2f} + {r['logistics']:.2f}) / {r['quantity']}"
            f"\n         ≈ {r['unit_cost']:.6f} 元/件\n\n"
            f"参考单价 = 单位成本 / (1 − {r['margin']:g}%)"
            f"\n         ≈ {r['unit_price']:.6f} 元/件\n\n"
            f"整单报价 = 未舍入的参考单价 × {r['quantity']}"
            f"\n         ≈ {r['total']:.2f} 元"
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
st.caption("本阶段不涉及税费处理、数据库或机器学习；数据仅保留在当前会话中，不作持久化保存。")
