"""pnl_heatmap — Month x Business Line revenue heatmap with margin overlay text."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, PALETTE

DEFAULT_HEIGHT = 360

BIZ_ORDER = ["SaaS Platform", "SaaS Relay", "Solutions", "Support"]


def render():
    df = query_view("pnl_monthly")
    if df.empty:
        st.warning("No P&L data available.")
        return

    df["month_start"] = pd.to_datetime(df["month_start"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df = df.dropna(subset=["month_start"])

    rev = df[df["pnl_section"] == "Revenue"]
    cogs = df[df["pnl_section"] == "COGS"]

    rev_pivot = rev.pivot_table(
        index="business_line", columns="month_start",
        values="amount", aggfunc="sum",
    ).reindex(BIZ_ORDER).fillna(0)

    cogs_pivot = cogs.pivot_table(
        index="business_line", columns="month_start",
        values="amount", aggfunc="sum",
    ).reindex(BIZ_ORDER).fillna(0)

    # Margin % matrix
    margin_pivot = ((rev_pivot - cogs_pivot) / rev_pivot.replace(0, np.nan) * 100).fillna(100)

    # Format month labels
    month_labels = [m.strftime("%b '%y") for m in rev_pivot.columns]

    # Dollar values for hover
    z_values = rev_pivot.values
    margin_values = margin_pivot.values

    # Custom text: show dollar amount in each cell
    text_matrix = []
    for i in range(len(BIZ_ORDER)):
        row = []
        for j in range(len(month_labels)):
            val = z_values[i][j]
            mgn = margin_values[i][j]
            if val > 0:
                row.append(f"${val/1000:.0f}K<br><span style='font-size:9px'>{mgn:.0f}%</span>")
            else:
                row.append("")
        text_matrix.append(row)

    # Hover text
    hover_matrix = []
    for i in range(len(BIZ_ORDER)):
        row = []
        for j in range(len(month_labels)):
            rev_val = z_values[i][j]
            cogs_val = cogs_pivot.values[i][j] if i < cogs_pivot.shape[0] else 0
            mgn = margin_values[i][j]
            row.append(
                f"{BIZ_ORDER[i]}<br>{month_labels[j]}<br>"
                f"Revenue: <b>${rev_val:,.0f}</b><br>"
                f"COGS: <b>${cogs_val:,.0f}</b><br>"
                f"Margin: <b>{mgn:.1f}%</b>"
            )
        hover_matrix.append(row)

    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=z_values,
        x=month_labels,
        y=BIZ_ORDER,
        text=text_matrix,
        texttemplate="%{text}",
        textfont=dict(size=10, family="Inter"),
        hovertext=hover_matrix,
        hovertemplate="%{hovertext}<extra></extra>",
        colorscale=[
            [0, "#F4F6FA"],
            [0.25, "#E8F1FD"],
            [0.5, "#93C5FD"],
            [0.75, "#2B7BE9"],
            [1, "#0D1B2A"],
        ],
        showscale=False,
        xgap=3,
        ygap=3,
    ))

    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        margin=dict(l=0, r=0, t=8, b=0),
        xaxis=dict(
            side="top",
            tickfont=dict(size=10, color=PALETTE["secondary"]),
            gridcolor="rgba(0,0,0,0)",
        ),
        yaxis=dict(
            automargin=True,
            tickfont=dict(size=11, color=PALETTE["ink"]),
            gridcolor="rgba(0,0,0,0)",
        ),
    ))

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("Revenue Heatmap", DEFAULT_HEIGHT)
    render()
