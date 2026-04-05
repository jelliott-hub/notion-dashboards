"""gallery — Live render of all widgets in one place, grouped by domain.

Run:
    streamlit run apps/widgets/gallery.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import importlib
import streamlit as st
from apps.widgets._registry import WIDGETS
from core.style import inject_css, page_header, section_label, PALETTE

DOMAIN_COLORS = {
    "support":  PALETTE["blue"],
    "finance":  PALETTE["green"],
    "sales":    PALETTE["amber"],
    "tickets":  PALETTE["navy"],
    "revenue":  PALETTE["blue_dark"],
    "pnl":      "#8B5CF6",
}

DOMAIN_ORDER = ["pnl", "revenue", "support", "finance", "sales", "tickets"]


def main():
    st.set_page_config(page_title="Widget Gallery", page_icon="◆", layout="wide")
    inject_css()

    # ── Sidebar filters ──────────────────────────────────────────────
    with st.sidebar:
        st.html(f"""
        <div style="font-size:15px;font-weight:600;color:{PALETTE['ink']};
                    margin-bottom:12px;">Filters</div>
        """)
        domains = st.multiselect(
            "Domain",
            options=DOMAIN_ORDER,
            default=DOMAIN_ORDER,
            format_func=lambda d: f"{d.title()} ({sum(1 for w in WIDGETS if w['domain'] == d)})",
        )
        type_filter = st.radio(
            "Type", ["All", "Metrics", "Charts"],
            horizontal=True,
        )
        cols_per_row = st.slider("Cards per row", 1, 3, 2)

    # ── Header ────────────────────────────────────────────────────────
    filtered = [w for w in WIDGETS if w["domain"] in domains]
    if type_filter == "Metrics":
        filtered = [w for w in filtered if w["type"] == "metric"]
    elif type_filter == "Charts":
        filtered = [w for w in filtered if w["type"] != "metric"]

    st.html(page_header(
        "Widget Gallery",
        f"{len(filtered)} widgets · select domains in sidebar to filter",
    ))

    # ── Render by domain ──────────────────────────────────────────────
    for domain in DOMAIN_ORDER:
        domain_widgets = [w for w in filtered if w["domain"] == domain]
        if not domain_widgets:
            continue

        clr = DOMAIN_COLORS.get(domain, PALETTE["secondary"])
        st.html(f"""
        <div style="display:flex;align-items:center;gap:8px;margin:28px 0 12px 0;">
            <div style="font-size:11px;font-weight:600;text-transform:uppercase;
                        letter-spacing:0.8px;color:{PALETTE['tertiary']};">{domain}</div>
            <div style="width:6px;height:6px;border-radius:50%;background:{clr};"></div>
            <div style="font-size:11px;color:{PALETTE['tertiary']};">
                {len(domain_widgets)} widget{'s' if len(domain_widgets) != 1 else ''}
            </div>
        </div>
        """)

        # Chunk widgets into rows
        for i in range(0, len(domain_widgets), cols_per_row):
            row_widgets = domain_widgets[i : i + cols_per_row]
            cols = st.columns(cols_per_row)
            for j, w in enumerate(row_widgets):
                with cols[j]:
                    with st.container(border=True):
                        # Card header with ID badge
                        type_label = "metric strip" if w["type"] == "metric" else "chart"
                        st.html(f"""
                        <div style="display:flex;justify-content:space-between;
                                    align-items:flex-start;margin-bottom:8px;">
                            <div>
                                <div style="font-size:13px;font-weight:600;
                                            color:{PALETTE['ink']};">
                                    {w['title']}
                                    <span style="font-size:9px;font-weight:500;color:white;
                                                 background:{clr};padding:2px 5px;
                                                 border-radius:3px;margin-left:6px;
                                                 text-transform:uppercase;
                                                 letter-spacing:0.4px;">{type_label}</span>
                                </div>
                                <div style="font-size:11px;color:{PALETTE['secondary']};
                                            margin-top:2px;">{w['description']}</div>
                            </div>
                            <div style="font-family:monospace;font-size:10px;
                                        color:{PALETTE['tertiary']};background:{PALETTE['bg']};
                                        padding:3px 6px;border-radius:4px;white-space:nowrap;">
                                {w['id']}
                            </div>
                        </div>
                        """)

                        # Render the actual widget
                        try:
                            mod = importlib.import_module(f"apps.widgets.{w['id']}")
                            mod.render()
                        except Exception as e:
                            st.error(f"Failed: {e}", icon="⚠")


if __name__ == "__main__":
    main()
