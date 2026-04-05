"""revenue_nrr_grr — NRR and GRR metric cards."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import pandas as pd
from apps.widgets._base import widget_page
from core.db import query_view
from core.style import metric_card, PALETTE

DEFAULT_HEIGHT = 120


def render():
    retention = query_view("revenue_retention_summary")
    if retention.empty:
        st.warning("No retention data available.")
        return

    retention["evaluation_month"] = pd.to_datetime(retention["evaluation_month"], errors="coerce")
    for c in ["ttm_current", "ttm_prior", "ttm_delta", "customer_count"]:
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

    if len(ret_monthly) < 1:
        st.info("Not enough retention data.")
        return

    latest = ret_monthly.iloc[-1]
    prev = ret_monthly.iloc[-2] if len(ret_monthly) > 1 else None

    nrr = latest["nrr"]
    grr = latest["grr"]
    nrr_color = PALETTE["green"] if nrr >= 100 else PALETTE["red"]
    grr_color = PALETTE["green"] if grr >= 90 else (PALETTE["amber"] if grr >= 80 else PALETTE["red"])

    nrr_sub, grr_sub = "", ""
    if prev is not None:
        d_nrr = nrr - prev["nrr"]
        nrr_sub = f"{'+' if d_nrr >= 0 else ''}{d_nrr:.1f}pp MoM"
        d_grr = grr - prev["grr"]
        grr_sub = f"{'+' if d_grr >= 0 else ''}{d_grr:.1f}pp MoM"

    m1, m2 = st.columns(2)
    with m1:
        with st.container(border=True):
            st.html(metric_card("Net Revenue Retention", f"{nrr:.1f}%", nrr_sub, nrr_color))
    with m2:
        with st.container(border=True):
            st.html(metric_card("Gross Revenue Retention", f"{grr:.1f}%", grr_sub, grr_color))


if __name__ == "__main__":
    widget_page("NRR / GRR", DEFAULT_HEIGHT)
    render()
