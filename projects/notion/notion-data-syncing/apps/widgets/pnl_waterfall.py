"""pnl_waterfall — Monthly P&L bridge: revenue by business line, COGS deductions, gross profit."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, PALETTE

DEFAULT_HEIGHT = 420

BIZ_ORDER = ["SaaS Platform", "SaaS Relay", "Solutions", "Support"]


def render():
    df = query_view("pnl_monthly")
    if df.empty:
        st.warning("No P&L data available.")
        return

    df["month_start"] = pd.to_datetime(df["month_start"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    # Latest complete month (has both Revenue and COGS)
    has_both = (df.groupby("month_start")["pnl_section"].nunique() >= 2)
    complete = has_both[has_both].index
    if complete.empty:
        st.info("No complete P&L month available.")
        return
    latest = complete.max()
    month_df = df[df["month_start"] == latest]

    # Build waterfall measures
    labels, values, measures, colors = [], [], [], []

    # Revenue items
    rev = month_df[month_df["pnl_section"] == "Revenue"]
    rev_by_biz = rev.groupby("business_line")["amount"].sum().reindex(BIZ_ORDER).dropna()
    for biz, amt in rev_by_biz.items():
        labels.append(biz)
        values.append(amt)
        measures.append("relative")
        colors.append("#2B7BE9")

    # Revenue subtotal
    total_rev = rev_by_biz.sum()
    labels.append("Total Revenue")
    values.append(total_rev)
    measures.append("total")
    colors.append("#1A5FC7")

    # COGS items (negative)
    cogs = month_df[month_df["pnl_section"] == "COGS"]
    cogs_by_biz = cogs.groupby("business_line")["amount"].sum()
    for biz, amt in cogs_by_biz.items():
        labels.append(f"COGS: {biz}")
        values.append(-amt)
        measures.append("relative")
        colors.append("#E74C3C")

    # Gross profit total
    total_cogs = cogs_by_biz.sum()
    gross_profit = total_rev - total_cogs
    labels.append("Gross Profit")
    values.append(gross_profit)
    measures.append("total")
    colors.append("#22C55E")

    margin_pct = (gross_profit / total_rev * 100) if total_rev else 0

    fig = go.Figure()
    fig.add_trace(go.Waterfall(
        x=labels, y=values, measure=measures,
        connector=dict(line=dict(color=PALETTE["border"], width=1, dash="dot")),
        decreasing=dict(marker=dict(color="#E74C3C")),
        increasing=dict(marker=dict(color="#2B7BE9")),
        totals=dict(marker=dict(color="#0D1B2A")),
        texttemplate="%{y:$,.0f}",
        textposition="outside",
        textfont=dict(size=10, family="Inter"),
        hovertemplate="%{x}<br><b>%{y:$,.0f}</b><extra></extra>",
    ))

    # Margin annotation on Gross Profit bar
    fig.add_annotation(
        x="Gross Profit", y=gross_profit,
        text=f"<b>{margin_pct:.0f}% margin</b>",
        showarrow=False, yshift=28,
        font=dict(size=12, color=PALETTE["green"]),
    )

    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        margin=dict(l=0, r=0, t=16, b=80),
        xaxis=dict(
            gridcolor="rgba(0,0,0,0)",
            tickangle=-35,
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            gridcolor=PALETTE["grid"],
            tickprefix="$", tickformat=",",
        ),
    ))

    # Month label
    month_label = latest.strftime("%B %Y")
    st.html(f'<div style="font-size:11px;color:{PALETTE["tertiary"]};margin-bottom:2px;">{month_label}</div>')
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("P&L Waterfall", DEFAULT_HEIGHT)
    render()
