"""sales_state_map — US choropleth: state channeler model (open/closed/hybrid/limited)."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, PALETTE

DEFAULT_HEIGHT = 400

CHANNELER_COLORS = {
    "open":    "#22C55E",
    "closed":  "#E74C3C",
    "hybrid":  "#F59E0B",
    "limited": "#94A3B8",
}


def render():
    df = query_view("sales_state_profiles")
    if df.empty:
        st.warning("No state profile data available.")
        return

    if "state_abbr" not in df.columns or "channeler_model" not in df.columns:
        st.warning("Missing state_abbr or channeler_model columns.")
        return

    map_df = df.dropna(subset=["state_abbr", "channeler_model"]).copy()
    if map_df.empty:
        st.warning("No state map data to display.")
        return

    # Map channeler model to numeric index for colorscale
    models = list(CHANNELER_COLORS.keys())
    map_df["model_lower"] = map_df["channeler_model"].str.lower()
    map_df["model_idx"] = map_df["model_lower"].apply(
        lambda m: models.index(m) if m in models else len(models)
    )

    # Build discrete colorscale
    n = len(models)
    colorscale = []
    for i, model in enumerate(models):
        lo = i / n
        hi = (i + 1) / n
        colorscale.append([lo, CHANNELER_COLORS[model]])
        colorscale.append([hi, CHANNELER_COLORS[model]])

    fig = go.Figure()
    fig.add_trace(go.Choropleth(
        locationmode="USA-states",
        locations=map_df["state_abbr"],
        z=map_df["model_idx"],
        text=map_df["channeler_model"],
        colorscale=colorscale,
        showscale=False,
        marker=dict(line=dict(color="white", width=1)),
        hovertemplate="<b>%{location}</b><br>%{text}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=get_height(DEFAULT_HEIGHT),
        margin=dict(l=0, r=0, t=0, b=0),
        font=dict(family="Inter, -apple-system, sans-serif", size=11, color=PALETTE["secondary"]),
        geo=dict(
            scope="usa",
            bgcolor="rgba(0,0,0,0)",
            lakecolor="rgba(0,0,0,0)",
            landcolor=PALETTE["grid"],
            showlakes=False,
            showframe=False,
        ),
    )

    # Add legend annotations for each model
    for i, model in enumerate(models):
        fig.add_annotation(
            x=0.02 + i * 0.18, y=-0.02,
            xref="paper", yref="paper",
            text=f'<span style="color:{CHANNELER_COLORS[model]};">&#9632;</span> {model.title()}',
            showarrow=False,
            font=dict(size=11, color=PALETTE["secondary"], family="Inter"),
        )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("State Channeler Map", DEFAULT_HEIGHT)
    render()
