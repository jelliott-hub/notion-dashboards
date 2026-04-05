"""catalog — Visual gallery of all available embeddable widgets."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import streamlit as st
from apps.widgets._base import _inject_widget_css
from apps.widgets._registry import WIDGETS
from core.style import PALETTE

DOMAIN_COLORS = {
    "support":  PALETTE["blue"],
    "finance":  PALETTE["green"],
    "sales":    PALETTE["amber"],
    "tickets":  PALETTE["navy"],
    "revenue":  PALETTE["blue_dark"],
}


def render():
    st.set_page_config(page_title="Widget Catalog", page_icon="◆", layout="wide")
    _inject_widget_css()

    st.html(f"""
    <div style="margin:0 0 24px 0;">
        <div style="font-size:18px;font-weight:600;color:{PALETTE['ink']};
                    letter-spacing:-0.3px;">Widget Catalog</div>
        <div style="font-size:13px;color:{PALETTE['secondary']};margin-top:3px;">
            Embeddable chart components for Notion. Use <code>?widget=ID</code> to load any widget.
        </div>
    </div>
    """)

    for w in WIDGETS:
        domain_clr = DOMAIN_COLORS.get(w["domain"], PALETTE["slate"])
        type_label = "metric strip" if w["type"] == "metric" else "chart"
        with st.container(border=True):
            st.html(f"""
            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                <div>
                    <div style="font-size:13px;font-weight:600;color:{PALETTE['ink']};">
                        {w['title']}
                        <span style="font-size:10px;font-weight:500;color:white;
                                     background:{domain_clr};padding:2px 6px;
                                     border-radius:4px;margin-left:8px;
                                     text-transform:uppercase;letter-spacing:0.5px;">
                            {w['domain']}
                        </span>
                    </div>
                    <div style="font-size:12px;color:{PALETTE['secondary']};margin-top:4px;">
                        {w['description']}
                    </div>
                    <div style="font-size:10px;color:{PALETTE['tertiary']};margin-top:4px;">
                        {type_label} · {w['default_height']}px · Source: {w['data_source']}
                    </div>
                </div>
                <div style="font-family:monospace;font-size:11px;color:{PALETTE['secondary']};
                            background:{PALETTE['bg']};padding:4px 8px;border-radius:4px;
                            white-space:nowrap;">
                    ?widget={w['id']}
                </div>
            </div>
            """)


if __name__ == "__main__":
    render()
