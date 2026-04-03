# apps/finance/tabs/accounting_inbox.py
"""Accounting Inbox tab — email volume, reply rates, classification trends."""

import streamlit as st
import pandas as pd
from streamlit_echarts import st_echarts
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html
from core.charts import area_chart, gauge_chart


def render():
    df = query_view("finance_accounting_inbox")
    if df.empty:
        st.warning("No accounting inbox data available.")
        return

    # Build month_date column from year + month
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["month"] = pd.to_numeric(df["month"], errors="coerce")
    df = df.dropna(subset=["year", "month"])
    df["month_date"] = pd.to_datetime(
        df["year"].astype(int).astype(str) + "-" +
        df["month"].astype(int).astype(str).str.zfill(2) + "-01"
    )
    df["month_label"] = df["month_date"].dt.strftime("%b %Y")

    # Ensure numeric columns
    for col in ["total_emails", "reply_rate_pct", "avg_response_min",
                "unique_customers", "inbound", "outbound", "internal",
                "replied", "conversations", "avg_thread_depth",
                "avg_turns_when_replied", "with_attachments"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # --- KPI Strip (latest month aggregated) ---
    latest = df.sort_values("month_date").iloc[-1] if not df.empty else None

    if latest is not None:
        total_emails = int(df["total_emails"].sum())
        avg_reply_rate = df["reply_rate_pct"].mean()
        avg_response = df["avg_response_min"].mean()
        unique_customers = int(df["unique_customers"].sum())
    else:
        total_emails, avg_reply_rate, avg_response, unique_customers = 0, 0.0, 0.0, 0

    kpis = [
        {"label": "Total Emails", "value": f"{total_emails:,}", "color": COLORS["navy"]},
        {"label": "Avg Reply Rate", "value": f"{avg_reply_rate:.1f}%",
         "color": COLORS["success"] if avg_reply_rate >= 80 else COLORS["warning"],
         "border_color": COLORS["success"] if avg_reply_rate >= 80 else COLORS["warning"]},
        {"label": "Avg Response Time", "value": f"{avg_response:.0f} min", "color": COLORS["blue"]},
        {"label": "Unique Customers", "value": f"{unique_customers:,}", "color": COLORS["slate"]},
    ]
    st.html(kpi_strip_html(kpis))

    # --- Charts Row ---
    col1, col2 = st.columns([3, 1])

    with col1:
        # Monthly volume trend by classification
        # Pivot to get one row per month_date with classification as columns
        if "email_classification" in df.columns and df["email_classification"].notna().any():
            trend_df = (
                df.groupby(["month_date", "email_classification"], as_index=False)["total_emails"]
                .sum()
                .pivot(index="month_date", columns="email_classification", values="total_emails")
                .fillna(0)
                .reset_index()
                .sort_values("month_date")
            )
            y_cols = [c for c in trend_df.columns if c != "month_date"]
            if y_cols:
                fig = area_chart(
                    trend_df, x="month_date", y_cols=y_cols,
                    title="Monthly Email Volume by Classification",
                    fill=False,
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No classification data available for trend chart.")
        else:
            # Fallback: total emails trend
            total_trend = (
                df.groupby("month_date", as_index=False)["total_emails"]
                .sum()
                .sort_values("month_date")
            )
            fig = area_chart(
                total_trend, x="month_date", y_cols=["total_emails"],
                title="Monthly Email Volume",
                fill=False,
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Reply rate gauge using latest month's rate
        gauge_value = float(latest["reply_rate_pct"]) if latest is not None else 0.0
        st_echarts(
            gauge_chart(gauge_value, "Reply Rate", suffix="%", min_val=0, max_val=100),
            height="250px",
        )
        if latest is not None:
            st.caption(f"Latest: {latest['month_label']}")

    # --- Data Table ---
    st.markdown("#### Monthly Inbox Detail")
    table_cols_available = [
        c for c in [
            "month_label", "email_classification", "folder_category",
            "total_emails", "inbound", "outbound", "internal",
            "unique_customers", "replied", "reply_rate_pct",
            "avg_response_min", "conversations",
        ]
        if c in df.columns
    ]
    if table_cols_available:
        show_df = df[table_cols_available]
        if "month_label" in show_df.columns:
            show_df = show_df.sort_values("month_label", ascending=False)
    else:
        show_df = df

    event = st.dataframe(
        show_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    # --- Detail Panel on row selection ---
    selected_rows = event.selection.get("rows", []) if event and hasattr(event, "selection") else []
    if selected_rows:
        idx = selected_rows[0]
        row_data = show_df.iloc[idx]
        # Reconstruct from original df using position
        full_row = df.iloc[show_df.index[idx]] if hasattr(show_df.index, "__getitem__") else row_data

        fields = {
            "Period": str(row_data.get("month_label", "—")),
            "Classification": str(row_data.get("email_classification", "—")),
            "Folder Category": str(row_data.get("folder_category", "—")),
            "Total Emails": f"{int(row_data.get('total_emails', 0)):,}",
            "Inbound": f"{int(row_data.get('inbound', 0)):,}",
            "Outbound": f"{int(row_data.get('outbound', 0)):,}",
            "Internal": f"{int(row_data.get('internal', 0)):,}",
            "Unique Customers": f"{int(row_data.get('unique_customers', 0)):,}",
            "Replied": f"{int(row_data.get('replied', 0)):,}",
            "Reply Rate": f"{float(row_data.get('reply_rate_pct', 0)):.1f}%",
            "Avg Response (min)": f"{float(row_data.get('avg_response_min', 0)):.0f}",
            "Conversations": f"{int(row_data.get('conversations', 0)):,}",
        }
        # Add optional fields if present
        for extra_col, label in [
            ("median_response_min", "Median Response (min)"),
            ("avg_thread_depth", "Avg Thread Depth"),
            ("avg_turns_when_replied", "Avg Turns (replied)"),
            ("max_thread_depth", "Max Thread Depth"),
            ("with_attachments", "With Attachments"),
        ]:
            if extra_col in row_data.index:
                val = row_data[extra_col]
                fields[label] = str(round(float(val), 1)) if pd.notna(val) else "—"

        st.html(detail_panel_html(
            f"Inbox — {row_data.get('month_label', '')} {row_data.get('email_classification', '')}",
            fields,
        ))
