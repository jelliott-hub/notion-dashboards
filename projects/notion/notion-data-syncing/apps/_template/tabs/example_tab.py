# apps/<dashboard_name>/tabs/<tab_name>.py
"""
<Tab Name> tab — <one-line description>.

Copy this file to apps/<your_dashboard>/tabs/<tab_name>.py and customize:
1. Change the view name in query_view()
2. Build KPIs from your data columns
3. Pick chart types from core.charts that fit your data
4. Set table_cols to the columns you want in the data table
5. Build the detail panel fields from the full row

Standard tab pattern:
    query → KPIs → charts in columns → data table → detail panel on row select
"""

import streamlit as st
import pandas as pd
from streamlit_echarts import st_echarts
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html
from core.charts import area_chart, horizontal_bar_chart, donut_chart, gauge_chart


def render():
    # --- 1. Load data ---
    df = query_view("your_view_name")  # schema defaults to "notion_sync"
    # df = query_view("mv_call_spine", schema="analytics")  # or any schema
    if df.empty:
        st.warning("No data available.")
        return

    # query_view auto-coerces types. Only add manual coercion if you need
    # specific handling like .fillna(0) or .astype(int) for display purposes.

    # --- 2. KPI strip ---
    kpis = [
        {"label": "Metric One", "value": f"{len(df):,}", "color": COLORS["navy"]},
        {"label": "Metric Two", "value": "—", "color": COLORS["success"],
         "border_color": COLORS["success"]},
        # Add more KPIs as needed. See core/components.py for all options.
    ]
    st.html(kpi_strip_html(kpis))

    # --- 3. Charts in columns ---
    col1, col2 = st.columns(2)

    with col1:
        # Pick any chart from core.charts — see docstrings for data shape
        # fig = area_chart(df, x="date_col", y_cols=["value_col"],
        #                  title="Trend Over Time")
        # st.plotly_chart(fig, use_container_width=True)
        st.info("Chart 1 — replace with your chart")

    with col2:
        # ECharts example:
        # st_echarts(gauge_chart(75.0, "Completion"), height="250px")
        # st_echarts(donut_chart(["A", "B"], [60, 40], "Breakdown"), height="250px")
        st.info("Chart 2 — replace with your chart")

    # --- 4. Data table with row selection ---
    st.markdown("#### Detail")
    table_cols = [c for c in df.columns[:8]]  # pick the columns you want
    show_df = df[table_cols]

    event = st.dataframe(
        show_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    # --- 5. Detail panel on row selection ---
    selected_rows = event.selection.get("rows", []) if event and hasattr(event, "selection") else []
    if selected_rows:
        idx = selected_rows[0]
        orig_idx = show_df.index[idx]
        row = df.loc[orig_idx]

        fields = {
            "Field One": str(row.get("col_a", "—")),
            "Field Two": str(row.get("col_b", "—")),
            # Add all relevant fields from the row
        }
        st.html(detail_panel_html("Row Detail", fields))
