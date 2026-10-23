"""所有页面共用的数据入口；仅当前 Streamlit 会话有效。"""
from copy import deepcopy

import streamlit as st

from data_service import prepare_import
from generate_data import generate


def get_data():
    if "validated_data" not in st.session_state:
        st.session_state.validated_data = generate()
    return deepcopy(st.session_state.validated_data)


def import_data(uploads):
    candidate, errors = prepare_import(get_data(), uploads)
    if not errors:
        st.session_state.validated_data = candidate
        st.session_state.pop("quote_result", None)
    return errors
