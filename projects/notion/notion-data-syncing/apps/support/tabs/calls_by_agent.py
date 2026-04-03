# apps/support/tabs/calls_by_agent.py
"""Calls by Agent tab — agent performance with radar, leaderboard, and drill-through."""

import streamlit as st
import pandas as pd
from streamlit_echarts import st_echarts
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html
from core.charts import radar_chart, horizontal_bar_chart


def render():
    df = query_view("calls_by_agent")
    if df.empty:
        st.warning("No calls by agent data available.")
        return

    # Coerce types
    df["call_month"] = pd.to_datetime(df["call_month"], errors="coerce")
    for col in ["total_calls", "answered"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    for col in ["answer_rate", "total_talk_min", "avg_talk_min", "avg_wait_min"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Aggregate across all months per agent for leaderboard
    agg_cols = {c: "sum" for c in ["total_calls", "answered", "total_talk_min"] if c in df.columns}
    agg_cols.update({c: "mean" for c in ["answer_rate", "avg_talk_min", "avg_wait_min"] if c in df.columns})
    agent_df = df.groupby("agent_name", as_index=False).agg(agg_cols)

    # --- KPIs ---
    agents_count = int(agent_df["agent_name"].nunique())

    top_volume_agent = "—"
    if "total_calls" in agent_df.columns and not agent_df.empty:
        top_volume_agent = str(agent_df.loc[agent_df["total_calls"].idxmax(), "agent_name"])

    best_answer_agent = "—"
    if "answer_rate" in agent_df.columns and not agent_df.empty:
        min_calls = agent_df["total_calls"].quantile(0.25) if "total_calls" in agent_df.columns else 0
        qualified = agent_df[agent_df.get("total_calls", pd.Series([0])) >= min_calls]
        if not qualified.empty:
            best_answer_agent = str(qualified.loc[qualified["answer_rate"].idxmax(), "agent_name"])

    kpis = [
        {"label": "Agents", "value": str(agents_count), "color": COLORS["navy"]},
        {"label": "Top Volume", "value": top_volume_agent, "color": COLORS["blue"],
         "border_color": COLORS["blue"]},
        {"label": "Best Answer Rate", "value": best_answer_agent, "color": COLORS["success"],
         "border_color": COLORS["success"]},
    ]
    st.html(kpi_strip_html(kpis))

    # --- Charts ---
    col1, col2 = st.columns(2)

    with col1:
        # Radar chart for top 5 agents by volume
        top5 = agent_df.nlargest(5, "total_calls") if "total_calls" in agent_df.columns else agent_df.head(5)

        if not top5.empty:
            max_calls = float(top5["total_calls"].max()) if "total_calls" in top5.columns else 1
            max_answer_rate = 100.0
            max_talk = float(top5["avg_talk_min"].max()) if "avg_talk_min" in top5.columns else 1

            indicators = [
                {"name": "Total Calls", "max": max(max_calls, 1)},
                {"name": "Answer Rate %", "max": max_answer_rate},
                {"name": "Avg Talk Min", "max": max(max_talk, 1)},
            ]

            series_data = []
            for _, row in top5.iterrows():
                series_data.append({
                    "name": str(row["agent_name"]),
                    "value": [
                        float(row.get("total_calls", 0)),
                        float(row.get("answer_rate", 0)),
                        float(row.get("avg_talk_min", 0)),
                    ],
                })

            radar_config = radar_chart(indicators, series_data, "Top 5 Agents — Performance Radar")
            st_echarts(radar_config, height="320px")

    with col2:
        # Horizontal leaderboard bar chart
        if "total_calls" in agent_df.columns and not agent_df.empty:
            leaderboard = agent_df.nlargest(15, "total_calls")[["agent_name", "total_calls"]]
            fig = horizontal_bar_chart(
                leaderboard, y="agent_name", x="total_calls",
                title="Agent Call Volume Leaderboard"
            )
            st.plotly_chart(fig, use_container_width=True)

    # --- Data table with single-row selection ---
    st.markdown("#### Agent Detail")
    display_cols = [c for c in [
        "agent_name", "total_calls", "answered", "answer_rate",
        "total_talk_min", "avg_talk_min", "avg_wait_min",
    ] if c in agent_df.columns]
    show_df = agent_df[display_cols].sort_values("total_calls", ascending=False)

    event = st.dataframe(
        show_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    # --- Drill-through: calls_log filtered by agent ---
    selected_rows = event.selection.get("rows", []) if event and hasattr(event, "selection") else []
    if selected_rows:
        idx = selected_rows[0]
        orig_idx = show_df.index[idx]
        row = agent_df.loc[orig_idx]
        selected_agent = str(row.get("agent_name", ""))

        st.markdown(f"#### Recent Calls — **{selected_agent}**")

        log_df = query_view("calls_log")
        if not log_df.empty and "agent_name" in log_df.columns:
            agent_log = log_df[log_df["agent_name"] == selected_agent]
            log_cols = [c for c in [
                "call_date", "customer_name", "call_status", "direction",
                "source_system", "department", "support_topic", "support_category",
                "talk_minutes", "wait_minutes", "accounting_bucket", "resolution_method",
            ] if c in agent_log.columns]
            top20 = agent_log[log_cols].head(20) if log_cols else agent_log.head(20)
            if not top20.empty:
                st.dataframe(top20, use_container_width=True, hide_index=True)
            else:
                st.info("No calls found for the selected agent.")
        else:
            st.info("Calls log not available.")
