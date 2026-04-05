"""revenue_fee_trend — Processing fee per scan: platform vs relay trend line."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, CHART_COLORS, PALETTE

DEFAULT_HEIGHT = 260


def render():
    df = query_view("unit_economics_monthly")
    if df.empty:
        st.warning("No unit economics data available.")
        return

    df["report_month"] = pd.to_datetime(df["report_month"], errors="coerce")
    df["processing_per_scan"] = pd.to_numeric(df["processing_per_scan"], errors="coerce").fillna(0)

    fee_trend = df[df["report_month"] >= "2025-01-01"].sort_values("report_month")
    if fee_trend.empty:
        st.info("No 2025+ fee trend data.")
        return

    fig = go.Figure()
    for biz, color in [("SaaS Platform", CHART_COLORS[0]), ("SaaS Relay", CHART_COLORS[1])]:
        d = fee_trend[fee_trend["business_line"] == biz]
        if d.empty:
            continue
        fig.add_trace(go.Scatter(
            x=d["report_month"], y=d["processing_per_scan"],
            name=biz, mode="lines+markers",
            line=dict(color=color, width=2.5, shape="spline"),
            marker=dict(size=5),
            hovertemplate="%{x|%b %Y}<br>" + biz + ": <b>$%{y:.2f}</b>/scan<extra></extra>",
        ))

    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        showlegend=True,
        legend=dict(orientation="h", y=-0.18, x=0,
                    font=dict(size=11, color=PALETTE["secondary"])),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        yaxis=dict(gridcolor=PALETTE["grid"], tickprefix="$"),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("Processing Fee Trend", DEFAULT_HEIGHT)
    render()
