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
    from apps.finance.tabs.pnl import render as render_pnl
    render_pnl()

with tab_ar:
    from apps.finance.tabs.ar_aging import render as render_ar
    render_ar()

with tab_variance:
    from apps.finance.tabs.variance import render as render_variance
    render_variance()

with tab_inbox:
    from apps.finance.tabs.accounting_inbox import render as render_inbox
    render_inbox()
