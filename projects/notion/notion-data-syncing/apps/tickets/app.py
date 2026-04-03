"""Tickets — Stripe-inspired bento dashboard.

Single-page, chromeless layout designed for Notion embeds.
Run with: streamlit run apps/tickets/app.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from core.db import query_view
from apps.analytics.style import (
    inject_css, metric_card, card_header, section_label,
    page_header, chart_layout, CHART_COLORS, PALETTE,
)

# ── Page config ──────────────────────────────────────────────────────
st.set_page_config(page_title="Tickets", page_icon="◆", layout="wide")
inject_css()
st.html(page_header("Tickets", "Support ticket volume and trends"))

# ── Data ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load():
    df = query_view("tickets_daily")
    df["ticket_date"] = pd.to_datetime(df["ticket_date"], errors="coerce")
    for col in ["opened", "closed", "net_new", "escalated"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    for col in ["avg_resolution_hours", "avg_first_response_hours",
                "sla_resolution_pct", "sla_response_pct"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


daily = load()

# ── Helpers ──────────────────────────────────────────────────────────

def _recent(df, days=7):
    """Last N complete days (excludes today — partial)."""
    cutoff = pd.Timestamp.now().normalize() - pd.Timedelta(days=days)
    today = pd.Timestamp.now().normalize()
    return df[(df["ticket_date"] >= cutoff) & (df["ticket_date"] < today)]


def _delta_str(cur, prev, invert=False):
    if prev == 0:
        return "", None
    pct = (cur - prev) / prev * 100
    up = pct >= 0
    good = (not up) if invert else up
    arrow = "↑" if up else "↓"
    color = PALETTE["green"] if good else PALETTE["red"]
    return f"{arrow} {abs(pct):.1f}% vs prior week", color


# ── Row 1 — Metric cards ────────────────────────────────────────────

this_week = _recent(daily, 7)
last_week = _recent(daily, 14)
# last_week is 14 days back; subtract this_week to get prior-week only
prior_week_cutoff = pd.Timestamp.now().normalize() - pd.Timedelta(days=7)
prior_week = last_week[last_week["ticket_date"] < prior_week_cutoff]

cur_opened = int(this_week["opened"].sum())
prev_opened = int(prior_week["opened"].sum())
cur_closed = int(this_week["closed"].sum())
prev_closed = int(prior_week["closed"].sum())

m1, m2, m3, m4 = st.columns(4)

delta_txt, delta_clr = _delta_str(cur_opened, prev_opened)
with m1:
    with st.container(border=True):
        st.html(metric_card("Opened (7d)", f"{cur_opened:,}", delta_txt, delta_clr))

delta_txt, delta_clr = _delta_str(cur_closed, prev_closed)
with m2:
    with st.container(border=True):
        st.html(metric_card("Closed (7d)", f"{cur_closed:,}", delta_txt, delta_clr))

# Net new — invert because negative is good (closing more than opening)
net = cur_opened - cur_closed
net_color = PALETTE["green"] if net <= 0 else PALETTE["red"]
with m3:
    with st.container(border=True):
        sign = "+" if net > 0 else ""
        st.html(metric_card("Net New (7d)", f"{sign}{net:,}",
                            "backlog shrinking" if net <= 0 else "backlog growing",
                            net_color))

# Open backlog count
open_count_row = _recent(daily, 1)  # won't work well — use a direct approach
# Actually just sum net_new over all time for a rough open count
# Better: use the tickets_open view count
with m4:
    with st.container(border=True):
        open_df = query_view("tickets_open")
        st.html(metric_card("Open Backlog", f"{len(open_df):,}",
                            "currently unresolved", PALETTE["secondary"]))


# ── Row 2 — Daily volume trend ──────────────────────────────────────

st.html(section_label("Volume"))

with st.container(border=True):
    st.html(card_header("Daily Tickets", "opened vs closed, weekdays",
                        source="notion_sync.tickets_daily"))

    if not daily.empty:
        # Weekdays only, last 90 days for readability
        cutoff_90 = pd.Timestamp.now().normalize() - pd.Timedelta(days=90)
        plot_df = daily[
            (daily["ticket_date"] >= cutoff_90)
            & (daily["ticket_date"].dt.dayofweek < 5)
        ].sort_values("ticket_date")

        fig = go.Figure()

        # Opened — brand blue area
        fig.add_trace(go.Scatter(
            x=plot_df["ticket_date"], y=plot_df["opened"],
            name="Opened",
            mode="lines",
            line=dict(color=CHART_COLORS[0], width=2, shape="spline"),
            fill="tozeroy",
            fillcolor="rgba(43,123,233,0.08)",
            hovertemplate="%{x|%b %d}<br><b>%{y:,.0f}</b> opened<extra></extra>",
        ))

        # Closed — dark blue line
        fig.add_trace(go.Scatter(
            x=plot_df["ticket_date"], y=plot_df["closed"],
            name="Closed",
            mode="lines",
            line=dict(color=PALETTE["blue_dark"], width=2, shape="spline",
                      dash="dot"),
            hovertemplate="%{x|%b %d}<br><b>%{y:,.0f}</b> closed<extra></extra>",
        ))

        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
        fig.update_layout(**chart_layout(
            height=340,
            showlegend=True,
            legend=dict(
                orientation="h", y=1.06, x=1, xanchor="right",
                font=dict(size=11, color=PALETTE["secondary"]),
            ),
            xaxis=dict(gridcolor="rgba(0,0,0,0)"),
            yaxis=dict(gridcolor=PALETTE["grid"]),
            margin=dict(l=0, r=0, t=32, b=0),
        ))
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False})
