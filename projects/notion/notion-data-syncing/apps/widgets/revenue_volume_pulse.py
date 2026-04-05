"""revenue_volume_pulse — Weekly volume: platform vs relay overlaid bars."""

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
    df = query_view("volume_weekly")
    if df.empty:
        st.warning("No weekly volume data available.")
        return

    df["period_start"] = pd.to_datetime(df["period_start"], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)

    wk = (df.groupby(["period_start", "business_line"])["volume"]
          .sum().reset_index().sort_values("period_start"))

    if wk.empty:
        st.info("No volume data to display.")
        return

    fig = go.Figure()

    relay_wk = wk[wk["business_line"] == "SaaS Relay"]
    if not relay_wk.empty:
        fig.add_trace(go.Bar(
            x=relay_wk["period_start"], y=relay_wk["volume"],
            name="Relay",
            marker=dict(color="rgba(43,123,233,0.15)", cornerradius=2),
            hovertemplate="%{x|%b %d}<br>Relay: <b>%{y:,.0f}</b><extra></extra>",
            yaxis="y2",
        ))

    plat_wk = wk[wk["business_line"] == "SaaS Platform"]
    if not plat_wk.empty:
        fig.add_trace(go.Bar(
            x=plat_wk["period_start"], y=plat_wk["volume"],
            name="Platform",
            marker=dict(color=CHART_COLORS[0], cornerradius=2),
            hovertemplate="%{x|%b %d}<br>Platform: <b>%{y:,.0f}</b><extra></extra>",
        ))

    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        showlegend=True,
        legend=dict(orientation="h", y=-0.12, x=0,
                    font=dict(size=11, color=PALETTE["secondary"])),
        barmode="overlay",
        xaxis=dict(gridcolor="rgba(0,0,0,0)",
                   rangebreaks=[dict(bounds=["sat", "mon"])]),
        yaxis=dict(gridcolor=PALETTE["grid"], tickformat=",",
                   title=dict(text="Platform", font=dict(size=10, color=PALETTE["secondary"]))),
        yaxis2=dict(overlaying="y", side="right", showgrid=False,
                    tickformat=",",
                    title=dict(text="Relay", font=dict(size=10, color=PALETTE["secondary"]))),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("Weekly Volume Pulse", DEFAULT_HEIGHT)
    render()
