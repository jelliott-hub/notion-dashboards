"""pnl_showcase — All 5 P&L widget styles in one page for comparison."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
from core.style import inject_css, section_label, page_header

st.set_page_config(page_title="P&L Widget Showcase", page_icon="◆", layout="wide")
inject_css()

st.html(page_header("P&L Widget Showcase", "5 styles, same data — pick your favorites"))

# ── 1. Waterfall ────────────────────────────────────────────────────
st.html(section_label("1 / Waterfall — latest month P&L bridge"))
with st.container(border=True):
    from apps.widgets.pnl_waterfall import render as waterfall_render
    waterfall_render()

# ── 2. Margin Trend ─────────────────────────────────────────────────
st.html(section_label("2 / Revenue + Margin Trend — stacked bars, dual axis"))
with st.container(border=True):
    from apps.widgets.pnl_margin_trend import render as margin_render
    margin_render()

# ── 3. Small Multiples / Sparklines ─────────────────────────────────
st.html(section_label("3 / Small Multiples — sparkline card per business line"))
from apps.widgets.pnl_sparklines import render as spark_render
spark_render()

# ── 4. Sankey Flow ──────────────────────────────────────────────────
st.html(section_label("4 / Sankey — revenue flow from BL through to GP vs COGS"))
with st.container(border=True):
    from apps.widgets.pnl_sankey import render as sankey_render
    sankey_render()

# ── 5. Heatmap Grid ─────────────────────────────────────────────────
st.html(section_label("5 / Heatmap — month x business line intensity grid"))
with st.container(border=True):
    from apps.widgets.pnl_heatmap import render as heatmap_render
    heatmap_render()
