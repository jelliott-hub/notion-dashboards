# apps/sales/tabs/state_profiles.py
"""State Profiles tab — channeler model map, fee comparison, state market intelligence."""

import streamlit as st
import pandas as pd
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html
from core.charts import choropleth_map, horizontal_bar_chart

CHANNELER_COLORS = {
    "open": COLORS["success"],
    "closed": COLORS["error"],
    "hybrid": COLORS["warning"],
    "limited": COLORS["slate"],
}


def render():
    df = query_view("sales_state_profiles")
    if df.empty:
        st.warning("No state profiles data available.")
        return

    # Coerce types
    for col in [
        "state_processing_fee", "fbi_processing_fee", "typical_rolling_fee",
        "est_total_applicant_cost", "state_processing_fee", "composite_score",
        "demand_score", "openness_score", "volume_score",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    for int_col in [
        "b4all_location_count", "identogo_location_count", "certifix_location_count",
        "total_operator_count", "civil_fingerprint_volume", "livescan_volume",
    ]:
        if int_col in df.columns:
            df[int_col] = pd.to_numeric(df[int_col], errors="coerce").fillna(0).astype(int)

    for bool_col in ["b4all_has_contract"]:
        if bool_col in df.columns:
            df[bool_col] = df[bool_col].astype(str).str.lower().isin(["true", "1", "yes", "t"])

    # --- KPIs ---
    total_states = len(df)
    open_market = int(
        (df["channeler_model"].str.lower() == "open").sum()
    ) if "channeler_model" in df.columns else 0
    b4all_states = int(df["b4all_has_contract"].sum()) if "b4all_has_contract" in df.columns else 0
    avg_composite = df["composite_score"].mean() if "composite_score" in df.columns else 0

    kpis = [
        {"label": "States", "value": str(total_states), "color": COLORS["navy"]},
        {"label": "Open Market", "value": str(open_market), "color": COLORS["success"],
         "border_color": COLORS["success"]},
        {"label": "B4ALL States", "value": str(b4all_states), "color": COLORS["blue"],
         "border_color": COLORS["blue"]},
        {"label": "Avg Composite Score", "value": f"{avg_composite:.1f}", "color": COLORS["navy"]},
    ]
    st.html(kpi_strip_html(kpis))

    # --- Charts ---
    col1, col2 = st.columns(2)

    with col1:
        if "state_abbr" in df.columns and "channeler_model" in df.columns:
            map_df = df.dropna(subset=["state_abbr", "channeler_model"])
            if not map_df.empty:
                fig = choropleth_map(
                    map_df, locations="state_abbr", color="channeler_model",
                    title="State Channeler Model",
                    color_map={k: v for k, v in CHANNELER_COLORS.items()},
                )
                st.plotly_chart(fig, use_container_width=True)

    with col2:
        fee_col = "est_total_applicant_cost" if "est_total_applicant_cost" in df.columns else "typical_rolling_fee"
        if "state_abbr" in df.columns and fee_col in df.columns:
            fee_df = df[["state_abbr", fee_col]].dropna()
            fee_df = fee_df[fee_df[fee_col] > 0]
            if not fee_df.empty:
                fig = horizontal_bar_chart(
                    fee_df, y="state_abbr", x=fee_col,
                    title=f"Fee by State ({fee_col.replace('_', ' ').title()})",
                )
                st.plotly_chart(fig, use_container_width=True)

    # --- Data Table ---
    st.markdown("#### State Profile Detail")
    display_cols = [c for c in [
        "state_abbr", "channeler_model", "b4all_has_contract", "composite_score",
        "openness_score", "demand_score", "volume_score",
        "incumbent_vendor", "contract_expiry_date",
        "b4all_location_count", "total_operator_count",
    ] if c in df.columns]
    show_df = df[display_cols].sort_values("composite_score", ascending=False) if "composite_score" in df.columns else df[display_cols]

    event = st.dataframe(
        show_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
    )

    # --- Detail Panel (all 21 fields) ---
    selected_rows = event.selection.get("rows", []) if event and hasattr(event, "selection") else []
    if selected_rows:
        idx = selected_rows[0]
        orig_idx = show_df.index[idx]
        row = df.loc[orig_idx]

        fields = {
            "State": str(row.get("state_abbr", "—")),
            "State Agency": str(row.get("state_agency_name", "—")),
            "Channeler Model": str(row.get("channeler_model", "—")),
            "Incumbent Vendor": str(row.get("incumbent_vendor", "—")),
            "Contract Expiry": str(row.get("contract_expiry_date", "—"))[:10],
            "State Processing Fee": f"${float(row.get('state_processing_fee', 0)):.2f}",
            "FBI Processing Fee": f"${float(row.get('fbi_processing_fee', 0)):.2f}",
            "Typical Rolling Fee": f"${float(row.get('typical_rolling_fee', 0)):.2f}",
            "Est Total Applicant Cost": f"${float(row.get('est_total_applicant_cost', 0)):.2f}",
            "Civil Fingerprint Volume": f"{int(row.get('civil_fingerprint_volume', 0)):,}",
            "Livescan Volume": f"{int(row.get('livescan_volume', 0)):,}",
            "B4ALL Location Count": str(int(row.get("b4all_location_count", 0))),
            "B4ALL Has Contract": str(row.get("b4all_has_contract", "—")),
            "Identogo Locations": str(int(row.get("identogo_location_count", 0))),
            "Certifix Locations": str(int(row.get("certifix_location_count", 0))),
            "Total Operators": str(int(row.get("total_operator_count", 0))),
            "Demand Score": str(int(row.get("demand_score", 0))),
            "Openness Score": str(int(row.get("openness_score", 0))),
            "Volume Score": str(int(row.get("volume_score", 0))),
            "Composite Score": f"{float(row.get('composite_score', 0)):.1f}",
            "Notes": str(row.get("notes", "—")),
        }
        st.html(detail_panel_html(f"State: {row.get('state_abbr', 'Detail')}", fields))
