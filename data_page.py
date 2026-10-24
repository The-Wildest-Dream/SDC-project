"""Data Center: synthetic data browsing, CSV validation/import, and payment summaries."""
import streamlit as st

from data_service import SCHEMAS, csv_bytes, payment_summary
from generate_data import AS_OF, generate
from shared_data import get_data, import_data

st.header("数据中心")
st.warning("模拟数据：请仅上传团队生成的合成数据，不要上传真实客户或交易信息。")
st.caption("有效业务数据保存在 PostgreSQL；刷新或重启后从数据库重新读取，不会自动恢复示例数据。")
kind = st.selectbox("查看数据类型", list(SCHEMAS))
data = get_data()
st.write(f"当前有效数据：{len(data[kind])} 条")
st.dataframe(data[kind], use_container_width=True, hide_index=True)
st.download_button("下载示例CSV（模拟数据）", csv_bytes(kind, generate()[kind]),
                   file_name=f"模拟数据_{kind}.csv", mime="text/csv")
st.caption("示例文件始终来自固定种子，不是当前上传数据的导出。历史交易额外保存单位和币种快照。")

st.subheader("上传并校验")
st.write("可同时上传多类 CSV。按ID合并：新增ID插入、已有ID更新，未上传记录保持不变。"
         "校验会检查整个数据集的引用关系，任一错误都会拒绝本批全部文件。")
st.caption("格式：UTF-8（可含BOM）、中文表头、日期 YYYY-MM-DD；仅实际付款日期允许为空。"
           "库存数量允许为0，交易数量必须大于0，所有金额和库存数量不得为负。")
uploads = {}
for table in SCHEMAS:
    file = st.file_uploader(f"{table}CSV", type=["csv"], key=f"csv_{table}")
    if file is not None:
        uploads[table] = file.getvalue()
confirmed = st.checkbox("我确认上传内容全部为团队生成的模拟数据")
st.warning("通过校验后将在同一数据库事务中保存，已有相同ID的内容会更新；不会删除未上传记录。原计算结果会清除。")
if st.button("校验并保存到数据库", disabled=not uploads or not confirmed):
    errors = import_data(uploads)
    if errors:
        st.error("校验失败：本批数据未应用，原有效数据保持不变。")
        st.dataframe(errors, hide_index=True, use_container_width=True)
        st.caption("行号为CSV物理行号（表头第1行）。跨表错误的数据类型指向发生引用错误的表。")
    else:
        st.session_state.import_notice = True
        st.rerun()
if st.session_state.pop("import_notice", False):
    st.success("校验通过，数据库事务已提交。")

st.subheader("客户付款表现（模拟数据）")
as_of = st.date_input("统计截至日期（日终）", value=AS_OF)
st.write("已到期订单数：订单日期不晚于统计日、约定付款日期 ≤ 统计日的订单数。"
         "按时付款率 = 其中实际付款日期 ≤ 约定付款日期且已在统计日付款的订单数 ÷ 已到期订单数。"
         "到期仍未付款的订单保留在分母；无到期订单时不计算比率。")
st.write("当前逾期未付：约定付款日期 < 统计日，且截至统计日未付款。"
         "历史逾期天数：已付款订单的 max(实际付款日期 − 约定付款日期, 0)，"
         "按客户累计，不包含未付订单；未付逾期天数在明细中单列。")
st.caption("到期样本少于10笔标记“样本不足”；10笔仅为演示提示阈值，不表示统计可靠性。"
           "未来付款日期在所选统计时点视为尚未付款。")
summary, detail = payment_summary(get_data(), as_of)
st.dataframe(summary, hide_index=True, use_container_width=True)
with st.expander("查看逐单逾期天数"):
    st.dataframe(detail, hide_index=True, use_container_width=True)
st.warning("以上仅为模拟订单的付款表现描述，不是“诚信判断”，不自动决定授信、账期或先货后款。")
