# apps/finance/app.py
"""B4ALL Finance Dashboard — Streamlit entrypoint."""

import sys
from pathlib import Path

# Add project root to path so core/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

st.set_page_config(
    page_title="B4ALL Finance Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide sidebar and Streamlit chrome for clean Notion embed
st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stHeader"] { display: none; }
    .block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 style="color:#0D1B2A;margin-bottom:0;">Finance Dashboard</h1>', unsafe_allow_html=True)

# Tab router
tab_close, tab_pnl, tab_ar, tab_variance, tab_inbox = st.tabs([
    "Close Dashboard", "P&L Reconciliation", "AR Aging", "Variance Analysis", "Accounting Inbox",
])

with tab_close:
    from apps.finance.tabs.close_dashboard import render as render_close
    render_close()

with tab_pnl:
    st.info("P&L Reconciliation — coming next task")

with tab_ar:
    st.info("AR Aging — coming soon")

with tab_variance:
    st.info("Variance Analysis — coming soon")

with tab_inbox:
    st.info("Accounting Inbox — coming soon")
