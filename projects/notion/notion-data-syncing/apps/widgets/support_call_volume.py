"""support_call_volume — Weekly call volume spline/area chart."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, CHART_COLORS

DEFAULT_HEIGHT = 300


def render():
    calls = query_view("calls_weekly")
    if calls.empty:
        st.warning("No call data available.")
        return

    calls["call_week"] = pd.to_datetime(calls["call_week"], errors="coerce")
    calls["total_calls"] = pd.to_numeric(calls["total_calls"], errors="coerce").fillna(0)

    weekly = (calls.groupby("call_week")["total_calls"]
              .sum().reset_index().sort_values("call_week"))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=weekly["call_week"], y=weekly["total_calls"],
        mode="lines",
        line=dict(color=CHART_COLORS[0], width=2.5, shape="spline"),
        fill="tozeroy",
        fillcolor="rgba(43,123,233,0.08)",
        hovertemplate="%{x|%b %d, %Y}<br><b>%{y:,.0f}</b> calls<extra></extra>",
    ))
    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("Call Volume", DEFAULT_HEIGHT)
    render()
