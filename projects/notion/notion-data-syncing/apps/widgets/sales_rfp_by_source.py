"""sales_rfp_by_source — RFPs by source and relevance, stacked bar chart."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, PALETTE

DEFAULT_HEIGHT = 340

RELEVANCE_COLORS = {
    "HIGH":   "#E74C3C",
    "MEDIUM": "#F59E0B",
    "LOW":    "#94A3B8",
}
RELEVANCE_ORDER = ["HIGH", "MEDIUM", "LOW"]


def render():
    df = query_view("sales_rfp_pipeline")
    if df.empty:
        st.warning("No RFP data available.")
        return

    if "source" not in df.columns or "relevance" not in df.columns:
        st.warning("Missing source or relevance columns.")
        return

    stacked = (
        df.groupby(["source", "relevance"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    if stacked.empty:
        st.warning("No RFP source data to display.")
        return

    sources = stacked.groupby("source")["count"].sum().sort_values(ascending=True).index.tolist()

    fig = go.Figure()
    for rel in RELEVANCE_ORDER:
        subset = stacked[stacked["relevance"] == rel]
        if subset.empty:
            continue
        # Align to all sources so stacking works cleanly
        vals = subset.set_index("source").reindex(sources).fillna(0)
        fig.add_trace(go.Bar(
            y=vals.index,
            x=vals["count"],
            name=rel,
            orientation="h",
            marker=dict(color=RELEVANCE_COLORS.get(rel, PALETTE["blue"]), cornerradius=2),
            hovertemplate="%{y}<br>" + rel + ": <b>%{x}</b><extra></extra>",
        ))

    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        barmode="stack",
        showlegend=True,
        legend=dict(
            orientation="h", y=1.06, x=1, xanchor="right",
            font=dict(size=11, color=PALETTE["secondary"]),
        ),
        margin=dict(l=0, r=16, t=32, b=0),
        xaxis=dict(gridcolor=PALETTE["grid"]),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", automargin=True),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("RFPs by Source", DEFAULT_HEIGHT)
    render()
