# apps/support/app.py
"""B4ALL Support Dashboard — Streamlit entrypoint."""

import sys
from pathlib import Path

# Add project root to path so core/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

st.set_page_config(
    page_title="B4ALL Support Dashboard",
    page_icon="🎧",
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

st.markdown('<h1 style="color:#0D1B2A;margin-bottom:0;">Support Dashboard</h1>', unsafe_allow_html=True)

# Tab router
tab_weekly, tab_topic, tab_agent, tab_tickets = st.tabs([
    "Calls Weekly", "Calls by Topic", "Calls by Agent", "Tickets",
])

with tab_weekly:
    from apps.support.tabs.calls_weekly import render as render_weekly
    render_weekly()

with tab_topic:
    from apps.support.tabs.calls_by_topic import render as render_topic
    render_topic()

with tab_agent:
    from apps.support.tabs.calls_by_agent import render as render_agent
    render_agent()

with tab_tickets:
    from apps.support.tabs.tickets import render as render_tickets
    render_tickets()
