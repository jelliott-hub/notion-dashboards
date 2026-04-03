# apps/finance/tabs/close_dashboard.py
"""Close Dashboard tab — month-end close health, blocking items, reconciliation status."""

import streamlit as st
import pandas as pd
from streamlit_echarts import st_echarts
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html, status_pill_html
from core.charts import area_chart, gauge_chart, donut_chart, status_bars


def _safe(val, fmt="{}", default="—"):
    """Safely format a value that might be None/NaN."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    return fmt.format(val)


def render():
    df = query_view("finance_close_dashboard")
    if df.empty:
        st.warning("No close dashboard data available.")
        return

    # Coerce numeric columns — REST API returns them as strings/None
    num_cols = ["total_revenue", "total_cogs", "gross_margin", "gross_margin_pct",
                "pnl_accounts_passing", "pnl_accounts_failing", "pnl_accounts_total",
                "clearing_open_count", "clearing_open_abs_total", "qb_ar_total",
                "tc_oi_ar", "ar_delta", "catchall_uncaptured_lines", "catchall_uncaptured_total",
                "deferred_rev_balance", "checklist_pct_complete"]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Month selector
    months = sorted(df["report_month"].unique(), reverse=True)
    selected_month = st.selectbox("Report Month", months, format_func=lambda x: pd.Timestamp(x).strftime("%B %Y"))
    row = df[df["report_month"] == selected_month].iloc[0]

    # --- KPI Strip ---
    health_color = {
        "GREEN": COLORS["success"], "YELLOW": COLORS["warning"], "RED": COLORS["error"],
        "GOOD": COLORS["success"], "WARN": COLORS["warning"], "FAIL": COLORS["error"],
    }.get(str(row.get("overall_health", "")).upper(), COLORS["slate"])
    kpis = [
        {"label": "Overall Health", "value": str(row.get("overall_health", "—")), "color": health_color},
        {"label": "Gross Margin", "value": _safe(row.get("gross_margin_pct"), "{:.1f}%"), "color": COLORS["navy"]},
        {"label": "Revenue", "value": _safe(row.get("total_revenue"), "${:,.0f}"), "color": COLORS["navy"]},
        {"label": "Failing", "value": str(int(row.get("pnl_accounts_failing") or 0)), "color": COLORS["error"],
         "border_color": COLORS["error"] if (row.get("pnl_accounts_failing") or 0) > 0 else None},
    ]
    st.html(kpi_strip_html(kpis))

    # --- Charts Row 1: Revenue trend + Margin gauge ---
    col1, col2 = st.columns([2, 1])

    with col1:
        trend_df = df.sort_values("report_month")
        fig = area_chart(
            trend_df, x="report_month", y_cols=["total_revenue", "total_cogs"],
            title="Revenue vs COGS Trend", dash_cols=["total_cogs"],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        margin_val = float(row["gross_margin_pct"]) if pd.notna(row.get("gross_margin_pct")) else 0
        st_echarts(
            gauge_chart(margin_val, "Gross Margin"),
            height="250px",
        )
        c1, c2 = st.columns(2)
        if len(df) >= 2:
            prior = df.sort_values("report_month", ascending=False).iloc[1]
            c1.metric("Prior Month", _safe(prior.get("gross_margin_pct"), "{:.1f}%"))
        c2.metric("Checklist", _safe(row.get("checklist_pct_complete"), "{:.0f}%"))

    # --- Charts Row 2: Close progress donut + Recon status bars ---
    col3, col4 = st.columns(2)

    with col3:
        passing = int(row.get("pnl_accounts_passing") or 0)
        failing = int(row.get("pnl_accounts_failing") or 0)
        total_accts = int(row.get("pnl_accounts_total") or 0)
        in_progress = max(0, total_accts - passing - failing)
        st_echarts(
            donut_chart(
                labels=["Passing", "In Progress", "Failing"],
                values=[passing, in_progress, failing],
                title="P&L Account Status",
                colors=[COLORS["success"], COLORS["warning"], COLORS["error"]],
            ),
            height="250px",
        )

    with col4:
        recon_items = [
            {"label": "P&L Accounts", "value": passing, "max": total_accts,
             "status": "success" if failing == 0 else "warning"},
            {"label": "Cash Recon", "value": 100 if str(row.get("cash_recon_status")) == "PASS" else 50,
             "max": 100, "status": "success" if str(row.get("cash_recon_status")) == "PASS" else "warning"},
            {"label": "AR Recon", "value": 100 if "PASS" in str(row.get("ar_recon_status", "")) else 70,
             "max": 100, "status": "success" if "PASS" in str(row.get("ar_recon_status", "")) else "warning"},
            {"label": "Clearing", "value": max(0, 100 - int(row.get("clearing_open_count") or 0) * 10),
             "max": 100, "status": "success" if (row.get("clearing_open_count") or 0) == 0 else "warning"},
        ]
        fig = status_bars(recon_items, title="Reconciliation Status")
        st.plotly_chart(fig, use_container_width=True)

    # --- Status Pills ---
    cols = st.columns(4)
    for col, (label, status_val) in zip(cols, [
        ("Cash Recon", row["cash_recon_status"]),
        ("AR Recon", row["ar_recon_status"]),
        ("Clearing", row["clearing_status"]),
        ("Catchall", row["catchall_status"]),
    ]):
        status_type = "success" if "PASS" in str(status_val) or "CLEAN" in str(status_val) else (
            "error" if "FAIL" in str(status_val) else "warning")
        col.html(f'<div style="text-align:center;">'
                 f'<div style="font-size:11px;color:{COLORS["slate"]};margin-bottom:4px;">{label}</div>'
                 f'{status_pill_html(str(status_val), status_type)}</div>')

    # --- Blocking Items Table ---
    if row["blocking_items"] and len(row["blocking_items"]) > 0:
        st.markdown("#### Blocking Items")
        for item in row["blocking_items"]:
            with st.expander(str(item), expanded=False):
                st.html(detail_panel_html(str(item), {
                    "Status": "Blocking",
                    "Report Month": str(selected_month),
                    "Action": "Review in P&L Reconciliation tab",
                }))
