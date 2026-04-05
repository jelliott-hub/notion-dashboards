"""revenue_volume_metrics — KPI strip: total volume, platform fee/scan, relay fee/scan, ratio."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import pandas as pd
from apps.widgets._base import widget_page
from core.db import query_view
from core.style import metric_card, PALETTE

DEFAULT_HEIGHT = 120


def render():
    df = query_view("unit_economics_monthly")
    if df.empty:
        st.warning("No unit economics data available.")
        return

    df["report_month"] = pd.to_datetime(df["report_month"], errors="coerce")
    for c in ["volume", "processing_per_scan"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    latest_month = df["report_month"].max()
    prev_month = latest_month - pd.DateOffset(months=1)
    latest = df[df["report_month"] == latest_month]
    prev = df[df["report_month"] == prev_month]

    plat = latest[latest["business_line"] == "SaaS Platform"]
    relay = latest[latest["business_line"] == "SaaS Relay"]
    plat_prev = prev[prev["business_line"] == "SaaS Platform"]
    relay_prev = prev[prev["business_line"] == "SaaS Relay"]

    total_vol = latest["volume"].sum()
    prev_total_vol = prev["volume"].sum()
    plat_vol = int(plat["volume"].sum()) if not plat.empty else 0
    relay_vol = int(relay["volume"].sum()) if not relay.empty else 0
    plat_fee = plat["processing_per_scan"].iloc[0] if not plat.empty else 0
    relay_fee = relay["processing_per_scan"].iloc[0] if not relay.empty else 0
    plat_fee_prev = plat_prev["processing_per_scan"].iloc[0] if not plat_prev.empty else 0
    relay_fee_prev = relay_prev["processing_per_scan"].iloc[0] if not relay_prev.empty else 0

    def _delta(cur, prev):
        if prev == 0:
            return "", None
        pct = (cur - prev) / abs(prev) * 100
        sign = "+" if pct >= 0 else ""
        color = PALETTE["green"] if pct >= 0 else PALETTE["red"]
        return f"{sign}{pct:.1f}% MoM", color

    v_d, v_c = _delta(total_vol, prev_total_vol)
    pf_d, pf_c = _delta(plat_fee, plat_fee_prev)
    rf_d, rf_c = _delta(relay_fee, relay_fee_prev)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        with st.container(border=True):
            st.html(metric_card("Total Volume", f"{int(total_vol):,}", v_d, v_c))
    with m2:
        with st.container(border=True):
            st.html(metric_card("Platform Fee/Scan", f"${plat_fee:.2f}", pf_d, pf_c))
    with m3:
        with st.container(border=True):
            st.html(metric_card("Relay Fee/Scan", f"${relay_fee:.2f}", rf_d, rf_c))
    with m4:
        with st.container(border=True):
            ratio = relay_vol / plat_vol if plat_vol > 0 else 0
            st.html(metric_card("Relay : Platform", f"{ratio:.1f}x",
                                f"{relay_vol:,} vs {plat_vol:,} scans"))


if __name__ == "__main__":
    widget_page("Volume Metrics", DEFAULT_HEIGHT)
    render()
