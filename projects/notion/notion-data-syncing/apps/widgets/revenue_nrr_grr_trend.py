"""revenue_nrr_grr_trend — NRR and GRR dual line chart over time."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import chart_layout, CHART_COLORS, PALETTE

DEFAULT_HEIGHT = 300


def render():
    retention = query_view("revenue_retention_summary")
    if retention.empty:
        st.warning("No retention data available.")
        return

    retention["evaluation_month"] = pd.to_datetime(retention["evaluation_month"], errors="coerce")
    for c in ["ttm_current", "ttm_prior", "ttm_delta"]:
        if c in retention.columns:
            retention[c] = pd.to_numeric(retention[c], errors="coerce").fillna(0)

    existing_cats = ["expansion", "contraction", "flat", "churned"]
    ret_existing = retention[retention["retention_category"].isin(existing_cats)]
    ret_monthly = (ret_existing.groupby("evaluation_month")
                   .agg(ttm_cur=("ttm_current", "sum"),
                        ttm_prior=("ttm_prior", "sum"))
                   .reset_index().sort_values("evaluation_month"))
    ret_monthly["nrr"] = (ret_monthly["ttm_cur"] / ret_monthly["ttm_prior"] * 100).round(1)

    loss_cats = ["contraction", "churned"]
    ret_loss = (retention[retention["retention_category"].isin(loss_cats)]
                .groupby("evaluation_month")["ttm_delta"].sum().reset_index())
    ret_loss.columns = ["evaluation_month", "loss_delta"]
    ret_monthly = ret_monthly.merge(ret_loss, on="evaluation_month", how="left")
    ret_monthly["loss_delta"] = ret_monthly["loss_delta"].fillna(0)
    ret_monthly["grr"] = ((ret_monthly["ttm_prior"] + ret_monthly["loss_delta"])
                          / ret_monthly["ttm_prior"] * 100).round(1)

    ret_monthly = ret_monthly[ret_monthly["evaluation_month"] >= "2025-01-01"]
    if ret_monthly.empty:
        st.info("No 2025+ retention data.")
        return

    fig = go.Figure()
    fig.add_hline(y=100, line_dash="dot", line_color=PALETTE["secondary"],
                  line_width=1, opacity=0.5)
    fig.add_trace(go.Scatter(
        x=ret_monthly["evaluation_month"], y=ret_monthly["nrr"],
        name="NRR", mode="lines",
        line=dict(color=CHART_COLORS[0], width=2.5, shape="spline"),
        hovertemplate="%{x|%b %Y}<br>NRR: <b>%{y:.1f}%</b><extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=ret_monthly["evaluation_month"], y=ret_monthly["grr"],
        name="GRR", mode="lines",
        line=dict(color=PALETTE["amber"], width=2.5, shape="spline"),
        hovertemplate="%{x|%b %Y}<br>GRR: <b>%{y:.1f}%</b><extra></extra>",
    ))

    fig.update_layout(**chart_layout(
        height=get_height(DEFAULT_HEIGHT),
        showlegend=True,
        legend=dict(orientation="h", y=-0.15, x=0,
                    font=dict(size=11, color=PALETTE["secondary"])),
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        yaxis=dict(gridcolor=PALETTE["grid"], ticksuffix="%"),
    ))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


if __name__ == "__main__":
    widget_page("NRR & GRR Trend", DEFAULT_HEIGHT)
    render()
