# apps/sales/tabs/rfp_pipeline.py
"""RFP Pipeline tab — active RFPs, due dates, relevance, and value tracking."""

import streamlit as st
import pandas as pd
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html
from core.charts import stacked_bar_chart, scatter_timeline

RELEVANCE_COLORS = {
    "HIGH": COLORS["error"],
    "MEDIUM": COLORS["warning"],
    "LOW": COLORS["slate"],
}


def render():
    df = query_view("sales_rfp_pipeline")
    if df.empty:
        st.warning("No RFP pipeline data available.")
        return

    # Coerce types
    df["posted_date"] = pd.to_datetime(df["posted_date"], errors="coerce")
    df["due_date"] = pd.to_datetime(df["due_date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

    # 30-day filter for KPIs
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=30)
    recent = df[df["posted_date"] >= cutoff] if df["posted_date"].notna().any() else df

    total_rfps = len(recent)
    high_count = int((recent["relevance"].str.upper() == "HIGH").sum()) if "relevance" in recent.columns else 0
    medium_count = int((recent["relevance"].str.upper() == "MEDIUM").sum()) if "relevance" in recent.columns else 0
    total_value = recent["amount"].sum()

    kpis = [
        {"label": "Total RFPs (30d)", "value": str(total_rfps), "color": COLORS["navy"]},
        {"label": "HIGH Relevance", "value": str(high_count), "color": COLORS["error"],
         "border_color": COLORS["error"] if high_count > 0 else None},
        {"label": "MEDIUM Relevance", "value": str(medium_count), "color": COLORS["warning"],
         "border_color": COLORS["warning"] if medium_count > 0 else None},
        {"label": "Total Value", "value": f"${total_value:,.0f}", "color": COLORS["blue"]},
    ]
    st.html(kpi_strip_html(kpis))

    # --- Relevance filter ---
    all_relevance = sorted(df["relevance"].dropna().unique().tolist()) if "relevance" in df.columns else []
    default_rel = [r for r in ["HIGH", "MEDIUM"] if r in all_relevance] or all_relevance
    selected_rel = st.multiselect("Filter by Relevance", options=all_relevance, default=default_rel)
    filtered = df[df["relevance"].isin(selected_rel)] if selected_rel else df

    # --- Charts ---
    col1, col2 = st.columns(2)

    with col1:
        if "source" in filtered.columns and "relevance" in filtered.columns:
            stacked_df = (
                filtered.groupby(["source", "relevance"], as_index=False)
                .size()
                .rename(columns={"size": "count"})
            )
            if not stacked_df.empty:
                fig = stacked_bar_chart(
                    stacked_df, x="source", y="count", color="relevance",
                    title="RFPs by Source and Relevance",
                    color_map={k: v for k, v in RELEVANCE_COLORS.items()},
                )
                st.plotly_chart(fig, use_container_width=True)

    with col2:
        timeline_df = filtered.dropna(subset=["due_date"])
        if not timeline_df.empty and "source" in timeline_df.columns:
            # Normalize size: 0-size bubbles cause errors, floor at 1
            timeline_df = timeline_df.copy()
            timeline_df["bubble_size"] = timeline_df["amount"].clip(lower=1)
            fig = scatter_timeline(
                timeline_df, x="due_date", y="source",
                size="bubble_size", color="relevance",
                title="RFP Due Date Timeline",
                color_map={k: v for k, v in RELEVANCE_COLORS.items()},
            )
            st.plotly_chart(fig, use_container_width=True)

    # --- Data Table ---
    st.markdown("#### RFP Detail")
    display_cols = [c for c in [
        "relevance", "title", "agency", "state", "source", "record_type",
        "solicitation_id", "posted_date", "due_date", "amount", "status", "recipient",
    ] if c in filtered.columns]
    show_df = filtered[display_cols].sort_values("due_date") if "due_date" in filtered.columns else filtered[display_cols]

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

        fields = {
            "Title": str(row.get("title", "—")),
            "Agency": str(row.get("agency", "—")),
            "State": str(row.get("state", "—")),
            "Source": str(row.get("source", "—")),
            "Record Type": str(row.get("record_type", "—")),
            "Solicitation ID": str(row.get("solicitation_id", "—")),
            "Posted Date": str(row.get("posted_date", "—"))[:10],
            "Due Date": str(row.get("due_date", "—"))[:10],
            "Amount": f"${float(row.get('amount', 0)):,.0f}",
            "Status": str(row.get("status", "—")),
            "Recipient": str(row.get("recipient", "—")),
            "Relevance": str(row.get("relevance", "—")),
            "Procurer Level": str(row.get("procurer_level", "—")),
        }
        url = row.get("source_url", "")
        if url and str(url) not in ("nan", "None", ""):
            fields["Source URL"] = str(url)

        st.html(detail_panel_html(str(row.get("title", "RFP Detail")), fields))
