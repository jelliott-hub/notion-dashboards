"""support_call_topics — Top 8 call topics by volume, horizontal bar."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, CHART_COLORS, PALETTE

DEFAULT_HEIGHT = 300


def render():
    topics = query_view("calls_by_topic")
    if topics.empty or "support_category" not in topics.columns:
        st.warning("No topic data available.")
        return

    topics["total_calls"] = pd.to_numeric(topics["total_calls"], errors="coerce").fillna(0)

    top = (topics.groupby("support_category")["total_calls"]
           .sum().nlargest(8).sort_values())

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=top.index, x=top.values,
        orientation="h",
        marker=dict(color=CHART_COLORS[0], cornerradius=4),
        hovertemplate="%{y}<br><b>%{x:,.0f}</b> calls<extra></extra>",
    ))
    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        margin=dict(l=0, r=16, t=8, b=0),
        xaxis=dict(gridcolor=PALETTE["grid"]),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", automargin=True),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("Top Topics", DEFAULT_HEIGHT)
    render()
