"""页面共享数据入口：所有已保存业务数据均从 PostgreSQL 读取。"""
import streamlit as st

from database import read_data, import_csv, DatabaseUnavailable


def get_data():
    # 清理旧版本遗留的会话业务数据，绝不作为数据库故障的后备数据。
    st.session_state.pop("validated_data", None)
    try:
        return read_data()
    except DatabaseUnavailable as error:
        st.error(str(error))
        st.stop()


def import_data(uploads):
    try:
        errors = import_csv(uploads)
    except DatabaseUnavailable as error:
        st.error(str(error))
        st.stop()
    if not errors:
        st.session_state.pop("quote_result", None)
    return errors
