"""revenue_conc_metrics — KPI strip: #1 customer, top-3/5/10 share of TTM revenue."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import pandas as pd
from apps.widgets._base import widget_page
from core.db import query_view
from core.style import metric_card, PALETTE

DEFAULT_HEIGHT = 120


def render():
    df = query_view("customer_concentration_top")
    if df.empty:
        st.warning("No concentration data available.")
        return

    df["ttm_revenue"] = pd.to_numeric(df["ttm_revenue"], errors="coerce").fillna(0)

    # Aggregate by client (customers can span multiple business lines)
    top_cust = (df.groupby(["client_id", "customer_name"])
                .agg(ttm=("ttm_revenue", "sum"))
                .reset_index().sort_values("ttm", ascending=False))
    total_ttm = top_cust["ttm"].sum()
    top_cust["share_pct"] = (top_cust["ttm"] / total_ttm * 100).round(2)

    if top_cust.empty:
        st.info("No customer data.")
        return

    top1 = top_cust.iloc[0]
    top3_share = top_cust.head(3)["share_pct"].sum()
    top5_share = top_cust.head(5)["share_pct"].sum()
    top10_share = top_cust.head(10)["share_pct"].sum()

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        with st.container(border=True):
            st.html(metric_card("#1 Customer", top1["customer_name"],
                                f"{top1['share_pct']:.1f}% · ${top1['ttm']:,.0f} TTM",
                                PALETTE["amber"]))
    with m2:
        with st.container(border=True):
            st.html(metric_card("Top-3 Share", f"{top3_share:.1f}%",
                                f"${top_cust.head(3)['ttm'].sum():,.0f} TTM"))
    with m3:
        with st.container(border=True):
            st.html(metric_card("Top-5 Share", f"{top5_share:.1f}%",
                                f"${top_cust.head(5)['ttm'].sum():,.0f} TTM"))
    with m4:
        with st.container(border=True):
            st.html(metric_card("Top-10 Share", f"{top10_share:.1f}%",
                                f"{len(top_cust):,} active customers"))


if __name__ == "__main__":
    widget_page("Concentration Metrics", DEFAULT_HEIGHT)
    render()
