"""sales_metrics — KPI strip: total deals, open deals, won, pipeline value."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import pandas as pd
from apps.widgets._base import widget_page
from core.db import query_view
from core.style import metric_card, PALETTE

DEFAULT_HEIGHT = 120


def render():
    df = query_view("sales_deals")
    if df.empty:
        st.warning("No deals data available.")
        return

    # Type coercion
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    for bool_col in ["is_closed_won", "is_closed_lost"]:
        if bool_col in df.columns:
            df[bool_col] = df[bool_col].astype(str).str.lower().isin(["true", "1", "yes", "t"])

    total = len(df)
    has_flags = all(c in df.columns for c in ["is_closed_won", "is_closed_lost"])
    open_mask = ~df["is_closed_won"] & ~df["is_closed_lost"] if has_flags else pd.Series(True, index=df.index)
    open_deals = int(open_mask.sum())
    won = int(df["is_closed_won"].sum()) if "is_closed_won" in df.columns else 0
    pipeline_value = df.loc[open_mask, "amount"].sum()

    # Win rate
    closed = df["is_closed_won"] | df["is_closed_lost"] if has_flags else pd.Series(False, index=df.index)
    closed_total = int(closed.sum())
    win_rate = (won / closed_total * 100) if closed_total > 0 else 0
    rate_color = PALETTE["green"] if win_rate >= 50 else PALETTE["amber"]

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        with st.container(border=True):
            st.html(metric_card("Total Deals", str(total)))
    with m2:
        with st.container(border=True):
            st.html(metric_card("Open Deals", str(open_deals), color=PALETTE["blue"]))
    with m3:
        with st.container(border=True):
            st.html(metric_card("Win Rate", f"{win_rate:.0f}%", f"{won} won / {closed_total} closed", rate_color))
    with m4:
        with st.container(border=True):
            st.html(metric_card("Pipeline Value", f"${pipeline_value:,.0f}"))


if __name__ == "__main__":
    widget_page("Sales Metrics", DEFAULT_HEIGHT)
    render()
