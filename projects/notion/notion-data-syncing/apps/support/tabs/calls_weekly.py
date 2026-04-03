# apps/support/tabs/calls_weekly.py
"""Calls Weekly tab — weekly call volume trends by source and department."""

import streamlit as st
import pandas as pd
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html
from core.charts import area_chart, stacked_bar_chart


def render():
    df = query_view("calls_weekly")
    if df.empty:
        st.warning("No calls weekly data available.")
        return

    # Coerce types
    df["call_week"] = pd.to_datetime(df["call_week"], errors="coerce")
    for col in ["total_calls", "answered", "abandoned", "voicemail", "missed"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    for col in ["answer_rate", "avg_talk_min", "avg_wait_min"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # --- KPIs from latest week ---
    latest_week = df["call_week"].max()
    latest = df[df["call_week"] == latest_week]

    week_label = latest_week.strftime("%b %d, %Y") if pd.notna(latest_week) else "—"
    total_calls = int(latest["total_calls"].sum())
    answered = int(latest["answered"].sum())
    answer_rate = (answered / total_calls * 100) if total_calls > 0 else 0

    kpis = [
        {"label": "Latest Week", "value": week_label, "color": COLORS["slate"]},
        {"label": "Total Calls", "value": f"{total_calls:,}", "color": COLORS["navy"]},
        {"label": "Answered", "value": f"{answered:,}", "color": COLORS["success"],
         "border_color": COLORS["success"]},
        {"label": "Answer Rate", "value": f"{answer_rate:.1f}%",
         "color": COLORS["success"] if answer_rate >= 80 else COLORS["warning"],
         "border_color": COLORS["success"] if answer_rate >= 80 else COLORS["warning"]},
    ]
    st.html(kpi_strip_html(kpis))

    # --- Stacked area by source_system over time ---
    col1, col2 = st.columns(2)

    with col1:
        if "source_system" in df.columns:
            source_weekly = (
                df.groupby(["call_week", "source_system"], as_index=False)["total_calls"].sum()
            )
            sources = sorted(source_weekly["source_system"].dropna().unique().tolist())
            if sources:
                pivot = source_weekly.pivot_table(
                    index="call_week", columns="source_system", values="total_calls", fill_value=0
                ).reset_index()
                pivot.columns.name = None
                y_cols = [c for c in pivot.columns if c != "call_week"]
                fig = area_chart(pivot, x="call_week", y_cols=y_cols,
                                 title="Weekly Calls by Source System", fill=True)
                st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "department" in df.columns:
            dept_weekly = (
                df.groupby(["call_week", "department"], as_index=False)["total_calls"].sum()
            )
            if not dept_weekly.empty:
                fig = stacked_bar_chart(
                    dept_weekly, x="call_week", y="total_calls",
                    color="department", title="Weekly Calls by Department"
                )
                st.plotly_chart(fig, use_container_width=True)

    # --- Data table ---
    st.markdown("#### Weekly Call Detail")
    display_cols = [c for c in [
        "call_week", "department", "source_system", "total_calls",
        "answered", "abandoned", "voicemail", "missed",
        "answer_rate", "avg_talk_min", "avg_wait_min",
    ] if c in df.columns]
    show_df = df[display_cols].sort_values("call_week", ascending=False)

    st.dataframe(show_df, use_container_width=True, hide_index=True)
