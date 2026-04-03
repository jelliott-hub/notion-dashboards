# apps/finance/tabs/variance.py
"""Variance Analysis tab — MoM/YoY changes, flagged accounts, heatmap."""

import streamlit as st
import pandas as pd
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html
from core.charts import heatmap_chart, horizontal_bar_chart


def render():
    df = query_view("finance_variance")
    if df.empty:
        st.warning("No variance data available.")
        return

    # Ensure numeric columns
    for col in ["mom_pct_change", "yoy_pct_change", "mom_change", "yoy_change",
                "current_month_actual", "prior_month_actual", "ytd_actual",
                "prior_ytd_actual", "prior_year_month_actual", "avg_6mo"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["report_month"] = pd.to_datetime(df["report_month"])
    df["month_label"] = df["report_month"].dt.strftime("%b %Y")

    # --- KPI Strip ---
    flagged = df[df["variance_flag"].notna() & (df["variance_flag"] != "")]
    flagged_count = len(flagged["gl_code"].unique())

    # Largest single MoM swing
    if not df.empty:
        max_mom_idx = df["mom_pct_change"].abs().idxmax()
        largest_mom = df.loc[max_mom_idx, "mom_pct_change"]
        largest_mom_name = df.loc[max_mom_idx, "gl_name"]
    else:
        largest_mom, largest_mom_name = 0.0, "—"

    if not df.empty:
        max_yoy_idx = df["yoy_pct_change"].abs().idxmax()
        largest_yoy = df.loc[max_yoy_idx, "yoy_pct_change"]
        largest_yoy_name = df.loc[max_yoy_idx, "gl_name"]
    else:
        largest_yoy, largest_yoy_name = 0.0, "—"

    kpis = [
        {"label": "Flagged Accounts", "value": str(flagged_count), "color": COLORS["warning"],
         "border_color": COLORS["warning"] if flagged_count > 0 else None},
        {"label": "Largest MoM Swing", "value": f"{largest_mom:+.1f}%",
         "subtitle": largest_mom_name[:30],
         "color": COLORS["error"] if abs(largest_mom) > 20 else COLORS["warning"]},
        {"label": "Largest YoY Swing", "value": f"{largest_yoy:+.1f}%",
         "subtitle": largest_yoy_name[:30],
         "color": COLORS["error"] if abs(largest_yoy) > 30 else COLORS["warning"]},
    ]
    st.html(kpi_strip_html(kpis))

    # --- P&L Section filter ---
    all_sections = sorted(df["pl_section"].dropna().unique().tolist())
    selected_sections = st.multiselect(
        "Filter by P&L Section", all_sections, default=all_sections
    )
    filtered_df = df[df["pl_section"].isin(selected_sections)].copy() if selected_sections else df.copy()

    # --- Charts Row ---
    col1, col2 = st.columns([3, 2])

    with col1:
        # Heatmap: MoM % by GL account × month
        hm_df = filtered_df[["gl_name", "month_label", "mom_pct_change"]].copy()
        if not hm_df.empty and hm_df["gl_name"].nunique() > 0:
            # Limit to top 20 accounts by max abs swing for readability
            top_accts = (
                hm_df.groupby("gl_name")["mom_pct_change"]
                .apply(lambda s: s.abs().max())
                .nlargest(20)
                .index
            )
            hm_df = hm_df[hm_df["gl_name"].isin(top_accts)]
            fig = heatmap_chart(
                hm_df, x="month_label", y="gl_name",
                z="mom_pct_change", title="MoM % Change by GL × Month",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Not enough data for heatmap.")

    with col2:
        # Flagged accounts bar
        flagged_df = filtered_df[
            filtered_df["variance_flag"].notna() & (filtered_df["variance_flag"] != "")
        ].copy()
        if not flagged_df.empty:
            flagged_summary = (
                flagged_df.groupby("gl_name")["mom_pct_change"]
                .apply(lambda s: s.abs().max())
                .reset_index()
                .rename(columns={"mom_pct_change": "max_abs_swing"})
                .nlargest(15, "max_abs_swing")
            )
            fig2 = horizontal_bar_chart(
                flagged_summary, y="gl_name", x="max_abs_swing",
                title="Flagged Accounts — Max |MoM %|",
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.success("No flagged accounts in selected sections.")

    # --- Data Table ---
    st.markdown("#### Variance Detail")
    table_cols = ["gl_code", "gl_name", "pl_section", "month_label",
                  "current_month_actual", "prior_month_actual", "mom_pct_change",
                  "yoy_pct_change", "variance_flag"]
    show_df = filtered_df[table_cols].sort_values("mom_pct_change", key=abs, ascending=False)

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
        row = show_df.iloc[idx]
        # Match on gl_code + month_label
        mask = (
            (filtered_df["gl_code"] == row["gl_code"]) &
            (filtered_df["month_label"] == row["month_label"])
        )
        matches = filtered_df[mask]
        if not matches.empty:
            full_row = matches.iloc[0]
            fields = {
                "GL Code": str(full_row["gl_code"]),
                "GL Name": str(full_row["gl_name"]),
                "P&L Section": str(full_row["pl_section"]),
                "Period": str(full_row["month_label"]),
                "Current Month": f"${full_row['current_month_actual']:,.2f}",
                "Prior Month": f"${full_row['prior_month_actual']:,.2f}",
                "MoM Change": f"${full_row['mom_change']:,.2f}",
                "MoM %": f"{full_row['mom_pct_change']:+.1f}%",
                "YTD Actual": f"${full_row['ytd_actual']:,.2f}",
                "Prior YTD": f"${full_row['prior_ytd_actual']:,.2f}",
                "YoY Change": f"${full_row['yoy_change']:,.2f}",
                "YoY %": f"{full_row['yoy_pct_change']:+.1f}%",
                "6-Mo Avg": f"${full_row['avg_6mo']:,.2f}",
                "Variance Flag": str(full_row.get("variance_flag", "—")),
            }
            st.html(detail_panel_html(f"{full_row['gl_name']} — {full_row['month_label']}", fields))
