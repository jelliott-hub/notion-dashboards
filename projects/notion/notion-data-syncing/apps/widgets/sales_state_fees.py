"""sales_state_fees — Applicant cost by state, horizontal bar chart."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, CHART_COLORS, PALETTE

DEFAULT_HEIGHT = 500


def render():
    df = query_view("sales_state_profiles")
    if df.empty or "state_abbr" not in df.columns:
        st.warning("No state profile data available.")
        return

    # Prefer est_total_applicant_cost, fall back to typical_rolling_fee
    fee_col = None
    for candidate in ["est_total_applicant_cost", "typical_rolling_fee", "state_processing_fee"]:
        if candidate in df.columns:
            fee_col = candidate
            break
    if fee_col is None:
        st.warning("No fee columns available.")
        return

    df[fee_col] = pd.to_numeric(df[fee_col], errors="coerce").fillna(0)
    fee_df = df[["state_abbr", fee_col]].copy()
    fee_df = fee_df[fee_df[fee_col] > 0].sort_values(fee_col)

    if fee_df.empty:
        st.warning("No state fee data to display.")
        return

    # Color bars: highlight top-5 most expensive
    n = len(fee_df)
    colors = [CHART_COLORS[0]] * n
    for i in range(max(0, n - 5), n):
        colors[i] = CHART_COLORS[1]  # dark blue for top 5

    label = fee_col.replace("_", " ").title()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=fee_df["state_abbr"],
        x=fee_df[fee_col],
        orientation="h",
        marker=dict(color=colors, cornerradius=4),
        text=[f"${v:,.2f}" for v in fee_df[fee_col]],
        textposition="auto",
        textfont=dict(size=10, family="Inter"),
        hovertemplate="%{y}<br><b>$%{x:,.2f}</b><extra></extra>",
    ))
    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        margin=dict(l=0, r=16, t=8, b=0),
        xaxis=dict(
            gridcolor=PALETTE["grid"],
            title=dict(text=label, font=dict(size=11, color=PALETTE["secondary"])),
        ),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", automargin=True),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("State Fees", DEFAULT_HEIGHT)
    render()
