# apps/<dashboard_name>/app.py
"""
B4ALL <Dashboard Name> — Streamlit entrypoint.

Copy this file to apps/<your_dashboard>/app.py and customize:
1. Update page_title, page_icon, and the h1 title
2. Add/remove tabs and wire them to your tab modules
3. Run with: streamlit run apps/<your_dashboard>/app.py
"""

import sys
from pathlib import Path

# Add project root to path so core/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

st.set_page_config(
    page_title="B4ALL <Dashboard Name>",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide sidebar and Streamlit chrome for clean embed
st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stHeader"] { display: none; }
    .block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 style="color:#0D1B2A;margin-bottom:0;"><Dashboard Name></h1>', unsafe_allow_html=True)

# --- Tab router ---
# Add one entry per tab. Each tab module must export a render() function.
tab_one, tab_two = st.tabs(["Tab One", "Tab Two"])

with tab_one:
    from apps._template.tabs.example_tab import render as render_one
    render_one()

with tab_two:
    # Wire your second tab here
    st.info("Tab Two — not yet implemented.")
