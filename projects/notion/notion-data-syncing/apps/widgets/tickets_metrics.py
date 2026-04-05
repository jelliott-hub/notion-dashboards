"""tickets_metrics — KPI strip: opened (7d), closed (7d), net new, open backlog."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import pandas as pd
from apps.widgets._base import widget_page
from core.db import query_view
from core.style import metric_card, PALETTE

DEFAULT_HEIGHT = 120


def render():
    daily = query_view("tickets_daily")
    if daily.empty:
        st.warning("No ticket data available.")
        return

    daily["ticket_date"] = pd.to_datetime(daily["ticket_date"], errors="coerce")
    for c in ["opened", "closed", "net_new"]:
        if c in daily.columns:
            daily[c] = pd.to_numeric(daily[c], errors="coerce").fillna(0).astype(int)

    today = pd.Timestamp.now().normalize()
    cutoff_7 = today - pd.Timedelta(days=7)
    cutoff_14 = today - pd.Timedelta(days=14)

    this_week = daily[(daily["ticket_date"] >= cutoff_7) & (daily["ticket_date"] < today)]
    prior_week = daily[(daily["ticket_date"] >= cutoff_14) & (daily["ticket_date"] < cutoff_7)]

    def _delta(cur, prev, invert=False):
        if prev == 0:
            return "", None
        pct = (cur - prev) / prev * 100
        up = pct >= 0
        good = (not up) if invert else up
        arrow = "↑" if up else "↓"
        color = PALETTE["green"] if good else PALETTE["red"]
        return f"{arrow} {abs(pct):.1f}% vs prior week", color

    cur_opened = int(this_week["opened"].sum())
    prev_opened = int(prior_week["opened"].sum())
    cur_closed = int(this_week["closed"].sum())
    prev_closed = int(prior_week["closed"].sum())
    net = cur_opened - cur_closed
    net_color = PALETTE["green"] if net <= 0 else PALETTE["red"]

    # Open backlog from tickets_open
    open_df = query_view("tickets_open")
    backlog = len(open_df)

    d_opened, c_opened = _delta(cur_opened, prev_opened)
    d_closed, c_closed = _delta(cur_closed, prev_closed)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        with st.container(border=True):
            st.html(metric_card("Opened (7d)", f"{cur_opened:,}", d_opened, c_opened))
    with m2:
        with st.container(border=True):
            st.html(metric_card("Closed (7d)", f"{cur_closed:,}", d_closed, c_closed))
    with m3:
        with st.container(border=True):
            sign = "+" if net > 0 else ""
            st.html(metric_card("Net New (7d)", f"{sign}{net:,}",
                                "backlog shrinking" if net <= 0 else "backlog growing",
                                net_color))
    with m4:
        with st.container(border=True):
            st.html(metric_card("Open Backlog", f"{backlog:,}",
                                "currently unresolved", PALETTE["secondary"]))


if __name__ == "__main__":
    widget_page("Ticket Metrics", DEFAULT_HEIGHT)
    render()
