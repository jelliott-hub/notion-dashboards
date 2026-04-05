"""sales_opp_heatmap — Opportunities heatmap: source type vs urgency tier."""

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


def render():
    df = query_view("sales_opportunities")
    if df.empty:
        st.warning("No opportunities data available.")
        return

    if "source_type" not in df.columns or "urgency_tier" not in df.columns:
        st.warning("Missing source_type or urgency_tier columns.")
        return

    heat_df = (
        df.groupby(["source_type", "urgency_tier"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    if heat_df.empty:
        st.warning("No heatmap data to display.")
        return

    # Pivot for heatmap matrix
    pivot = heat_df.pivot_table(
        index="urgency_tier", columns="source_type",
        values="count", fill_value=0, aggfunc="sum",
    )

    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale=[
            [0, PALETTE["blue_light"]],
            [0.5, PALETTE["blue"]],
            [1, PALETTE["blue_dark"]],
        ],
        text=pivot.values.astype(int).astype(str),
        texttemplate="%{text}",
        textfont=dict(size=13, family="Inter"),
        hovertemplate="Source: %{x}<br>Urgency: %{y}<br>Count: <b>%{z}</b><extra></extra>",
        showscale=False,
    ))
    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        margin=dict(l=0, r=0, t=8, b=0),
        xaxis=dict(gridcolor="rgba(0,0,0,0)", side="bottom", automargin=True),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", automargin=True, autorange="reversed"),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("Opportunity Heatmap", DEFAULT_HEIGHT)
    render()
