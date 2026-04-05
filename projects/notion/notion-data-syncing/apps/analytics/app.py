"""Analytics — Stripe-inspired bento dashboard.

Single-page, chromeless layout designed for Notion embeds.
Run with: streamlit run apps/analytics/app.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from core.db import query_view
from core.style import (
    inject_css, metric_card, card_header, section_label,
    page_header, chart_layout, CHART_COLORS, PALETTE,
)

# ── Page config ──────────────────────────────────────────────────────
st.set_page_config(page_title="Analytics", page_icon="◆", layout="wide")
inject_css()
st.html(page_header("Analytics", "Operations overview"))


# ── Data ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load():
    return {
        "calls": query_view("calls_weekly"),
        "agents": query_view("calls_by_agent"),
        "topics": query_view("calls_by_topic"),
        "deals": query_view("sales_deals"),
    }


data = load()
calls = data["calls"].copy()
agents = data["agents"].copy()
topics = data["topics"].copy()
deals = data["deals"].copy()


# ── Type coercion ────────────────────────────────────────────────────

def _num(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

def _dt(df, col):
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")


_dt(calls, "call_week")
_num(calls, ["total_calls", "answered", "abandoned", "missed", "voicemail"])
_num(calls, ["answer_rate", "avg_talk_min", "avg_wait_min"])

_dt(agents, "call_month")
_num(agents, ["total_calls", "answered", "answer_rate", "avg_talk_min",
              "avg_wait_min", "total_talk_min"])

_num(topics, ["total_calls"])

_dt(deals, "close_date")


# ── Metric helpers ───────────────────────────────────────────────────

def _latest_week_total(col="total_calls"):
    if calls.empty:
        return 0, 0
    latest = calls["call_week"].max()
    cur = int(calls.loc[calls["call_week"] == latest, col].sum())
    prev_wk = latest - pd.Timedelta(weeks=1)
    prev = int(calls.loc[calls["call_week"] == prev_wk, col].sum())
    return cur, prev


def _delta_str(cur, prev, invert=False):
    """Return '↑ 8.2%' or '↓ 3.1%' with color. invert=True means down is good."""
    if prev == 0:
        return "", None
    pct = (cur - prev) / prev * 100
    up = pct >= 0
    good = (not up) if invert else up
    arrow = "↑" if up else "↓"
    color = PALETTE["green"] if good else PALETTE["red"]
    return f"{arrow} {abs(pct):.1f}% vs prior week", color


# ── Row 1 — Metric cards ────────────────────────────────────────────

m1, m2, m3, m4 = st.columns(4)

# Total calls
cur_calls, prev_calls = _latest_week_total("total_calls")
delta_txt, delta_clr = _delta_str(cur_calls, prev_calls)
with m1:
    with st.container(border=True):
        st.html(metric_card("Weekly Calls", f"{cur_calls:,}", delta_txt, delta_clr))

# Answer rate (weighted)
if not calls.empty:
    latest = calls["call_week"].max()
    wk = calls[calls["call_week"] == latest]
    ans = wk["answered"].sum()
    tot = wk["total_calls"].sum()
    rate = (ans / tot * 100) if tot else 0
    rate_color = PALETTE["green"] if rate >= 80 else PALETTE["amber"]
    with m2:
        with st.container(border=True):
            st.html(metric_card("Answer Rate", f"{rate:.0f}%",
                                "target: 80%", rate_color))

# Abandoned
cur_abn, prev_abn = _latest_week_total("abandoned")
abn_txt, abn_clr = _delta_str(cur_abn, prev_abn, invert=True)
with m3:
    with st.container(border=True):
        st.html(metric_card("Abandoned", f"{cur_abn:,}", abn_txt, abn_clr))

# Active deals
with m4:
    with st.container(border=True):
        deal_count = len(deals) if not deals.empty else 0
        st.html(metric_card("Pipeline Deals", str(deal_count)))


# ── Row 2 — Call trend + Topic breakdown ─────────────────────────────

st.html(section_label("Trends"))
c1, c2 = st.columns([3, 2])

with c1:
    with st.container(border=True):
        st.html(card_header("Call Volume", "weekly", source="notion_sync.calls_weekly"))
        if not calls.empty:
            weekly = (calls.groupby("call_week")["total_calls"]
                      .sum().reset_index().sort_values("call_week"))
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=weekly["call_week"], y=weekly["total_calls"],
                mode="lines",
                line=dict(color=CHART_COLORS[0], width=2.5, shape="spline"),
                fill="tozeroy",
                fillcolor="rgba(43,123,233,0.08)",
                hovertemplate="%{x|%b %d, %Y}<br><b>%{y:,.0f}</b> calls<extra></extra>",
            ))
            fig.update_layout(**chart_layout(
                height=300,
                xaxis=dict(gridcolor="rgba(0,0,0,0)"),
            ))
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False})

with c2:
    with st.container(border=True):
        st.html(card_header("Top Topics", "by volume", source="notion_sync.calls_by_topic"))
        if not topics.empty and "support_category" in topics.columns:
            top = (topics.groupby("support_category")["total_calls"]
                   .sum().nlargest(8).sort_values())
            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=top.index, x=top.values,
                orientation="h",
                marker=dict(color=CHART_COLORS[0], cornerradius=4),
                hovertemplate="%{y}<br><b>%{x:,.0f}</b> calls<extra></extra>",
            ))
            fig.update_layout(**chart_layout(
                height=300,
                margin=dict(l=0, r=16, t=8, b=0),
                xaxis=dict(gridcolor=PALETTE["grid"]),
                yaxis=dict(gridcolor="rgba(0,0,0,0)", automargin=True),
            ))
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False})


# ── Row 3 — Agent leaderboard + Answer rate trend ────────────────────

st.html(section_label("Performance"))
c3, c4 = st.columns([2, 3])

with c3:
    with st.container(border=True):
        st.html(card_header("Agents", "by call volume", source="notion_sync.calls_by_agent"))
        if not agents.empty:
            board = (agents.groupby("agent_name")["total_calls"]
                     .sum().nlargest(10).sort_values())
            bar_colors = [CHART_COLORS[0]] * len(board)
            bar_colors[-1] = CHART_COLORS[1]  # top agent in dark blue
            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=board.index, x=board.values,
                orientation="h",
                marker=dict(color=bar_colors, cornerradius=4),
                hovertemplate="%{y}<br><b>%{x:,.0f}</b> calls<extra></extra>",
            ))
            fig.update_layout(**chart_layout(
                height=340,
                margin=dict(l=0, r=16, t=8, b=0),
                xaxis=dict(gridcolor=PALETTE["grid"]),
                yaxis=dict(gridcolor="rgba(0,0,0,0)", automargin=True),
            ))
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False})

with c4:
    with st.container(border=True):
        st.html(card_header("Answer Rate", "weekly trend", source="notion_sync.calls_weekly"))
        if not calls.empty and "answer_rate" in calls.columns:
            # Weighted weekly answer rate
            wk_agg = (calls.groupby("call_week")
                      .agg(answered=("answered", "sum"),
                           total=("total_calls", "sum"))
                      .reset_index().sort_values("call_week"))
            wk_agg["rate"] = (wk_agg["answered"] / wk_agg["total"] * 100
                              ).fillna(0)

            fig = go.Figure()
            # 80% target line
            fig.add_hline(
                y=80,
                line=dict(color=PALETTE["border"], width=1, dash="dot"),
                annotation=dict(text="80% target", font=dict(
                    size=10, color=PALETTE["tertiary"])),
            )
            fig.add_trace(go.Scatter(
                x=wk_agg["call_week"], y=wk_agg["rate"],
                mode="lines+markers",
                line=dict(color=PALETTE["blue_dark"], width=2.5, shape="spline"),
                marker=dict(size=5, color=PALETTE["blue_dark"]),
                fill="tozeroy",
                fillcolor="rgba(26,95,199,0.06)",
                hovertemplate="%{x|%b %d}<br><b>%{y:.1f}%</b><extra></extra>",
            ))
            fig.update_layout(**chart_layout(
                height=340,
                yaxis=dict(gridcolor=PALETTE["grid"], range=[0, 105]),
                xaxis=dict(gridcolor="rgba(0,0,0,0)"),
            ))
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False})


# ── Row 4 — Call mix: stacked columns + summary table ────────────────

st.html(section_label("Call Mix"))

with st.container(border=True):
    st.html(card_header("Daily Calls", "weekdays only",
                        source="notion_sync.calls_log"))

    log = query_view("calls_log")
    if not log.empty:
        log["call_date"] = pd.to_datetime(log["call_date"], errors="coerce")
        log = log[log["call_date"].dt.dayofweek < 5]  # weekdays only

        # Categorize every call into one of 4 buckets
        def _categorize(row):
            if row["is_bland_call"]:
                return "Bland"
            if row["direction"] == "outbound":
                return "Outbound"
            if row["call_status"] == "voicemail":
                return "Inbound — Voicemail"
            return "Inbound — Answered"

        log["category"] = log.apply(_categorize, axis=1)

        cat_order = ["Inbound — Answered", "Inbound — Voicemail",
                     "Outbound", "Bland"]
        cat_colors = {
            "Inbound — Answered":  "#1A5FC7",           # dark blue
            "Inbound — Voicemail": "#F59E0B",           # orange
            "Outbound":            "#94A3B8",           # grey
            "Bland":               "rgba(43,123,233,0.30)",  # opaque blue wash
        }

        # ── Stacked column chart with % labels ───────────
        cat_daily = (log.groupby(["call_date", "category"])
                     .size().reset_index(name="calls"))

        # Pre-compute each segment's % of its day's total
        day_totals = cat_daily.groupby("call_date")["calls"].transform("sum")
        cat_daily["pct"] = (cat_daily["calls"] / day_totals * 100)

        fig = go.Figure()
        for cat in cat_order:
            d = cat_daily[cat_daily["category"] == cat].sort_values("call_date")
            if d.empty:
                continue
            labels = [f"{p:.0f}%" for p in d["pct"]]
            text_color = "white" if cat != "Bland" else PALETTE["navy"]
            fig.add_trace(go.Bar(
                x=d["call_date"], y=d["calls"],
                name=cat,
                text=labels,
                textposition="inside",
                textangle=0,
                insidetextanchor="middle",
                constraintext="none",
                cliponaxis=False,
                textfont=dict(size=9, color=text_color, family="Inter"),
                marker=dict(color=cat_colors[cat], cornerradius=2,
                            line=dict(width=0)),
                width=1000 * 60 * 60 * 14,
                hovertemplate=(
                    "%{x|%b %d}<br>%{fullData.name}: "
                    "<b>%{y}</b><extra></extra>"
                ),
            ))

        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
        fig.update_layout(**chart_layout(
            height=380,
            barmode="stack",
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
