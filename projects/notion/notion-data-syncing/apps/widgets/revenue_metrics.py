"""revenue_metrics — KPI strip: gross revenue, net revenue, net expansion, new customers."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import pandas as pd
from apps.widgets._base import widget_page
from core.db import query_view
from core.style import metric_card, PALETTE

DEFAULT_HEIGHT = 120


def render():
    df = query_view("revenue_decomposition")
    if df.empty:
        st.warning("No revenue data available.")
        return

    df["report_month"] = pd.to_datetime(df["report_month"], errors="coerce")
    for c in ["gross_revenue", "passthrough_revenue", "expansion_dollars",
              "contraction_dollars", "new_customers"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    latest = df["report_month"].max()
    prev = latest - pd.DateOffset(months=1)
    cur = df[df["report_month"] == latest]
    prv = df[df["report_month"] == prev]

    cur_gross = cur["gross_revenue"].sum()
    prev_gross = prv["gross_revenue"].sum()
    cur_net = cur_gross - cur["passthrough_revenue"].sum()
    prev_net = prev_gross - prv["passthrough_revenue"].sum()
    cur_new = int(cur["new_customers"].sum())

    def _delta(c, p):
        if p == 0:
            return "", None
        pct = (c - p) / abs(p) * 100
        sign = "+" if pct >= 0 else ""
        color = PALETTE["green"] if pct >= 0 else PALETTE["red"]
        return f"{sign}{pct:.1f}% MoM", color

    d_gross, c_gross = _delta(cur_gross, prev_gross)
    d_net, c_net = _delta(cur_net, prev_net)

    exp = cur["expansion_dollars"].sum()
    con = cur["contraction_dollars"].sum()
    net_exp = exp + con
    exp_label = f"+${net_exp:,.0f}" if net_exp >= 0 else f"-${abs(net_exp):,.0f}"
    exp_color = PALETTE["green"] if net_exp >= 0 else PALETTE["red"]

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        with st.container(border=True):
            st.html(metric_card("Gross Revenue", f"${cur_gross:,.0f}", d_gross, c_gross))
    with m2:
        with st.container(border=True):
            st.html(metric_card("Net Revenue", f"${cur_net:,.0f}", d_net, c_net))
    with m3:
        with st.container(border=True):
            st.html(metric_card("Net Expansion", exp_label,
                                f"${exp:,.0f} exp / ${abs(con):,.0f} con", exp_color))
    with m4:
        with st.container(border=True):
            st.html(metric_card("New Customers", str(cur_new),
                                latest.strftime("%B %Y")))


if __name__ == "__main__":
    widget_page("Revenue Metrics", DEFAULT_HEIGHT)
    render()
