"""tickets_daily_trend — Daily opened vs closed spline/area chart."""

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
    daily = query_view("tickets_daily")
    if daily.empty:
        st.warning("No ticket data available.")
        return

    daily["ticket_date"] = pd.to_datetime(daily["ticket_date"], errors="coerce")
    for c in ["opened", "closed"]:
        if c in daily.columns:
            daily[c] = pd.to_numeric(daily[c], errors="coerce").fillna(0).astype(int)

    # Last 90 days, weekdays only
    cutoff = pd.Timestamp.now().normalize() - pd.Timedelta(days=90)
    plot_df = daily[
        (daily["ticket_date"] >= cutoff)
        & (daily["ticket_date"].dt.dayofweek < 5)
    ].sort_values("ticket_date")

    if plot_df.empty:
        st.info("No recent ticket data to display.")
        return

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=plot_df["ticket_date"], y=plot_df["opened"],
        name="Opened",
        mode="lines",
        line=dict(color=CHART_COLORS[0], width=2, shape="spline"),
        fill="tozeroy",
        fillcolor="rgba(43,123,233,0.08)",
        hovertemplate="%{x|%b %d}<br><b>%{y:,.0f}</b> opened<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=plot_df["ticket_date"], y=plot_df["closed"],
        name="Closed",
        mode="lines",
        line=dict(color=PALETTE["blue_dark"], width=2, shape="spline", dash="dot"),
        hovertemplate="%{x|%b %d}<br><b>%{y:,.0f}</b> closed<extra></extra>",
    ))

    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        showlegend=True,
        legend=dict(
            orientation="h", y=1.06, x=1, xanchor="right",
            font=dict(size=11, color=PALETTE["secondary"]),
        ),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        yaxis=dict(gridcolor=PALETTE["grid"]),
        margin=dict(l=0, r=0, t=32, b=0),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("Daily Tickets", DEFAULT_HEIGHT)
    render()
