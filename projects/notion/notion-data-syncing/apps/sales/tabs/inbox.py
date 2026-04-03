# apps/sales/tabs/inbox.py
"""Sales Inbox tab — email feed sorted by received date with detail panel."""

import streamlit as st
import pandas as pd
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html


def render():
    df = query_view("sales_inbox")
    if df.empty:
        st.warning("No sales inbox data available.")
        return

    # Coerce types
    df["received_at"] = pd.to_datetime(df["received_at"], errors="coerce")
    for bool_col in ["has_attachments", "is_read"]:
        if bool_col in df.columns:
            df[bool_col] = df[bool_col].astype(str).str.lower().isin(["true", "1", "yes", "t"])

    # --- KPIs ---
    total = len(df)
    unread = int((~df["is_read"]).sum()) if "is_read" in df.columns else 0
    with_attachments = int(df["has_attachments"].sum()) if "has_attachments" in df.columns else 0

    kpis = [
        {"label": "Total Emails", "value": f"{total:,}", "color": COLORS["navy"]},
        {"label": "Unread", "value": str(unread), "color": COLORS["warning"],
         "border_color": COLORS["warning"] if unread > 0 else None},
        {"label": "With Attachments", "value": str(with_attachments), "color": COLORS["blue"],
         "border_color": COLORS["blue"] if with_attachments > 0 else None},
    ]
    st.html(kpi_strip_html(kpis))

    # --- Data Table ---
    st.markdown("#### Email Feed")
    display_cols = [c for c in [
        "received_at", "from_name", "from_address", "subject",
        "direction", "is_read", "has_attachments", "importance",
        "mailbox", "folder_path",
    ] if c in df.columns]
    show_df = df[display_cols].sort_values("received_at", ascending=False) if "received_at" in df.columns else df[display_cols]

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
        row = df.loc[orig_idx]

        received = row.get("received_at", "—")
        received_str = str(received)[:19] if pd.notna(received) else "—"

        fields = {
            "Subject": str(row.get("subject", "—")),
            "From": f"{row.get('from_name', '')} <{row.get('from_address', '')}>",
            "Received": received_str,
            "Direction": str(row.get("direction", "—")),
            "Mailbox": str(row.get("mailbox", "—")),
            "Folder": str(row.get("folder_path", "—")),
            "Importance": str(row.get("importance", "—")),
            "Is Read": str(row.get("is_read", "—")),
            "Has Attachments": str(row.get("has_attachments", "—")),
            "Preview": str(row.get("body_preview", "—")),
        }
        st.html(detail_panel_html(str(row.get("subject", "Email Detail")), fields))
