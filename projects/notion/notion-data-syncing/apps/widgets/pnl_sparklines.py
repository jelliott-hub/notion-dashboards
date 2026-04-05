"""pnl_sparklines — Small multiples: one card per business line with sparkline + key metrics."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import PALETTE

DEFAULT_HEIGHT = 320

BIZ_ORDER = ["SaaS Platform", "SaaS Relay", "Solutions", "Support"]
BIZ_COLORS = {
    "SaaS Platform": "#2B7BE9",
    "SaaS Relay":    "#1A5FC7",
    "Solutions":     "#F59E0B",
    "Support":       "#94A3B8",
}


def _sparkline(series: pd.Series, color: str, height: int = 60) -> go.Figure:
    """Tiny sparkline figure — no axes, no labels, just the line."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=series.index, y=series.values,
        mode="lines",
        line=dict(color=color, width=2, shape="spline"),
        fill="tozeroy",
        fillcolor=color.replace(")", ",0.08)").replace("rgb", "rgba") if "rgb" in color
                  else f"{color}14",
        hoverinfo="skip",
    ))
    # End dot
    fig.add_trace(go.Scatter(
        x=[series.index[-1]], y=[series.values[-1]],
        mode="markers",
        marker=dict(size=6, color=color, line=dict(color="white", width=1.5)),
        hoverinfo="skip",
    ))
    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig


def _delta_html(current: float, previous: float) -> str:
    if previous == 0:
        return ""
    pct = (current - previous) / previous * 100
    arrow = "&#9650;" if pct >= 0 else "&#9660;"
    color = PALETTE["green"] if pct >= 0 else PALETTE["red"]
    return f'<span style="color:{color};font-size:11px;font-weight:600;">{arrow} {abs(pct):.1f}%</span>'


def render():
    df = query_view("pnl_monthly")
    if df.empty:
        st.warning("No P&L data available.")
        return

    df["month_start"] = pd.to_datetime(df["month_start"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df = df.dropna(subset=["month_start"])

    rev = df[df["pnl_section"] == "Revenue"]
    cogs = df[df["pnl_section"] == "COGS"]

    cols = st.columns(4, gap="small")

    for i, biz in enumerate(BIZ_ORDER):
        biz_rev = rev[rev["business_line"] == biz].groupby("month_start")["amount"].sum().sort_index()
        biz_cogs = cogs[cogs["business_line"] == biz].groupby("month_start")["amount"].sum().sort_index()

        if biz_rev.empty:
            continue

        latest_rev = biz_rev.iloc[-1]
        prev_rev = biz_rev.iloc[-2] if len(biz_rev) >= 2 else 0
        total_cogs = biz_cogs.reindex(biz_rev.index).fillna(0)
        latest_cogs = total_cogs.iloc[-1] if not total_cogs.empty else 0
        margin = ((latest_rev - latest_cogs) / latest_rev * 100) if latest_rev else 0

        color = BIZ_COLORS.get(biz, "#2B7BE9")
        delta = _delta_html(latest_rev, prev_rev)

        with cols[i]:
            with st.container(border=True):
                st.html(f"""
                <div style="padding:2px 0;">
                    <div style="font-size:10px;font-weight:600;color:{PALETTE['secondary']};
                                text-transform:uppercase;letter-spacing:0.8px;
                                white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{biz}</div>
                    <div style="display:flex;align-items:baseline;gap:8px;margin:4px 0 0 0;">
                        <span style="font-size:22px;font-weight:600;color:{PALETTE['ink']};
                                     letter-spacing:-0.5px;">${latest_rev:,.0f}</span>
                        {delta}
                    </div>
                    <div style="font-size:10px;color:{PALETTE['tertiary']};margin-top:2px;">
                        {f'{margin:.0f}% margin' if latest_cogs > 0 else 'No COGS'}
                        &nbsp;&middot;&nbsp; COGS ${latest_cogs:,.0f}
                    </div>
                </div>
                """)
                st.plotly_chart(
                    _sparkline(biz_rev, color, height=55),
                    use_container_width=True,
                    config={"displayModeBar": False},
                )


if __name__ == "__main__":
    widget_page("P&L by Business Line", DEFAULT_HEIGHT)
    render()
