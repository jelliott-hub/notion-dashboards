"""revenue_landscape — Top 20 customers treemap by TTM revenue, grouped by segment."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, CHART_COLORS, PALETTE

DEFAULT_HEIGHT = 400

BUCKET_COLORS = {
    "SaaS":            CHART_COLORS[0],
    "Partner":         CHART_COLORS[1],
    "Law Enforcement": CHART_COLORS[2],
    "Service Center":  CHART_COLORS[3],
}


def render():
    df = query_view("customer_concentration_top")
    if df.empty:
        st.warning("No concentration data available.")
        return

    df["ttm_revenue"] = pd.to_numeric(df["ttm_revenue"], errors="coerce").fillna(0)

    top_cust = (df.groupby(["client_id", "customer_name"])
                .agg(ttm=("ttm_revenue", "sum"),
                     bucket=("accounting_bucket", "first"))
                .reset_index().sort_values("ttm", ascending=False))
    total_ttm = top_cust["ttm"].sum()
    top_cust["share_pct"] = (top_cust["ttm"] / total_ttm * 100).round(2)

    top20 = top_cust.head(20).copy()
    if top20.empty:
        st.info("No customer data for treemap.")
        return

    top20["label"] = (top20["customer_name"] + "<br>"
                      + top20["share_pct"].apply(lambda x: f"{x:.1f}%")
                      + " · $" + top20["ttm"].apply(lambda x: f"{x:,.0f}"))

    fig = go.Figure(go.Treemap(
        labels=top20["label"],
        parents=top20["bucket"],
        values=top20["ttm"],
        textinfo="label",
        textfont=dict(size=11),
        marker=dict(
            colors=[BUCKET_COLORS.get(b, CHART_COLORS[0]) for b in top20["bucket"]],
            line=dict(width=2, color="white"),
        ),
        hovertemplate="<b>%{label}</b><extra></extra>",
    ))

    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        margin=dict(l=0, r=0, t=28, b=0),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("Revenue Landscape", DEFAULT_HEIGHT)
    render()
