"""finance_variance_heatmap — MoM % change heatmap by GL account x month."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, PALETTE

DEFAULT_HEIGHT = 420


def render():
    df = query_view("finance_variance")
    if df.empty:
        st.warning("No variance data available.")
        return

    df["mom_pct_change"] = pd.to_numeric(df["mom_pct_change"], errors="coerce").fillna(0)
    df["report_month"] = pd.to_datetime(df["report_month"], errors="coerce")
    df["month_label"] = df["report_month"].dt.strftime("%b %Y")

    # Top 20 accounts by max abs swing for readability
    top_accts = (
        df.groupby("gl_name")["mom_pct_change"]
        .apply(lambda s: s.abs().max())
        .nlargest(20)
        .index
    )
    hm_df = df[df["gl_name"].isin(top_accts)].copy()

    if hm_df.empty or hm_df["gl_name"].nunique() < 2:
        st.info("Not enough data for heatmap.")
        return

    # Pivot for heatmap
    pivot = (
        hm_df.pivot_table(index="gl_name", columns="month_label",
                          values="mom_pct_change", aggfunc="first")
        .fillna(0)
    )

    # Sort months chronologically
    month_order = (
        hm_df[["report_month", "month_label"]]
        .drop_duplicates()
        .sort_values("report_month")["month_label"]
        .tolist()
    )
    pivot = pivot.reindex(columns=[m for m in month_order if m in pivot.columns])

    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale=[
            [0, "rgba(231,76,60,0.7)"],
            [0.35, "rgba(231,76,60,0.15)"],
            [0.5, "rgba(241,245,249,1)"],
            [0.65, "rgba(34,197,94,0.15)"],
            [1, "rgba(34,197,94,0.7)"],
        ],
        zmid=0,
        text=[[f"{v:+.0f}%" for v in row] for row in pivot.values],
        texttemplate="%{text}",
        textfont=dict(size=9),
        hovertemplate="%{y}<br>%{x}<br><b>%{z:+.1f}%</b> MoM<extra></extra>",
        colorbar=dict(
            title=dict(text="MoM %", font=dict(size=10, color=PALETTE["secondary"])),
            tickfont=dict(size=9, color=PALETTE["secondary"]),
            thickness=12,
            len=0.6,
        ),
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, -apple-system, sans-serif", size=10, color=PALETTE["secondary"]),
        height=get_height(DEFAULT_HEIGHT),
        margin=dict(l=0, r=0, t=8, b=0),
        xaxis=dict(side="top", tickfont=dict(size=10, color=PALETTE["secondary"])),
        yaxis=dict(automargin=True, tickfont=dict(size=10, color=PALETTE["secondary"]),
                   autorange="reversed"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("Variance Heatmap", DEFAULT_HEIGHT)
    render()
