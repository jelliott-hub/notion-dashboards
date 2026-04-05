"""finance_inbox_volume — Weekly inbox stacked bar: inbound, replied, outbound, internal."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, PALETTE

DEFAULT_HEIGHT = 340

SEGMENTS = [
    ("inbound_unreplied", "Inbound",  "#1A5FC7"),
    ("replied",           "Replied",  "#22C55E"),
    ("outbound",          "Outbound", "#94A3B8"),
    ("internal",          "Internal", "#F59E0B"),
]


def render():
    df = query_view("finance_accounting_inbox")
    if df.empty:
        st.warning("No accounting inbox data available.")
        return

    df["week_start"] = pd.to_datetime(df["week_start"], errors="coerce")
    for c in ["inbound", "outbound", "replied", "internal"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # Aggregate across classification/folder to get one row per week
    weekly = (
        df.groupby("week_start", as_index=False)[["inbound", "outbound", "replied", "internal"]]
        .sum()
        .sort_values("week_start")
    )

    # Inbound unreplied = inbound - replied
    weekly["inbound_unreplied"] = weekly["inbound"] - weekly["replied"]

    # Last 12 complete weeks (drop partial current week)
    latest_monday = pd.Timestamp.now().normalize() - pd.Timedelta(days=pd.Timestamp.now().weekday())
    weekly = weekly[weekly["week_start"] < latest_monday].tail(12)

    if weekly.empty:
        st.warning("No complete weeks available.")
        return

    fig = go.Figure()
    for col, label, color in SEGMENTS:
        fig.add_trace(go.Bar(
            x=weekly["week_start"],
            y=weekly[col],
            name=label,
            marker=dict(color=color, cornerradius=2, line=dict(width=0)),
            hovertemplate="%{x|%b %d}<br>" + label + ": <b>%{y:,.0f}</b><extra></extra>",
        ))

    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        barmode="stack",
        showlegend=True,
        legend=dict(
            orientation="h", y=1.06, x=1, xanchor="right",
            font=dict(size=11, color=PALETTE["secondary"]),
        ),
        xaxis=dict(
            gridcolor="rgba(0,0,0,0)",
            tickformat="%b %d",
            dtick=7 * 24 * 60 * 60 * 1000,
        ),
        yaxis=dict(gridcolor=PALETTE["grid"]),
        margin=dict(l=0, r=0, t=32, b=0),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("Inbox Volume", DEFAULT_HEIGHT)
    render()
