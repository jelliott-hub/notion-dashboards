# apps/support/tabs/tickets.py
"""Tickets tab — HubSpot ticket metrics with SLA gauge, pipeline funnel, and log drill-through."""

import streamlit as st
import pandas as pd
from streamlit_echarts import st_echarts
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html
from core.charts import area_chart, gauge_chart, funnel_chart


def render():
    monthly_df = query_view("tickets_monthly")
    log_df = query_view("tickets_log")

    if monthly_df.empty and log_df.empty:
        st.warning("No tickets data available.")
        return

    # Coerce monthly types
    if not monthly_df.empty:
        monthly_df["report_month"] = pd.to_datetime(monthly_df["report_month"], errors="coerce")
        for col in ["tickets_opened", "tickets_closed", "net_new", "escalated_count"]:
            if col in monthly_df.columns:
                monthly_df[col] = pd.to_numeric(monthly_df[col], errors="coerce").fillna(0).astype(int)
        for col in ["avg_first_response_hours", "avg_resolution_hours", "median_resolution_hours",
                    "sla_response_on_time_pct", "sla_resolution_on_time_pct"]:
            if col in monthly_df.columns:
                monthly_df[col] = pd.to_numeric(monthly_df[col], errors="coerce").fillna(0)

    # Coerce log types
    if not log_df.empty:
        for ts_col in ["created_at", "closed_at"]:
            if ts_col in log_df.columns:
                log_df[ts_col] = pd.to_datetime(log_df[ts_col], errors="coerce")
        for col in ["resolution_hours", "first_response_hours", "thread_duration_days"]:
            if col in log_df.columns:
                log_df[col] = pd.to_numeric(log_df[col], errors="coerce").fillna(0)
        if "email_count" in log_df.columns:
            log_df["email_count"] = pd.to_numeric(log_df["email_count"], errors="coerce").fillna(0).astype(int)

    # --- KPIs from latest month ---
    latest_month = monthly_df["report_month"].max() if not monthly_df.empty else None
    latest = monthly_df[monthly_df["report_month"] == latest_month] if latest_month is not None else pd.DataFrame()

    opened = int(latest["tickets_opened"].sum()) if not latest.empty and "tickets_opened" in latest.columns else 0
    closed = int(latest["tickets_closed"].sum()) if not latest.empty and "tickets_closed" in latest.columns else 0
    sla_pct = float(latest["sla_resolution_on_time_pct"].mean()) if not latest.empty and "sla_resolution_on_time_pct" in latest.columns else 0.0
    avg_res = float(latest["avg_resolution_hours"].mean()) if not latest.empty and "avg_resolution_hours" in latest.columns else 0.0

    kpis = [
        {"label": "Opened", "value": f"{opened:,}", "color": COLORS["navy"],
         "subtitle": latest_month.strftime("%b %Y") if latest_month is not None and pd.notna(latest_month) else ""},
        {"label": "Closed", "value": f"{closed:,}", "color": COLORS["success"],
         "border_color": COLORS["success"]},
        {"label": "SLA On Time", "value": f"{sla_pct:.1f}%",
         "color": COLORS["success"] if sla_pct >= 80 else COLORS["warning"],
         "border_color": COLORS["success"] if sla_pct >= 80 else COLORS["warning"]},
        {"label": "Avg Resolution", "value": f"{avg_res:.1f}h", "color": COLORS["slate"]},
    ]
    st.html(kpi_strip_html(kpis))

    # --- Charts row 1: burndown + SLA gauge ---
    col1, col2 = st.columns([2, 1])

    with col1:
        # Opened vs Closed trend
        if not monthly_df.empty:
            trend_cols = [c for c in ["tickets_opened", "tickets_closed"] if c in monthly_df.columns]
            if trend_cols:
                trend_df = monthly_df.groupby("report_month", as_index=False)[trend_cols].sum()
                trend_df = trend_df.sort_values("report_month")
                fig = area_chart(trend_df, x="report_month", y_cols=trend_cols,
                                 title="Ticket Burndown — Opened vs Closed", fill=False)
                st.plotly_chart(fig, use_container_width=True)

    with col2:
        # SLA compliance gauge
        gauge_config = gauge_chart(round(sla_pct, 1), "Resolution SLA On Time", suffix="%")
        st_echarts(gauge_config, height="260px")

    # --- Charts row 2: pipeline funnel ---
    if not log_df.empty and "pipeline" in log_df.columns:
        pipeline_counts = (
            log_df.groupby("pipeline", as_index=False).size()
            .rename(columns={"size": "ticket_count"})
        )
        pipeline_counts = pipeline_counts.sort_values("ticket_count", ascending=False)
        if not pipeline_counts.empty:
            fig = funnel_chart(pipeline_counts, stage="pipeline", value="ticket_count",
                               title="Tickets by Pipeline")
            st.plotly_chart(fig, use_container_width=True)

    # --- Ticket log data table ---
    st.markdown("#### Ticket Log")

    if not log_df.empty:
        log_display_cols = [c for c in [
            "hubspot_ticket_id", "subject", "status", "priority", "pipeline",
            "source", "channel", "ticket_intent", "support_effort",
            "sla_status", "response_sla_status",
            "created_at", "closed_at", "resolution_hours", "first_response_hours",
            "customer_name", "accounting_bucket", "client_id",
        ] if c in log_df.columns]
        show_log = log_df[log_display_cols].sort_values(
            "created_at", ascending=False
        ) if "created_at" in log_df.columns else log_df[log_display_cols]

        event = st.dataframe(
            show_log,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
        )

        # --- Detail panel ---
        selected_rows = event.selection.get("rows", []) if event and hasattr(event, "selection") else []
        if selected_rows:
            idx = selected_rows[0]
            orig_idx = show_log.index[idx]
            row = log_df.loc[orig_idx]

            thread_summary = str(row.get("thread_summary", "") or "")
            if len(thread_summary) > 200:
                thread_summary = thread_summary[:200] + "..."

            fields = {
                "Ticket ID": str(row.get("hubspot_ticket_id", "—")),
                "Subject": str(row.get("subject", "—")),
                "Status": str(row.get("status", "—")),
                "Priority": str(row.get("priority", "—")),
                "Pipeline": str(row.get("pipeline", "—")),
                "Source": str(row.get("source", "—")),
                "Channel": str(row.get("channel", "—")),
                "Intent": str(row.get("ticket_intent", "—")),
                "Ops Disposition": str(row.get("ops_disposition", "—")),
                "Support Effort": str(row.get("support_effort", "—")),
                "Operational Impact": str(row.get("operational_impact", "—")),
                "Classification": str(row.get("ticket_classification", "—")),
                "Sender Persona": str(row.get("sender_persona", "—")),
                "Created": str(row.get("created_at", "—"))[:19],
                "Closed": str(row.get("closed_at", "—"))[:19],
                "Resolution Hours": f"{float(row.get('resolution_hours', 0)):.1f}h",
                "First Response Hours": f"{float(row.get('first_response_hours', 0)):.1f}h",
                "SLA Status": str(row.get("sla_status", "—")),
                "Response SLA": str(row.get("response_sla_status", "—")),
                "Email Count": str(row.get("email_count", "—")),
                "Thread Duration (days)": str(row.get("thread_duration_days", "—")),
                "Client ID": str(row.get("client_id", "—")),
                "Customer": str(row.get("customer_name", "—")),
                "Accounting Bucket": str(row.get("accounting_bucket", "—")),
                "Thread Summary": thread_summary or "—",
            }
            subject = str(row.get("subject", "Ticket Detail"))
            st.html(detail_panel_html(subject, fields))
    else:
        st.info("Ticket log not available.")
