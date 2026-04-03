# apps/finance/tabs/pnl.py
"""P&L Reconciliation tab — GL account pass/fail status, delta analysis."""

import streamlit as st
import pandas as pd
from streamlit_echarts import st_echarts
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html
from core.charts import horizontal_bar_chart, donut_chart


def render():
    df = query_view("finance_pnl")
    if df.empty:
        st.warning("No P&L reconciliation data available.")
        return

    # Ensure numeric columns
    df["delta"] = pd.to_numeric(df["delta"], errors="coerce").fillna(0)
    df["hub_total"] = pd.to_numeric(df["hub_total"], errors="coerce").fillna(0)
    df["qb_total"] = pd.to_numeric(df["qb_total"], errors="coerce").fillna(0)
    df["abs_delta"] = df["delta"].abs()

    # Period selector
    periods = sorted(df["period_start"].unique(), reverse=True)
    selected_period = st.selectbox(
        "Period",
        periods,
        format_func=lambda x: pd.Timestamp(x).strftime("%B %Y"),
    )
    period_df = df[df["period_start"] == selected_period].copy()

    # --- KPI Strip ---
    total_accounts = len(period_df)
    failing = int((period_df["status"] == "FAIL").sum())
    passing = int((period_df["status"] == "PASS").sum())
    total_abs_delta = period_df["abs_delta"].sum()

    kpis = [
        {"label": "Total Accounts", "value": str(total_accounts), "color": COLORS["navy"]},
        {"label": "Passing", "value": str(passing), "color": COLORS["success"],
         "border_color": COLORS["success"]},
        {"label": "Failing", "value": str(failing), "color": COLORS["error"],
         "border_color": COLORS["error"] if failing > 0 else None},
        {"label": "Total |Delta|", "value": f"${total_abs_delta:,.0f}", "color": COLORS["warning"]},
    ]
    st.html(kpi_strip_html(kpis))

    # --- Charts Row ---
    col1, col2 = st.columns([2, 1])

    with col1:
        top15 = period_df.nlargest(15, "abs_delta")[["gl_name", "delta"]].copy()
        top15["delta_label"] = top15["gl_name"].str[:35]
        fig = horizontal_bar_chart(
            top15, y="delta_label", x="delta",
            title="Top 15 GL Accounts by |Delta|",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        in_progress = max(0, total_accounts - passing - failing)
        st_echarts(
            donut_chart(
                labels=["Passing", "In Progress", "Failing"],
                values=[passing, in_progress, failing],
                title="Account Status",
                colors=[COLORS["success"], COLORS["warning"], COLORS["error"]],
            ),
            height="280px",
        )

    # --- Filter + Data Table ---
    st.markdown("#### GL Account Detail")
    status_filter = st.radio(
        "Filter by status", ["All", "Failing", "Passing"], horizontal=True
    )

    display_df = period_df.copy()
    if status_filter == "Failing":
        display_df = display_df[display_df["status"] == "FAIL"]
    elif status_filter == "Passing":
        display_df = display_df[display_df["status"] == "PASS"]

    table_cols = ["gl_code", "gl_name", "pl_section", "hub_total", "qb_total", "delta", "status"]
    display_df_show = display_df[table_cols].assign(abs_delta=display_df["abs_delta"]).sort_values("abs_delta", ascending=False).drop(columns="abs_delta")

    event = st.dataframe(
        display_df_show,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    # --- Detail Panel on row selection ---
    selected_rows = event.selection.get("rows", []) if event and hasattr(event, "selection") else []
    if selected_rows:
        idx = selected_rows[0]
        row = display_df_show.iloc[idx]
        full_row = period_df[period_df["gl_code"] == row["gl_code"]].iloc[0]
        fields = {
            "GL Code": str(full_row["gl_code"]),
            "GL Name": str(full_row["gl_name"]),
            "P&L Section": str(full_row["pl_section"]),
            "Source View": str(full_row["source_view"]),
            "Period": pd.Timestamp(selected_period).strftime("%B %Y"),
            "Hub Total": f"${full_row['hub_total']:,.2f}",
            "QB Total": f"${full_row['qb_total']:,.2f}",
            "Delta": f"${full_row['delta']:,.2f}",
            "Status": str(full_row["status"]),
            "Note": str(full_row.get("note", "—")),
        }
        st.html(detail_panel_html(f"{full_row['gl_name']} — Detail", fields))
