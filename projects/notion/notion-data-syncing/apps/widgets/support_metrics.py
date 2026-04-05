"""support_metrics — KPI strip: weekly calls, answer rate, abandoned, pipeline deals."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import pandas as pd
from apps.widgets._base import widget_page
from core.db import query_view
from core.style import metric_card, PALETTE

DEFAULT_HEIGHT = 120


def render():
    calls = query_view("calls_weekly")
    deals = query_view("sales_deals")

    if calls.empty:
        st.warning("No call data available.")
        return

    # Type coercion
    calls["call_week"] = pd.to_datetime(calls["call_week"], errors="coerce")
    for c in ["total_calls", "answered", "abandoned"]:
        if c in calls.columns:
            calls[c] = pd.to_numeric(calls[c], errors="coerce").fillna(0)

    latest = calls["call_week"].max()
    prev_wk = latest - pd.Timedelta(weeks=1)

    def _week_sum(col):
        cur = int(calls.loc[calls["call_week"] == latest, col].sum())
        prev = int(calls.loc[calls["call_week"] == prev_wk, col].sum())
        return cur, prev

    def _delta(cur, prev, invert=False):
        if prev == 0:
            return "", None
        pct = (cur - prev) / prev * 100
        up = pct >= 0
        good = (not up) if invert else up
        arrow = "↑" if up else "↓"
        color = PALETTE["green"] if good else PALETTE["red"]
        return f"{arrow} {abs(pct):.1f}% vs prior week", color

    cur_calls, prev_calls = _week_sum("total_calls")
    delta_txt, delta_clr = _delta(cur_calls, prev_calls)

    # Answer rate
    wk = calls[calls["call_week"] == latest]
    ans, tot = wk["answered"].sum(), wk["total_calls"].sum()
    rate = (ans / tot * 100) if tot else 0
    rate_color = PALETTE["green"] if rate >= 80 else PALETTE["amber"]

    # Abandoned
    cur_abn, prev_abn = _week_sum("abandoned")
    abn_txt, abn_clr = _delta(cur_abn, prev_abn, invert=True)

    # Deals
    deal_count = len(deals) if not deals.empty else 0

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        with st.container(border=True):
            st.html(metric_card("Weekly Calls", f"{cur_calls:,}", delta_txt, delta_clr))
    with m2:
        with st.container(border=True):
            st.html(metric_card("Answer Rate", f"{rate:.0f}%", "target: 80%", rate_color))
    with m3:
        with st.container(border=True):
            st.html(metric_card("Abandoned", f"{cur_abn:,}", abn_txt, abn_clr))
    with m4:
        with st.container(border=True):
            st.html(metric_card("Pipeline Deals", str(deal_count)))


if __name__ == "__main__":
    widget_page("Support Metrics", DEFAULT_HEIGHT)
    render()
