# apps/sales/tabs/opportunities.py
"""Opportunities tab — gov bids, recompetes, federal RFPs by urgency and source."""

import streamlit as st
import pandas as pd
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html
from core.charts import heatmap_chart, stacked_bar_chart


def render():
    df = query_view("sales_opportunities")
    if df.empty:
        st.warning("No opportunities data available.")
        return

    # Coerce types
    df["date_posted"] = pd.to_datetime(df["date_posted"], errors="coerce")
    df["deadline"] = pd.to_datetime(df["deadline"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    # --- KPIs ---
    total = len(df)
    gov_bids = int((df["source_type"].str.lower().str.contains("gov", na=False)).sum()) if "source_type" in df.columns else 0
    recompetes = int((df["title"].str.lower().str.contains("recompete", na=False)).sum()) if "title" in df.columns else 0
    federal = int((df["source_type"].str.lower().str.contains("federal", na=False)).sum()) if "source_type" in df.columns else 0

    kpis = [
        {"label": "Total Opportunities", "value": str(total), "color": COLORS["navy"]},
        {"label": "Gov Bids", "value": str(gov_bids), "color": COLORS["blue"],
         "border_color": COLORS["blue"]},
        {"label": "Recompetes", "value": str(recompetes), "color": COLORS["warning"],
         "border_color": COLORS["warning"] if recompetes > 0 else None},
        {"label": "Federal", "value": str(federal), "color": COLORS["error"],
         "border_color": COLORS["error"] if federal > 0 else None},
    ]
    st.html(kpi_strip_html(kpis))

    # --- Source type filter ---
    all_sources = sorted(df["source_type"].dropna().unique().tolist()) if "source_type" in df.columns else []
    selected_sources = st.multiselect("Filter by Source Type", options=all_sources, default=all_sources)
    filtered = df[df["source_type"].isin(selected_sources)] if selected_sources else df

    # --- Charts ---
    col1, col2 = st.columns(2)

    with col1:
        if "source_type" in filtered.columns and "urgency_tier" in filtered.columns:
            heatmap_df = (
                filtered.groupby(["source_type", "urgency_tier"], as_index=False)
                .size()
                .rename(columns={"size": "count"})
            )
            if not heatmap_df.empty:
                fig = heatmap_chart(
                    heatmap_df, x="source_type", y="urgency_tier", z="count",
                    title="Opportunities: Source vs Urgency Tier",
                )
                st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "source_type" in filtered.columns and "urgency_tier" in filtered.columns:
            stack_df = (
                filtered.groupby(["source_type", "urgency_tier"], as_index=False)
                .size()
                .rename(columns={"size": "count"})
            )
            if not stack_df.empty:
                fig = stacked_bar_chart(
                    stack_df, x="source_type", y="count", color="urgency_tier",
                    title="Opportunities by Source Type",
                )
                st.plotly_chart(fig, use_container_width=True)

    # --- Data Table ---
    st.markdown("#### Opportunity Detail")
    display_cols = [c for c in [
        "relevance", "urgency_tier", "title", "agency", "state", "source_type",
        "date_posted", "deadline", "amount",
    ] if c in filtered.columns]
    show_df = filtered[display_cols].sort_values("deadline") if "deadline" in filtered.columns else filtered[display_cols]

    event = st.dataframe(
        show_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    # --- Detail Panel ---
    selected_rows = event.selection.get("rows", []) if event and hasattr(event, "selection") else []
    if selected_rows:
        idx = selected_rows[0]
        orig_idx = show_df.index[idx]
        row = filtered.loc[orig_idx]

        desc = str(row.get("description", "—"))
        if len(desc) > 200:
            desc = desc[:200] + "..."

        fields = {
            "Title": str(row.get("title", "—")),
            "Agency": str(row.get("agency", "—")),
            "State": str(row.get("state", "—")),
            "Source Type": str(row.get("source_type", "—")),
            "Relevance": str(row.get("relevance", "—")),
            "Urgency Tier": str(row.get("urgency_tier", "—")),
            "Date Posted": str(row.get("date_posted", "—"))[:10],
            "Deadline": str(row.get("deadline", "—"))[:10],
            "Amount": f"${float(row.get('amount', 0)):,.0f}",
            "Description": desc,
        }
        url = row.get("source_url", "")
        if url and str(url) not in ("nan", "None", ""):
            fields["Source URL"] = str(url)

        st.html(detail_panel_html(str(row.get("title", "Opportunity Detail")), fields))
