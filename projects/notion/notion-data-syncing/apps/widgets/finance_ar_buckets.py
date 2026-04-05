"""finance_ar_buckets — AR aging by bucket, horizontal bar with color-coded severity."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, PALETTE

DEFAULT_HEIGHT = 300

BUCKET_ORDER = ["Current", "1-30", "31-60", "61-90", "91-120", "120+"]
BUCKET_COLORS = {
    "Current": PALETTE["green"],
    "1-30":    PALETTE["blue"],
    "31-60":   PALETTE["amber"],
    "61-90":   "#F97316",
    "91-120":  PALETTE["red"],
    "120+":    PALETTE["navy"],
}


def render():
    df = query_view("finance_ar_aging")
    if df.empty:
        st.warning("No AR aging data available.")
        return

    df["amount_due"] = pd.to_numeric(df["amount_due"], errors="coerce").fillna(0)

    bucket_summary = (
        df.groupby("aging_bucket", as_index=False)["amount_due"]
        .sum()
        .rename(columns={"amount_due": "total_due"})
    )

    # Sort by bucket order
    order_map = {b: i for i, b in enumerate(BUCKET_ORDER)}
    bucket_summary["_order"] = bucket_summary["aging_bucket"].map(order_map).fillna(99)
    bucket_summary = bucket_summary.sort_values("_order")

    bar_colors = [BUCKET_COLORS.get(b, PALETTE["secondary"]) for b in bucket_summary["aging_bucket"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=bucket_summary["aging_bucket"],
        x=bucket_summary["total_due"],
        orientation="h",
        marker=dict(color=bar_colors, cornerradius=4),
        hovertemplate="%{y}<br><b>$%{x:,.0f}</b><extra></extra>",
    ))
    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        margin=dict(l=0, r=16, t=8, b=0),
        xaxis=dict(gridcolor=PALETTE["grid"]),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", automargin=True, categoryorder="array",
                   categoryarray=list(bucket_summary["aging_bucket"])),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("AR Aging Buckets", DEFAULT_HEIGHT)
    render()
