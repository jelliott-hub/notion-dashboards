"""support_answer_rate — Weekly answer rate trend with 80% target line."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, PALETTE

DEFAULT_HEIGHT = 340


def render():
    calls = query_view("calls_weekly")
    if calls.empty or "answer_rate" not in calls.columns:
        st.warning("No call data available.")
        return

    calls["call_week"] = pd.to_datetime(calls["call_week"], errors="coerce")
    for c in ["answered", "total_calls"]:
        if c in calls.columns:
            calls[c] = pd.to_numeric(calls[c], errors="coerce").fillna(0)

    wk_agg = (calls.groupby("call_week")
              .agg(answered=("answered", "sum"),
                   total=("total_calls", "sum"))
              .reset_index().sort_values("call_week"))
    wk_agg["rate"] = (wk_agg["answered"] / wk_agg["total"] * 100).fillna(0)

    fig = go.Figure()

    # 80% target line
    fig.add_hline(
        y=80,
        line=dict(color=PALETTE["border"], width=1, dash="dot"),
        annotation=dict(text="80% target", font=dict(
            size=10, color=PALETTE["tertiary"])),
    )

    fig.add_trace(go.Scatter(
        x=wk_agg["call_week"], y=wk_agg["rate"],
        mode="lines+markers",
        line=dict(color=PALETTE["blue_dark"], width=2.5, shape="spline"),
        marker=dict(size=5, color=PALETTE["blue_dark"]),
        fill="tozeroy",
        fillcolor="rgba(26,95,199,0.06)",
        hovertemplate="%{x|%b %d}<br><b>%{y:.1f}%</b><extra></extra>",
    ))
    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        yaxis=dict(gridcolor=PALETTE["grid"], range=[0, 105]),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("Answer Rate", DEFAULT_HEIGHT)
    render()
