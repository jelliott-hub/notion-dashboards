"""revenue_conc_trend — Top-N share of TTM revenue trend (multi-line)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, CHART_COLORS, PALETTE

DEFAULT_HEIGHT = 380


def render():
    df = query_view("customer_concentration_trend")
    if df.empty:
        st.warning("No concentration trend data available.")
        return

    df["evaluation_month"] = pd.to_datetime(df["evaluation_month"], errors="coerce")
    for c in ["top1_share_pct", "top5_share_pct", "top10_share_pct", "top20_share_pct"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    trend = df[
        (df["cut_dimension"] == "Overall")
        & (df["cut_value"] == "All Revenue")
        & (df["evaluation_month"] >= "2025-01-01")
    ].sort_values("evaluation_month")

    if trend.empty:
        st.info("No 2025+ concentration trend data.")
        return

    fig = go.Figure()
    for col, label, color in [
        ("top1_share_pct",  "Top-1",  PALETTE["red"]),
        ("top5_share_pct",  "Top-5",  PALETTE["amber"]),
        ("top10_share_pct", "Top-10", CHART_COLORS[0]),
        ("top20_share_pct", "Top-20", PALETTE["secondary"]),
    ]:
        fig.add_trace(go.Scatter(
            x=trend["evaluation_month"], y=trend[col],
            name=label, mode="lines",
            line=dict(color=color, width=2.5, shape="spline"),
            hovertemplate="%{x|%b %Y}<br>" + label + ": <b>%{y:.1f}%</b><extra></extra>",
        ))

    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        showlegend=True,
        legend=dict(orientation="h", y=-0.15, x=0,
                    font=dict(size=11, color=PALETTE["secondary"])),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        yaxis=dict(gridcolor=PALETTE["grid"], ticksuffix="%", range=[0, 75]),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("Concentration Trend", DEFAULT_HEIGHT)
    render()
