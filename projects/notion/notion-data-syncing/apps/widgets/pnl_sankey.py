"""pnl_sankey — Revenue flows from business lines through to gross profit vs COGS."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, PALETTE

DEFAULT_HEIGHT = 440

BIZ_ORDER = ["SaaS Platform", "SaaS Relay", "Solutions", "Support"]


def render():
    df = query_view("pnl_monthly")
    if df.empty:
        st.warning("No P&L data available.")
        return

    df["month_start"] = pd.to_datetime(df["month_start"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    # Latest complete month
    has_both = df.groupby("month_start")["pnl_section"].nunique() >= 2
    complete = has_both[has_both].index
    if complete.empty:
        st.info("No complete P&L month available.")
        return
    latest = complete.max()
    mdf = df[df["month_start"] == latest]

    rev = mdf[mdf["pnl_section"] == "Revenue"].groupby("business_line")["amount"].sum()
    cogs = mdf[mdf["pnl_section"] == "COGS"].groupby("business_line")["amount"].sum()

    total_rev = rev.sum()
    total_cogs = cogs.sum()
    gross_profit = total_rev - total_cogs

    # Nodes: [BizLines...] → [Total Revenue] → [Gross Profit, Total COGS]
    # Then COGS splits back to business lines
    nodes = []
    node_colors = []

    # 0-3: Business lines
    biz_colors_map = {
        "SaaS Platform": "#2B7BE9",
        "SaaS Relay": "#1A5FC7",
        "Solutions": "#F59E0B",
        "Support": "#94A3B8",
    }
    for biz in BIZ_ORDER:
        nodes.append(biz)
        node_colors.append(biz_colors_map.get(biz, "#2B7BE9"))

    # 4: Total Revenue
    nodes.append(f"Revenue ${total_rev:,.0f}")
    node_colors.append("#0D1B2A")

    # 5: Gross Profit
    nodes.append(f"Gross Profit ${gross_profit:,.0f}")
    node_colors.append("#22C55E")

    # 6: COGS
    nodes.append(f"COGS ${total_cogs:,.0f}")
    node_colors.append("#E74C3C")

    sources, targets, values, link_colors = [], [], [], []

    # Business lines → Revenue
    for i, biz in enumerate(BIZ_ORDER):
        if biz in rev.index and rev[biz] > 0:
            sources.append(i)
            targets.append(4)
            values.append(float(rev[biz]))
            link_colors.append(biz_colors_map.get(biz, "#2B7BE9") + "40")

    # Revenue → Gross Profit
    sources.append(4)
    targets.append(5)
    values.append(float(gross_profit))
    link_colors.append("rgba(34,197,94,0.25)")

    # Revenue → COGS
    sources.append(4)
    targets.append(6)
    values.append(float(total_cogs))
    link_colors.append("rgba(231,76,60,0.25)")

    margin_pct = (gross_profit / total_rev * 100) if total_rev else 0

    fig = go.Figure()
    fig.add_trace(go.Sankey(
        arrangement="snap",
        node=dict(
            pad=20,
            thickness=24,
            line=dict(color="rgba(0,0,0,0)", width=0),
            label=nodes,
            color=node_colors,
        ),
        link=dict(
            source=sources, target=targets, value=values,
            color=link_colors,
        ),
        textfont=dict(size=11, family="Inter", color=PALETTE["ink"]),
    ))

    fig.update_layout(
        height=get_height(DEFAULT_HEIGHT),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=8, r=8, t=32, b=8),
        font=dict(family="Inter, sans-serif", size=11, color=PALETTE["secondary"]),
    )

    month_label = latest.strftime("%B %Y")
    st.html(f"""
    <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:2px;">
        <span style="font-size:11px;color:{PALETTE['tertiary']};">{month_label}</span>
        <span style="font-size:12px;font-weight:600;color:{PALETTE['green']};">{margin_pct:.0f}% gross margin</span>
    </div>
    """)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("P&L Flow", DEFAULT_HEIGHT)
    render()
