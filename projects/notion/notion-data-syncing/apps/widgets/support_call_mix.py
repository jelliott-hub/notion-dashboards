"""support_call_mix — Daily stacked bar: inbound answered, voicemail, outbound, Bland AI."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, PALETTE

DEFAULT_HEIGHT = 380

CAT_ORDER = ["Inbound — Answered", "Inbound — Voicemail", "Outbound", "Bland"]
CAT_COLORS = {
    "Inbound — Answered":  "#1A5FC7",
    "Inbound — Voicemail": "#F59E0B",
    "Outbound":            "#94A3B8",
    "Bland":               "rgba(43,123,233,0.30)",
}


def render():
    log = query_view("calls_log")
    if log.empty:
        st.warning("No call log data available.")
        return

    log["call_date"] = pd.to_datetime(log["call_date"], errors="coerce")
    log = log[log["call_date"].dt.dayofweek < 5]  # weekdays only

    def _categorize(row):
        if row.get("is_bland_call"):
            return "Bland"
        if row.get("direction") == "outbound":
            return "Outbound"
        if row.get("call_status") == "voicemail":
            return "Inbound — Voicemail"
        return "Inbound — Answered"

    log["category"] = log.apply(_categorize, axis=1)

    cat_daily = (log.groupby(["call_date", "category"])
                 .size().reset_index(name="calls"))
    day_totals = cat_daily.groupby("call_date")["calls"].transform("sum")
    cat_daily["pct"] = cat_daily["calls"] / day_totals * 100

    fig = go.Figure()
    for cat in CAT_ORDER:
        d = cat_daily[cat_daily["category"] == cat].sort_values("call_date")
        if d.empty:
            continue
        labels = [f"{p:.0f}%" for p in d["pct"]]
        text_color = "white" if cat != "Bland" else PALETTE["navy"]
        fig.add_trace(go.Bar(
            x=d["call_date"], y=d["calls"],
            name=cat,
            text=labels,
            textposition="inside",
            textangle=0,
            insidetextanchor="middle",
            constraintext="none",
            cliponaxis=False,
            textfont=dict(size=9, color=text_color, family="Inter"),
            marker=dict(color=CAT_COLORS[cat], cornerradius=2,
                        line=dict(width=0)),
            width=1000 * 60 * 60 * 14,
            hovertemplate=(
                "%{x|%b %d}<br>%{fullData.name}: "
                "<b>%{y}</b><extra></extra>"
            ),
        ))

    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        barmode="stack",
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
    widget_page("Call Mix", DEFAULT_HEIGHT)
    render()
