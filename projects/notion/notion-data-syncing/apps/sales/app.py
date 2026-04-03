# apps/sales/app.py
"""B4ALL Sales Dashboard — Streamlit entrypoint."""

import sys
from pathlib import Path

# Add project root to path so core/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

st.set_page_config(
    page_title="B4ALL Sales Dashboard",
    page_icon="📈",
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

st.markdown('<h1 style="color:#0D1B2A;margin-bottom:0;">Sales Dashboard</h1>', unsafe_allow_html=True)

# Tab router
tab_rfp, tab_deals, tab_opp, tab_prospects, tab_states, tab_inbox = st.tabs([
    "RFP Pipeline", "Deals", "Opportunities", "Prospects", "State Profiles", "Inbox",
])

with tab_rfp:
    from apps.sales.tabs.rfp_pipeline import render as render_rfp
    render_rfp()

with tab_deals:
    from apps.sales.tabs.deals import render as render_deals
    render_deals()

with tab_opp:
    from apps.sales.tabs.opportunities import render as render_opp
    render_opp()

with tab_prospects:
    from apps.sales.tabs.prospects import render as render_prospects
    render_prospects()

with tab_states:
    from apps.sales.tabs.state_profiles import render as render_states
    render_states()

with tab_inbox:
    from apps.sales.tabs.inbox import render as render_inbox
    render_inbox()
