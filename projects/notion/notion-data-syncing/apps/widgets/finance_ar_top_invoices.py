"""finance_ar_top_invoices — Overdue invoices feed: client, invoice, amount, aging."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
import pandas as pd
from apps.widgets._base import widget_page, get_height
from core.db import query_view
from core.style import PALETTE

DEFAULT_HEIGHT = 400


def _aging_color(bucket: str) -> str:
    b = str(bucket).lower()
    if "90" in b or "+" in b:
        return PALETTE["red"]
    if "60" in b or "31" in b:
        return PALETTE["amber"]
    return PALETTE["blue"]


def render():
    df = query_view("finance_ar_aging")
    if df.empty:
        st.warning("No AR aging data available.")
        return

    df["amount_due"] = pd.to_numeric(df["amount_due"], errors="coerce").fillna(0)
    df["days_outstanding"] = pd.to_numeric(df["days_outstanding"], errors="coerce").fillna(0)

    # Only overdue
    overdue = df[df["aging_bucket"].str.lower() != "current"].copy()
    if overdue.empty:
        st.info("No overdue invoices.")
        return

    overdue = overdue.sort_values("amount_due", ascending=False).head(20)

    # Build styled HTML feed
    rows_html = ""
    for _, r in overdue.iterrows():
        client = r.get("client_name") or r.get("client_id", "—")
        client_id = r.get("client_id", "")
        inv = r.get("invoice_number", "—")
        amt = f"${r['amount_due']:,.0f}"
        days = int(r["days_outstanding"])
        bucket = str(r.get("aging_bucket", ""))
        clr = _aging_color(bucket)

        rows_html += f"""
        <div style="display:flex;align-items:center;justify-content:space-between;
                    padding:10px 12px;border-bottom:1px solid {PALETTE['border']};">
            <div style="flex:1;min-width:0;">
                <div style="font-size:13px;font-weight:600;color:{PALETTE['ink']};
                            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                    {client}
                </div>
                <div style="font-size:11px;color:{PALETTE['tertiary']};margin-top:2px;">
                    {client_id} &middot; Inv #{inv}
                </div>
            </div>
            <div style="text-align:right;margin-left:16px;flex-shrink:0;">
                <div style="font-size:14px;font-weight:600;color:{PALETTE['ink']};">{amt}</div>
                <div style="font-size:10px;font-weight:500;color:{clr};margin-top:2px;">
                    {days}d &middot; {bucket}
                </div>
            </div>
        </div>
        """

    st.html(f"""
    <div style="border:1px solid {PALETTE['border']};border-radius:8px;overflow:hidden;
                background:{PALETTE['card']};">
        <div style="display:flex;justify-content:space-between;padding:8px 12px;
                    background:{PALETTE['bg']};border-bottom:1px solid {PALETTE['border']};">
            <div style="font-size:10px;font-weight:600;text-transform:uppercase;
                        letter-spacing:0.5px;color:{PALETTE['tertiary']};">Client / Invoice</div>
            <div style="font-size:10px;font-weight:600;text-transform:uppercase;
                        letter-spacing:0.5px;color:{PALETTE['tertiary']};">Amount / Aging</div>
        </div>
        {rows_html}
    </div>
    """)


if __name__ == "__main__":
    widget_page("Overdue Invoices", DEFAULT_HEIGHT)
    render()
