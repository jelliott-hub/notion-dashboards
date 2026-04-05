"""Widget framework — bootstrap for standalone Streamlit chart embeds.

Each widget calls widget_page() once at startup to configure the page,
inject embed-optimised CSS, and optionally render a card header.

Widgets use transparent backgrounds so they blend into Notion embed blocks.
"""

import streamlit as st
from core.style import card_header, PALETTE


def widget_page(title: str, default_height: int = 300):
    """One-call widget bootstrap. Handles page config, CSS, and header.

    Args:
        title: Widget title (used in browser tab and optional card header).
        default_height: Fallback chart height in pixels.
    """
    st.set_page_config(page_title=title, page_icon="◆", layout="wide")
    _inject_widget_css()

    params = st.query_params
    show_header = params.get("show_header", "true").lower() != "false"

    if show_header:
        source = params.get("source", "")
        st.html(card_header(title, source=source))


def get_height(default: int = 300) -> int:
    """Read chart height from query params, falling back to *default*."""
    try:
        return int(st.query_params.get("height", default))
    except (ValueError, TypeError):
        return default


def _inject_widget_css():
    """Slim CSS for widget embeds — transparent bg, tight padding, no chrome."""
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    .stApp {{
        background: transparent !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }}

    /* Hide all Streamlit chrome */
    #MainMenu, footer, header,
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    .stDeployButton,
    [data-testid="stHeader"] {{ display: none !important; }}

    /* Tight padding for embed blocks */
    .block-container {{
        padding: 0.5rem 1rem 0 1rem !important;
        overflow: hidden !important;
    }}

    /* Bento card styling for containers */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        border: 1px solid {PALETTE['border']} !important;
        border-radius: 12px !important;
        background: {PALETTE['card']} !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    }}

    [data-testid="stHorizontalBlock"] {{ gap: 12px !important; }}
    .js-plotly-plot .plotly .modebar {{ display: none !important; }}
    </style>
    """, unsafe_allow_html=True)
