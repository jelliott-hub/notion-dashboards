"""support_agent_leaderboard — Top 10 agents by call volume, horizontal bar."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, CHART_COLORS, PALETTE

DEFAULT_HEIGHT = 340


def render():
    agents = query_view("calls_by_agent")
    if agents.empty:
        st.warning("No agent data available.")
        return

    agents["total_calls"] = pd.to_numeric(agents["total_calls"], errors="coerce").fillna(0)

    board = (agents.groupby("agent_name")["total_calls"]
             .sum().nlargest(10).sort_values())

    bar_colors = [CHART_COLORS[0]] * len(board)
    bar_colors[-1] = CHART_COLORS[1]  # top agent in dark blue

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=board.index, x=board.values,
        orientation="h",
        marker=dict(color=bar_colors, cornerradius=4),
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
    widget_page("Agent Leaderboard", DEFAULT_HEIGHT)
    render()
