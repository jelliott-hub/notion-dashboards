"""revenue_fee_decomp — Revenue per scan fee decomposition (processing + gov + sam), stacked area."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, CHART_COLORS, PALETTE

DEFAULT_HEIGHT = 340


def render():
    df = query_view("unit_economics_monthly")
    if df.empty:
        st.warning("No unit economics data available.")
        return

    df["report_month"] = pd.to_datetime(df["report_month"], errors="coerce")
    for c in ["processing_per_scan", "gov_per_scan", "sam_per_scan"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    plat = (df[(df["business_line"] == "SaaS Platform")
               & (df["report_month"] >= "2025-01-01")]
            .sort_values("report_month"))

    if plat.empty:
        st.info("No Platform unit economics from 2025 onward.")
        return

    fig = go.Figure()
    for col, label, color in [
        ("processing_per_scan", "Processing", CHART_COLORS[0]),
        ("gov_per_scan", "Gov Fee", CHART_COLORS[2]),
        ("sam_per_scan", "SAM Fee", CHART_COLORS[1]),
    ]:
        fig.add_trace(go.Scatter(
            x=plat["report_month"], y=plat[col].fillna(0),
            name=label, stackgroup="one",
            line=dict(width=0.5, color=color),
            hovertemplate="%{x|%b %Y}<br>" + label + ": <b>$%{y:.2f}</b><extra></extra>",
        ))

    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        showlegend=True,
        legend=dict(orientation="h", y=-0.12, x=0,
                    font=dict(size=11, color=PALETTE["secondary"])),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        yaxis=dict(gridcolor=PALETTE["grid"], tickprefix="$"),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("Revenue per Scan", DEFAULT_HEIGHT)
    render()
