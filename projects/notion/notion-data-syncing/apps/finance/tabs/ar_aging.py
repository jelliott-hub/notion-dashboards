# apps/finance/tabs/ar_aging.py
"""AR Aging tab — invoice aging buckets, overdue analysis, client detail."""

import streamlit as st
import pandas as pd
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html
from core.charts import horizontal_bar_chart


BUCKET_ORDER = ["Current", "1-30", "31-60", "61-90", "91-120", "120+"]

BUCKET_COLORS = {
    "Current": COLORS["success"],
    "1-30": COLORS["blue"],
    "31-60": COLORS["warning"],
    "61-90": "#F97316",   # orange
    "91-120": COLORS["error"],
    "120+": COLORS["navy"],
}


def render():
    df = query_view("finance_ar_aging")
    if df.empty:
        st.warning("No AR aging data available.")
        return

    # Ensure numeric columns
    df["amount_due"] = pd.to_numeric(df["amount_due"], errors="coerce").fillna(0)
    df["days_outstanding"] = pd.to_numeric(df["days_outstanding"], errors="coerce").fillna(0)

    # --- KPI Strip ---
    total_ar = df["amount_due"].sum()
    current_ar = df[df["aging_bucket"] == "Current"]["amount_due"].sum()
    bucket_31_60 = df[df["aging_bucket"] == "31-60"]["amount_due"].sum()
    bucket_90_plus = df[df["aging_bucket"].isin(["91-120", "120+"])]["amount_due"].sum()

    kpis = [
        {"label": "Total AR", "value": f"${total_ar:,.0f}", "color": COLORS["navy"]},
        {"label": "Current", "value": f"${current_ar:,.0f}", "color": COLORS["success"],
         "border_color": COLORS["success"]},
        {"label": "31–60 Days", "value": f"${bucket_31_60:,.0f}", "color": COLORS["warning"],
         "border_color": COLORS["warning"] if bucket_31_60 > 0 else None},
        {"label": "90+ Days", "value": f"${bucket_90_plus:,.0f}", "color": COLORS["error"],
         "border_color": COLORS["error"] if bucket_90_plus > 0 else None},
    ]
    st.html(kpi_strip_html(kpis))

    # --- Bucket filter ---
    available_buckets = [b for b in BUCKET_ORDER if b in df["aging_bucket"].unique()]
    selected_buckets = st.multiselect(
        "Filter by aging bucket", available_buckets, default=available_buckets
    )
    filtered_df = df[df["aging_bucket"].isin(selected_buckets)].copy() if selected_buckets else df.copy()

    # --- Charts Row ---
    col1, col2 = st.columns(2)

    with col1:
        bucket_summary = (
            filtered_df.groupby("aging_bucket", as_index=False)["amount_due"]
            .sum()
            .rename(columns={"amount_due": "total_due"})
        )
        # Sort by bucket order
        bucket_summary["_order"] = bucket_summary["aging_bucket"].map(
            {b: i for i, b in enumerate(BUCKET_ORDER)}
        )
        bucket_summary = bucket_summary.sort_values("_order")

        fig = horizontal_bar_chart(
            bucket_summary, y="aging_bucket", x="total_due",
            title="AR by Aging Bucket",
            color="aging_bucket", color_map=BUCKET_COLORS,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        top10 = (
            filtered_df.nlargest(10, "amount_due")[["invoice_number", "amount_due"]]
            .copy()
        )
        fig2 = horizontal_bar_chart(
            top10, y="invoice_number", x="amount_due",
            title="Top 10 Overdue Invoices",
        )
        st.plotly_chart(fig2, use_container_width=True)

    # --- Data Table ---
    st.markdown("#### Invoice Detail")
    table_cols = ["client_id", "invoice_number", "invoice_date", "due_date",
                  "amount_due", "days_outstanding", "aging_bucket"]
    show_df = filtered_df[table_cols].sort_values("days_outstanding", ascending=False)

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
        full_row = filtered_df[filtered_df["invoice_number"] == row["invoice_number"]].iloc[0]
        fields = {
            "Client ID": str(full_row["client_id"]),
            "Invoice Number": str(full_row["invoice_number"]),
            "Invoice Date": str(full_row.get("invoice_date", "—")),
            "Due Date": str(full_row.get("due_date", "—")),
            "Amount Due": f"${full_row['amount_due']:,.2f}",
            "Days Outstanding": str(int(full_row["days_outstanding"])),
            "Aging Bucket": str(full_row["aging_bucket"]),
            "Report Month": str(full_row.get("report_month", "—")),
        }
        st.html(detail_panel_html(f"Invoice {full_row['invoice_number']} — Detail", fields))
