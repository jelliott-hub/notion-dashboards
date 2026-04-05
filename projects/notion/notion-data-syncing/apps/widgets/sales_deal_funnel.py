"""sales_deal_funnel — Deal value by stage, Plotly funnel chart."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, CHART_COLORS, PALETTE

DEFAULT_HEIGHT = 360

STAGE_ORDER = [
    "Prospecting", "Qualification", "Proposal", "Negotiation",
    "Closed Won", "Closed Lost",
]


def render():
    df = query_view("sales_deals")
    if df.empty or "deal_stage" not in df.columns:
        st.warning("No deals data available.")
        return

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    stage_df = (
        df.groupby("deal_stage", as_index=False)["amount"]
        .sum()
        .rename(columns={"amount": "total_amount"})
    )
    stage_df["_order"] = stage_df["deal_stage"].apply(
        lambda s: STAGE_ORDER.index(s) if s in STAGE_ORDER else 999
    )
    stage_df = stage_df.sort_values("_order").drop(columns="_order")

    if stage_df.empty:
        st.warning("No stage data to display.")
        return

    fig = go.Figure()
    fig.add_trace(go.Funnel(
        y=stage_df["deal_stage"],
        x=stage_df["total_amount"],
        textinfo="value+percent initial",
        texttemplate="$%{value:,.0f}<br>%{percentInitial:.0%}",
        textfont=dict(size=11, family="Inter"),
        marker=dict(
            color=[CHART_COLORS[i % len(CHART_COLORS)] for i in range(len(stage_df))],
            line=dict(width=0),
        ),
        connector=dict(line=dict(color=PALETTE["border"], width=1)),
        hovertemplate="%{y}<br><b>$%{x:,.0f}</b><extra></extra>",
    ))
    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        margin=dict(l=0, r=0, t=8, b=0),
        yaxis=dict(automargin=True),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("Deal Funnel", DEFAULT_HEIGHT)
    render()
