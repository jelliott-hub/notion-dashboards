"""pnl_margin_trend — Stacked revenue bars + COGS overlay + gross margin % line (dual axis)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, CHART_COLORS, PALETTE

DEFAULT_HEIGHT = 400

BIZ_COLORS = {
    "SaaS Platform": "#2B7BE9",
    "SaaS Relay":    "#1A5FC7",
    "Solutions":     "#F59E0B",
    "Support":       "#94A3B8",
}


def render():
    df = query_view("pnl_monthly")
    if df.empty:
        st.warning("No P&L data available.")
        return

    df["month_start"] = pd.to_datetime(df["month_start"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df = df.dropna(subset=["month_start"])

    # Revenue by business line
    rev = df[df["pnl_section"] == "Revenue"]
    rev_pivot = rev.pivot_table(index="month_start", columns="business_line",
                                 values="amount", aggfunc="sum").fillna(0)

    # COGS total by month
    cogs = df[df["pnl_section"] == "COGS"]
    cogs_monthly = cogs.groupby("month_start")["amount"].sum()

    # Margin %
    rev_monthly = rev.groupby("month_start")["amount"].sum()
    margin_pct = ((rev_monthly - cogs_monthly) / rev_monthly * 100).fillna(0)

    fig = go.Figure()

    # Stacked revenue bars
    for biz in ["SaaS Platform", "SaaS Relay", "Solutions", "Support"]:
        if biz not in rev_pivot.columns:
            continue
        fig.add_trace(go.Bar(
            x=rev_pivot.index, y=rev_pivot[biz],
            name=biz,
            marker=dict(color=BIZ_COLORS.get(biz, CHART_COLORS[0]), cornerradius=2),
            hovertemplate="%{x|%b %Y}<br>" + biz + ": <b>$%{y:,.0f}</b><extra></extra>",
            yaxis="y",
        ))

    # COGS as a semi-transparent overlay bar
    fig.add_trace(go.Bar(
        x=cogs_monthly.index, y=cogs_monthly.values,
        name="COGS",
        marker=dict(color="rgba(231,76,60,0.25)", line=dict(color="#E74C3C", width=1.5)),
        hovertemplate="%{x|%b %Y}<br>COGS: <b>$%{y:,.0f}</b><extra></extra>",
        yaxis="y",
    ))

    # Margin % line on secondary axis
    fig.add_trace(go.Scatter(
        x=margin_pct.index, y=margin_pct.values,
        name="Gross Margin %",
        mode="lines+markers",
        line=dict(color="#22C55E", width=2.5, shape="spline"),
        marker=dict(size=6, color="#22C55E", line=dict(color="white", width=1.5)),
        hovertemplate="%{x|%b %Y}<br>Margin: <b>%{y:.1f}%</b><extra></extra>",
        yaxis="y2",
    ))

    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        barmode="stack",
        showlegend=True,
        legend=dict(
            orientation="h", y=-0.15, x=0.5, xanchor="center",
            font=dict(size=10, color=PALETTE["secondary"]),
        ),
        margin=dict(l=0, r=48, t=8, b=60),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        yaxis=dict(
            gridcolor=PALETTE["grid"],
            tickprefix="$", tickformat=",",
            title=None,
        ),
        yaxis2=dict(
            overlaying="y", side="right",
            range=[0, 100],
            ticksuffix="%",
            tickfont=dict(size=10, color="#22C55E"),
            gridcolor="rgba(0,0,0,0)",
            zeroline=False, showline=False,
            title=None,
        ),
    ))

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("Revenue & Margin Trend", DEFAULT_HEIGHT)
    render()
