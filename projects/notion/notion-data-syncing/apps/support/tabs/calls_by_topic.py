# apps/support/tabs/calls_by_topic.py
"""Calls by Topic tab — topic/category breakdown with drill-through to call log."""

import streamlit as st
import pandas as pd
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html
from core.charts import treemap_chart, area_chart


def render():
    df = query_view("calls_by_topic")
    if df.empty:
        st.warning("No calls by topic data available.")
        return

    # Coerce types
    df["call_month"] = pd.to_datetime(df["call_month"], errors="coerce")
    for col in ["total_calls", "answered", "unique_customers"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    if "avg_talk_min" in df.columns:
        df["avg_talk_min"] = pd.to_numeric(df["avg_talk_min"], errors="coerce").fillna(0)

    # --- KPIs ---
    topics_count = int(df["support_topic"].nunique()) if "support_topic" in df.columns else 0
    categories_count = int(df["support_category"].nunique()) if "support_category" in df.columns else 0

    latest_month = df["call_month"].max()
    latest_df = df[df["call_month"] == latest_month]
    latest_calls = int(latest_df["total_calls"].sum())

    top_category = "—"
    if "support_category" in df.columns:
        cat_totals = df.groupby("support_category")["total_calls"].sum()
        if not cat_totals.empty:
            top_category = str(cat_totals.idxmax())

    kpis = [
        {"label": "Topics", "value": str(topics_count), "color": COLORS["navy"]},
        {"label": "Categories", "value": str(categories_count), "color": COLORS["blue"],
         "border_color": COLORS["blue"]},
        {"label": "Top Category", "value": top_category, "color": COLORS["navy"]},
        {"label": "Latest Month Calls", "value": f"{latest_calls:,}", "color": COLORS["slate"],
         "subtitle": latest_month.strftime("%b %Y") if pd.notna(latest_month) else ""},
    ]
    st.html(kpi_strip_html(kpis))

    # --- Charts ---
    col1, col2 = st.columns(2)

    with col1:
        # Treemap: latest month, support_category -> support_topic
        if not latest_df.empty and "support_category" in df.columns and "support_topic" in df.columns:
            treemap_df = latest_df[latest_df["total_calls"] > 0].copy()
            if not treemap_df.empty:
                fig = treemap_chart(
                    treemap_df,
                    path=["support_category", "support_topic"],
                    values="total_calls",
                    title=f"Topic Volume — {latest_month.strftime('%b %Y') if pd.notna(latest_month) else 'Latest Month'}",
                )
                st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Trend lines for top 5 categories
        if "support_category" in df.columns:
            top5_cats = (
                df.groupby("support_category")["total_calls"].sum()
                .nlargest(5).index.tolist()
            )
            cat_trend = (
                df[df["support_category"].isin(top5_cats)]
                .groupby(["call_month", "support_category"], as_index=False)["total_calls"].sum()
            )
            if not cat_trend.empty:
                pivot = cat_trend.pivot_table(
                    index="call_month", columns="support_category",
                    values="total_calls", fill_value=0
                ).reset_index()
                pivot.columns.name = None
                y_cols = [c for c in pivot.columns if c != "call_month"]
                fig = area_chart(pivot, x="call_month", y_cols=y_cols,
                                 title="Top 5 Categories — Monthly Trend", fill=False)
                st.plotly_chart(fig, use_container_width=True)

    # --- Data table with drill-through ---
    st.markdown("#### Topic Detail")
    display_cols = [c for c in [
        "call_month", "support_category", "support_topic",
        "total_calls", "answered", "avg_talk_min", "unique_customers",
    ] if c in df.columns]
    show_df = df[display_cols].sort_values(["call_month", "total_calls"], ascending=[False, False])

    event = st.dataframe(
        show_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    # --- Drill-through: calls_log filtered by topic ---
    selected_rows = event.selection.get("rows", []) if event and hasattr(event, "selection") else []
    if selected_rows:
        idx = selected_rows[0]
        orig_idx = show_df.index[idx]
        row = df.loc[orig_idx]
        selected_topic = str(row.get("support_topic", ""))
        selected_category = str(row.get("support_category", ""))
        selected_month = row.get("call_month")

        month_label = pd.to_datetime(selected_month).strftime("%b %Y") if pd.notna(selected_month) else "All Time"
        st.markdown(f"#### Calls for **{selected_topic}** ({selected_category}) — {month_label}")

        log_df = query_view("calls_log")
        if not log_df.empty and "support_topic" in log_df.columns:
            filtered_log = log_df[log_df["support_topic"] == selected_topic]
            if pd.notna(selected_month):
                if "call_month" in filtered_log.columns:
                    filtered_log = filtered_log[
                        pd.to_datetime(filtered_log["call_month"], errors="coerce") == selected_month
                    ]
                elif "call_date" in filtered_log.columns:
                    filtered_log["_month"] = pd.to_datetime(
                        filtered_log["call_date"], errors="coerce"
                    ).dt.to_period("M")
                    target_period = pd.to_datetime(selected_month).to_period("M")
                    filtered_log = filtered_log[filtered_log["_month"] == target_period].drop(columns="_month")

            log_cols = [c for c in [
                "call_date", "agent_name", "customer_name", "call_status",
                "direction", "source_system", "support_topic", "support_category",
                "talk_minutes", "wait_minutes", "resolution_method",
            ] if c in filtered_log.columns]
            top20 = filtered_log[log_cols].head(20) if log_cols else filtered_log.head(20)
            if not top20.empty:
                st.dataframe(top20, use_container_width=True, hide_index=True)
            else:
                st.info("No calls found for the selected topic/month.")
        else:
            st.info("Calls log not available.")
