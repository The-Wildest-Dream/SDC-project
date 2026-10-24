"""Shared page data access; all persisted business data is read from PostgreSQL."""
import streamlit as st

from database import read_data, import_csv, DatabaseUnavailable


def get_data():
    # Remove legacy session business data; never use it as a database-failure fallback.
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
