"""revenue_gross_trend — Gross revenue stacked bar by business line with YoY annotations."""

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

    # Filter to months with at least 2 business lines (complete months)
    month_biz = df.groupby("report_month")["business_line"].nunique()
    real_months = month_biz[month_biz >= 2].index
    df = df[df["report_month"].isin(real_months)]

    monthly = (df.groupby(["report_month", "business_line"])["gross_revenue"]
               .sum().reset_index().sort_values("report_month"))
    chart_df = monthly[monthly["report_month"] >= "2025-01-01"]

    if chart_df.empty:
        st.info("No revenue data from 2025 onward.")
        return

    # YoY annotations
    month_totals = df.groupby("report_month")["gross_revenue"].sum().to_dict()
    yoy_annotations = {}
    for m in chart_df["report_month"].unique():
        prior = m - pd.DateOffset(years=1)
        if prior in month_totals and month_totals[prior] > 0:
            pct = (month_totals[m] - month_totals[prior]) / month_totals[prior] * 100
            yoy_annotations[m] = (pct, month_totals[m])

    fig = go.Figure()
    for biz in ["SaaS Platform", "SaaS Relay", "Support Fees", "Solutions"]:
        d = chart_df[chart_df["business_line"] == biz]
        if d.empty:
            continue
        fig.add_trace(go.Bar(
            x=d["report_month"], y=d["gross_revenue"],
            name=biz,
            marker=dict(color=BIZ_COLORS.get(biz, CHART_COLORS[0]), cornerradius=2),
            hovertemplate="%{x|%b %Y}<br>" + biz + ": <b>$%{y:,.0f}</b><extra></extra>",
        ))

    for m, (pct, total) in yoy_annotations.items():
        sign = "+" if pct >= 0 else ""
        color = PALETTE["green"] if pct >= 0 else PALETTE["red"]
        fig.add_annotation(
            x=m, y=total, text=f"<b>{sign}{pct:.0f}%</b>",
            showarrow=False, yshift=12,
            font=dict(size=10, color=color),
        )

    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        barmode="stack",
        showlegend=True,
        legend=dict(orientation="h", y=-0.12, x=0,
                    font=dict(size=11, color=PALETTE["secondary"])),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        yaxis=dict(gridcolor=PALETTE["grid"], tickprefix="$", tickformat=","),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("Gross Revenue", DEFAULT_HEIGHT)
    render()
