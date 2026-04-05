"""sales_rfp_timeline — RFP due-date scatter, sized by dollar amount, colored by relevance."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, PALETTE

DEFAULT_HEIGHT = 360

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

    df["due_date"] = pd.to_datetime(df["due_date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    plot_df = df.dropna(subset=["due_date"])
    if plot_df.empty or "source" not in plot_df.columns:
        st.warning("No RFP timeline data to display.")
        return

    plot_df = plot_df.copy()
    # Floor bubble size so zero-amount RFPs still show
    plot_df["bubble"] = plot_df["amount"].clip(lower=1)
    # Normalize bubble sizes: map to 8-40 range
    bmax = plot_df["bubble"].max()
    if bmax > 0:
        plot_df["size"] = 8 + (plot_df["bubble"] / bmax) * 32
    else:
        plot_df["size"] = 12

    fig = go.Figure()
    for rel in RELEVANCE_ORDER:
        subset = plot_df[plot_df["relevance"] == rel] if "relevance" in plot_df.columns else pd.DataFrame()
        if subset.empty:
            continue
        fig.add_trace(go.Scatter(
            x=subset["due_date"],
            y=subset["source"],
            mode="markers",
            name=rel,
            marker=dict(
                size=subset["size"],
                color=RELEVANCE_COLORS.get(rel, PALETTE["blue"]),
                opacity=0.75,
                line=dict(width=1, color="white"),
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Due: %{x|%b %d, %Y}<br>"
                "Amount: $%{customdata[1]:,.0f}<br>"
                "Source: %{y}<extra></extra>"
            ),
            customdata=list(zip(
                subset.get("title", pd.Series([""] * len(subset))),
                subset["amount"],
            )),
        ))

    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        hovermode="closest",
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
    widget_page("RFP Timeline", DEFAULT_HEIGHT)
    render()
