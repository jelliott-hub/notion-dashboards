# apps/sales/tabs/deals.py
"""Deals tab — HubSpot deal pipeline, stage funnel, and deal details."""

import streamlit as st
import pandas as pd
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html
from core.charts import funnel_chart, horizontal_bar_chart


def render():
    df = query_view("sales_deals")
    if df.empty:
        st.warning("No deals data available.")
        return

    # Coerce types
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["close_date"] = pd.to_datetime(df["close_date"], errors="coerce")
    df["days_in_pipeline"] = pd.to_numeric(df["days_in_pipeline"], errors="coerce").fillna(0)
    for bool_col in ["is_closed_won", "is_closed_lost"]:
        if bool_col in df.columns:
            df[bool_col] = df[bool_col].astype(str).str.lower().isin(["true", "1", "yes", "t"])

    # --- KPIs ---
    total = len(df)
    open_deals = int((~df["is_closed_won"] & ~df["is_closed_lost"]).sum()) if all(
        c in df.columns for c in ["is_closed_won", "is_closed_lost"]) else total
    won = int(df["is_closed_won"].sum()) if "is_closed_won" in df.columns else 0
    pipeline_value = df[~df["is_closed_won"] & ~df["is_closed_lost"]]["amount"].sum() if all(
        c in df.columns for c in ["is_closed_won", "is_closed_lost"]) else df["amount"].sum()

    kpis = [
        {"label": "Total Deals", "value": str(total), "color": COLORS["navy"]},
        {"label": "Open", "value": str(open_deals), "color": COLORS["blue"],
         "border_color": COLORS["blue"]},
        {"label": "Won", "value": str(won), "color": COLORS["success"],
         "border_color": COLORS["success"]},
        {"label": "Pipeline Value", "value": f"${pipeline_value:,.0f}", "color": COLORS["navy"]},
    ]
    st.html(kpi_strip_html(kpis))

    # --- Pipeline filter ---
    all_pipelines = sorted(df["pipeline"].dropna().unique().tolist()) if "pipeline" in df.columns else []
    selected_pipelines = st.multiselect("Filter by Pipeline", options=all_pipelines, default=all_pipelines)
    filtered = df[df["pipeline"].isin(selected_pipelines)] if selected_pipelines else df

    # --- Charts ---
    col1, col2 = st.columns(2)

    with col1:
        if "deal_stage" in filtered.columns:
            stage_order = [
                "Prospecting", "Qualification", "Proposal", "Negotiation",
                "Closed Won", "Closed Lost",
            ]
            stage_df = (
                filtered.groupby("deal_stage", as_index=False)["amount"]
                .sum()
                .rename(columns={"amount": "total_amount"})
            )
            # Sort by stage order if possible, otherwise by amount desc
            stage_df["_order"] = stage_df["deal_stage"].apply(
                lambda s: stage_order.index(s) if s in stage_order else 999
            )
            stage_df = stage_df.sort_values("_order").drop(columns="_order")
            if not stage_df.empty:
                fig = funnel_chart(stage_df, stage="deal_stage", value="total_amount",
                                   title="Deal Value by Stage")
                st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "pipeline" in filtered.columns:
            pipe_df = (
                filtered.groupby("pipeline", as_index=False)["amount"]
                .sum()
                .rename(columns={"amount": "total_amount"})
            )
            if not pipe_df.empty:
                fig = horizontal_bar_chart(pipe_df, y="pipeline", x="total_amount",
                                           title="Deal Value by Pipeline")
                st.plotly_chart(fig, use_container_width=True)

    # --- Data Table ---
    st.markdown("#### Deal Detail")
    display_cols = [c for c in [
        "deal_name", "deal_stage", "pipeline", "amount", "close_date",
        "days_in_pipeline", "is_closed_won", "is_closed_lost", "deal_source",
        "customer_name", "agent_name", "accounting_bucket",
    ] if c in filtered.columns]
    show_df = filtered[display_cols].sort_values("amount", ascending=False)

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
            "Deal Name": str(row.get("deal_name", "—")),
            "Stage": str(row.get("deal_stage", "—")),
            "Pipeline": str(row.get("pipeline", "—")),
            "Amount": f"${float(row.get('amount', 0)):,.0f}",
            "Close Date": str(row.get("close_date", "—"))[:10],
            "Days in Pipeline": str(int(row.get("days_in_pipeline", 0))),
            "Closed Won": str(row.get("is_closed_won", "—")),
            "Closed Lost": str(row.get("is_closed_lost", "—")),
            "Won Reason": str(row.get("closed_won_reason", "—")),
            "Loss Reason": str(row.get("loss_reason", "—")),
            "Deal Source": str(row.get("deal_source", "—")),
            "Client ID": str(row.get("client_id", "—")),
            "Customer": str(row.get("customer_name", "—")),
            "Parent Customer": str(row.get("parent_customer_name", "—")),
            "Accounting Bucket": str(row.get("accounting_bucket", "—")),
            "Customer Status": str(row.get("customer_status", "—")),
            "Agent": str(row.get("agent_name", "—")),
            "HubSpot Deal ID": str(row.get("hubspot_deal_id", "—")),
        }
        st.html(detail_panel_html(str(row.get("deal_name", "Deal Detail")), fields))
