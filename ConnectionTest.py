import streamlit as st
from sqlalchemy import text
from utils.db import get_engine

st.title("DB Connection Test")

try:
    with get_engine().connect() as conn:
        result = conn.execute(text("SELECT SUSER_SNAME()"))
        st.success(f"Connected as: {result.scalar()}")
except Exception as e:
    st.error(f"Connection failed: {e}")
