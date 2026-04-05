"""revenue_ttm_movement — TTM revenue movement stacked bar by retention category."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, CHART_COLORS, PALETTE

DEFAULT_HEIGHT = 300

CAT_COLORS = {
    "expansion":   PALETTE["green"],
    "new":         CHART_COLORS[0],
    "reactivation": CHART_COLORS[1],
    "contraction": PALETTE["amber"],
    "churned":     PALETTE["red"],
}


def render():
    retention = query_view("revenue_retention_summary")
    if retention.empty:
        st.warning("No retention data available.")
        return

    retention["evaluation_month"] = pd.to_datetime(retention["evaluation_month"], errors="coerce")
    retention["ttm_delta"] = pd.to_numeric(retention["ttm_delta"], errors="coerce").fillna(0)

    move = (retention[retention["evaluation_month"] >= "2025-01-01"]
            .groupby(["evaluation_month", "retention_category"])["ttm_delta"]
            .sum().reset_index().sort_values("evaluation_month"))

    if move.empty:
        st.info("No 2025+ retention movement data.")
        return

    fig = go.Figure()
    for cat in ["expansion", "new", "reactivation", "contraction", "churned"]:
        d = move[move["retention_category"] == cat]
        if d.empty:
            continue
        fig.add_trace(go.Bar(
            x=d["evaluation_month"], y=d["ttm_delta"],
            name=cat.title(),
            marker=dict(color=CAT_COLORS.get(cat, CHART_COLORS[0]), cornerradius=3),
            hovertemplate="%{x|%b %Y}<br>" + cat.title() + ": <b>$%{y:,.0f}</b><extra></extra>",
        ))

    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        barmode="relative",
        showlegend=True,
        legend=dict(orientation="h", y=-0.15, x=0,
                    font=dict(size=11, color=PALETTE["secondary"])),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        yaxis=dict(gridcolor=PALETTE["grid"], tickprefix="$", tickformat=","),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("TTM Movement", DEFAULT_HEIGHT)
    render()
