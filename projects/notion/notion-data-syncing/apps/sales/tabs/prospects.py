# apps/sales/tabs/prospects.py
"""Prospects tab — scored prospect list with treemap, histogram, and full detail panel."""

import streamlit as st
import pandas as pd
import plotly.express as px
from core.db import query_view
from core.theme import COLORS, COLOR_SEQUENCE
from core.components import kpi_strip_html, detail_panel_html
from core.charts import treemap_chart


def render():
    df = query_view("sales_prospects")
    if df.empty:
        st.warning("No prospects data available.")
        return

    # Coerce numeric columns
    for col in [
        "ori_count", "fee_per_scan", "employee_count", "est_annual_volume",
        "est_annual_revenue", "volume_score", "accessibility_score", "priority_score",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    for bool_col in ["is_b4all_customer", "active_billing"]:
        if bool_col in df.columns:
            df[bool_col] = df[bool_col].astype(str).str.lower().isin(["true", "1", "yes", "t"])

    # --- KPIs ---
    total = len(df)
    tier1a = int((df["priority_tier"].str.upper() == "1A").sum()) if "priority_tier" in df.columns else 0
    states_covered = int(df["state_abbr"].nunique()) if "state_abbr" in df.columns else 0
    est_revenue = df["est_annual_revenue"].sum() if "est_annual_revenue" in df.columns else 0

    kpis = [
        {"label": "Total Prospects", "value": f"{total:,}", "color": COLORS["navy"]},
        {"label": "Tier 1A", "value": str(tier1a), "color": COLORS["error"],
         "border_color": COLORS["error"] if tier1a > 0 else None},
        {"label": "States Covered", "value": str(states_covered), "color": COLORS["blue"]},
        {"label": "Est Annual Revenue", "value": f"${est_revenue:,.0f}", "color": COLORS["success"],
         "border_color": COLORS["success"]},
    ]
    st.html(kpi_strip_html(kpis))

    # --- Filters ---
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        all_tiers = sorted(df["priority_tier"].dropna().unique().tolist()) if "priority_tier" in df.columns else []
        selected_tiers = st.multiselect("Filter by Priority Tier", options=all_tiers, default=all_tiers)
    with col_f2:
        all_states = sorted(df["state_abbr"].dropna().unique().tolist()) if "state_abbr" in df.columns else []
        selected_states = st.multiselect("Filter by State", options=all_states, default=all_states)

    filtered = df.copy()
    if selected_tiers and "priority_tier" in filtered.columns:
        filtered = filtered[filtered["priority_tier"].isin(selected_tiers)]
    if selected_states and "state_abbr" in filtered.columns:
        filtered = filtered[filtered["state_abbr"].isin(selected_states)]

    # --- Charts ---
    col1, col2 = st.columns(2)

    with col1:
        tree_df = filtered.copy()
        # treemap needs positive values; use count of prospects per state+tier
        if "state_abbr" in tree_df.columns and "priority_tier" in tree_df.columns:
            tree_agg = (
                tree_df.groupby(["state_abbr", "priority_tier"], as_index=False)
                .size()
                .rename(columns={"size": "count"})
            )
            if not tree_agg.empty:
                fig = treemap_chart(
                    tree_agg, path=["state_abbr", "priority_tier"],
                    values="count", title="Prospects by State and Priority Tier",
                    color="priority_tier",
                )
                st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "priority_score" in filtered.columns and filtered["priority_score"].notna().any():
            fig = px.histogram(
                filtered, x="priority_score", nbins=20,
                title="Priority Score Distribution",
                color_discrete_sequence=[COLORS["blue"]],
            )
            fig.update_layout(
                paper_bgcolor=COLORS["bg"],
                plot_bgcolor=COLORS["white"],
                font=dict(family="Inter, system-ui, sans-serif", color=COLORS["navy"], size=12),
                margin=dict(l=40, r=20, t=40, b=40),
                xaxis=dict(gridcolor=COLORS["border"], linecolor=COLORS["border"]),
                yaxis=dict(gridcolor=COLORS["border"], linecolor=COLORS["border"]),
            )
            st.plotly_chart(fig, use_container_width=True)

    # --- Data Table ---
    st.markdown("#### Prospect Detail")
    display_cols = [c for c in [
        "priority_tier", "priority_score", "entity_name", "state_abbr", "county",
        "city", "effective_vertical", "vertical_cluster", "demand_type",
        "est_annual_revenue", "est_annual_volume", "size_category",
        "is_b4all_customer", "active_billing",
    ] if c in filtered.columns]
    show_df = filtered[display_cols].sort_values("priority_score", ascending=False) if "priority_score" in filtered.columns else filtered[display_cols]

    event = st.dataframe(
        show_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    # --- Detail Panel (all 25 fields) ---
    selected_rows = event.selection.get("rows", []) if event and hasattr(event, "selection") else []
    if selected_rows:
        idx = selected_rows[0]
        orig_idx = show_df.index[idx]
        row = filtered.loc[orig_idx]

        fields = {
            "Entity Name": str(row.get("entity_name", "—")),
            "ORI Code": str(row.get("ori_code", "—")),
            "Effective Vertical": str(row.get("effective_vertical", "—")),
            "Vertical Cluster": str(row.get("vertical_cluster", "—")),
            "State": str(row.get("state_abbr", "—")),
            "County": str(row.get("county", "—")),
            "City": str(row.get("city", "—")),
            "ZIP": str(row.get("zip", "—")),
            "B4ALL Customer": str(row.get("is_b4all_customer", "—")),
            "Active Billing": str(row.get("active_billing", "—")),
            "Client ID": str(row.get("client_id", "—")),
            "Contact Name": str(row.get("contact_name", "—")),
            "Contact Domain": str(row.get("contact_domain", "—")),
            "Demand Type": str(row.get("demand_type", "—")),
            "ORI Count": str(int(row.get("ori_count", 0))),
            "Fee Per Scan": f"${float(row.get('fee_per_scan', 0)):.2f}",
            "Employee Count": str(int(row.get("employee_count", 0))),
            "Size Category": str(row.get("size_category", "—")),
            "Est Annual Volume": f"{float(row.get('est_annual_volume', 0)):,.0f}",
            "Est Annual Revenue": f"${float(row.get('est_annual_revenue', 0)):,.0f}",
            "Volume Score": str(int(row.get("volume_score", 0))),
            "Accessibility Score": str(int(row.get("accessibility_score", 0))),
            "Priority Score": str(int(row.get("priority_score", 0))),
            "Priority Tier": str(row.get("priority_tier", "—")),
            "Score Reason": str(row.get("score_reason", "—")),
        }
        st.html(detail_panel_html(str(row.get("entity_name", "Prospect Detail")), fields))
