"""revenue_business_mix — % of gross revenue by business line, stacked area."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, CHART_COLORS, PALETTE

DEFAULT_HEIGHT = 340

BIZ_COLORS = {
    "SaaS Platform": CHART_COLORS[0],
    "SaaS Relay":    CHART_COLORS[1],
    "Support Fees":  CHART_COLORS[2],
    "Solutions":     CHART_COLORS[3],
}


def render():
    df = query_view("revenue_decomposition")
    if df.empty:
        st.warning("No revenue data available.")
        return

    df["report_month"] = pd.to_datetime(df["report_month"], errors="coerce")
    df["gross_revenue"] = pd.to_numeric(df["gross_revenue"], errors="coerce").fillna(0)

    mix = (df[(df["report_month"] >= "2025-01-01") & (df["report_month"] <= "2026-03-31")]
           .groupby(["report_month", "business_line"])["gross_revenue"]
           .sum().reset_index())
    mix_totals = mix.groupby("report_month")["gross_revenue"].transform("sum")
    mix["share_pct"] = (mix["gross_revenue"] / mix_totals * 100).round(1)

    if mix.empty:
        st.info("No data from 2025 onward.")
        return

    fig = go.Figure()
    for biz in ["SaaS Platform", "SaaS Relay", "Support Fees", "Solutions"]:
        d = mix[mix["business_line"] == biz].sort_values("report_month")
        if d.empty:
            continue
        fig.add_trace(go.Scatter(
            x=d["report_month"], y=d["share_pct"],
            name=biz, stackgroup="one",
            line=dict(width=0.5, color=BIZ_COLORS.get(biz, CHART_COLORS[0])),
            hovertemplate="%{x|%b %Y}<br>" + biz + ": <b>%{y:.1f}%</b><extra></extra>",
        ))

    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        showlegend=True,
        legend=dict(orientation="h", y=-0.12, x=0,
                    font=dict(size=11, color=PALETTE["secondary"])),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        yaxis=dict(gridcolor=PALETTE["grid"], range=[0, 100], ticksuffix="%"),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("Business Mix", DEFAULT_HEIGHT)
    render()
