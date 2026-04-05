"""revenue_top_customers — Top 10 customers by TTM revenue, horizontal bar."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, CHART_COLORS, PALETTE

DEFAULT_HEIGHT = 380

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

    top10 = top_cust.head(10).sort_values("ttm")
    if top10.empty:
        st.info("No customer data.")
        return

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=top10["customer_name"], x=top10["ttm"],
        orientation="h",
        marker=dict(
            color=[BUCKET_COLORS.get(b, CHART_COLORS[0]) for b in top10["bucket"]],
            cornerradius=4,
        ),
        text=[f"{s:.1f}%" for s in top10["share_pct"]],
        textposition="outside",
        textfont=dict(size=10, color=PALETTE["secondary"]),
        hovertemplate="%{y}<br><b>$%{x:,.0f}</b> TTM<extra></extra>",
    ))

    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        margin=dict(l=0, r=50, t=8, b=0),
        xaxis=dict(gridcolor=PALETTE["grid"], tickprefix="$", tickformat=","),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", automargin=True),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("Top 10 Customers", DEFAULT_HEIGHT)
    render()
