# apps/finance/tabs/close_dashboard.py
"""Close Dashboard tab — month-end close health, blocking items, reconciliation status."""

import streamlit as st
import pandas as pd
from streamlit_echarts import st_echarts
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html, status_pill_html
from core.charts import area_chart, gauge_chart, donut_chart, status_bars


def render():
    df = query_view("finance_close_dashboard")
    if df.empty:
        st.warning("No close dashboard data available.")
        return

    # Month selector
    months = sorted(df["report_month"].unique(), reverse=True)
    selected_month = st.selectbox("Report Month", months, format_func=lambda x: pd.Timestamp(x).strftime("%B %Y"))
    row = df[df["report_month"] == selected_month].iloc[0]

    # --- KPI Strip ---
    health_color = {"GOOD": COLORS["success"], "WARN": COLORS["warning"], "FAIL": COLORS["error"]}.get(
        row["overall_health"], COLORS["slate"])
    kpis = [
        {"label": "Overall Health", "value": row["overall_health"], "color": health_color},
        {"label": "Gross Margin", "value": f"{row['gross_margin_pct']:.1f}%", "color": COLORS["navy"]},
        {"label": "Revenue", "value": f"${row['total_revenue']:,.0f}", "color": COLORS["navy"]},
        {"label": "Failing", "value": str(row["pnl_accounts_failing"]), "color": COLORS["error"],
         "border_color": COLORS["error"] if row["pnl_accounts_failing"] > 0 else None},
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
        st_echarts(
            gauge_chart(float(row["gross_margin_pct"]), "Gross Margin"),
            height="250px",
        )
        c1, c2 = st.columns(2)
        if len(df) >= 2:
            prior = df.sort_values("report_month", ascending=False).iloc[1]
            c1.metric("Prior Month", f"{prior['gross_margin_pct']:.1f}%")
        c2.metric("Checklist", f"{row['checklist_pct_complete']:.0f}%")

    # --- Charts Row 2: Close progress donut + Recon status bars ---
    col3, col4 = st.columns(2)

    with col3:
        passing = int(row["pnl_accounts_passing"])
        failing = int(row["pnl_accounts_failing"])
        in_progress = max(0, int(row["pnl_accounts_total"]) - passing - failing)
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
            {"label": "P&L Accounts", "value": passing, "max": int(row["pnl_accounts_total"]),
             "status": "success" if failing == 0 else "warning"},
            {"label": "Cash Recon", "value": 100 if row["cash_recon_status"] == "PASS" else 50,
             "max": 100, "status": "success" if row["cash_recon_status"] == "PASS" else "warning"},
            {"label": "AR Recon", "value": 100 if "PASS" in str(row["ar_recon_status"]) else 70,
             "max": 100, "status": "success" if "PASS" in str(row["ar_recon_status"]) else "warning"},
            {"label": "Clearing", "value": max(0, 100 - int(row["clearing_open_count"]) * 10),
             "max": 100, "status": "success" if row["clearing_open_count"] == 0 else "warning"},
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
