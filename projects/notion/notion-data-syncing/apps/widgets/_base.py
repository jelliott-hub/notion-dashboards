"""Widget framework — bootstrap for standalone Streamlit chart embeds.

Each widget calls widget_page() once at startup to configure the page,
inject embed-optimised CSS, and optionally render a card header.

Widgets use transparent backgrounds so they blend into Notion embed blocks.
Supports ?embed=true for Notion iframe mode (fills container, no padding).
"""

import streamlit as st
from core.style import card_header, PALETTE


def is_embed() -> bool:
    """Check if running in embed/iframe mode via query param."""
    return st.query_params.get("embed", "false").lower() == "true"


def widget_page(title: str, default_height: int = 300):
    """One-call widget bootstrap. Handles page config, CSS, and header.

    Args:
        title: Widget title (used in browser tab and optional card header).
        default_height: Fallback chart height in pixels.
    """
    st.set_page_config(page_title=title, page_icon="◆", layout="wide")
    _inject_widget_css()

    params = st.query_params
    # Hide header by default in embed mode
    embed = is_embed()
    show_header_default = "false" if embed else "true"
    show_header = params.get("show_header", show_header_default).lower() != "false"

    if show_header:
        source = params.get("source", "")
        st.html(card_header(title, source=source))


def get_height(default: int = 300) -> int:
    """Read chart height from query params, falling back to *default*.

    In embed mode, uses a larger default to fill the Notion container.
    """
    try:
        h = st.query_params.get("height")
        if h:
            return int(h)
    except (ValueError, TypeError):
        pass
    # In embed mode, fill more vertical space
    if is_embed():
        return max(default, 360)
    return default


def _inject_widget_css():
    """Slim CSS for widget embeds — transparent bg, tight padding, no chrome."""
    embed = is_embed()

    # Tighter padding for embed mode
    padding = "0 0.5rem 0 0.5rem" if embed else "0.5rem 1rem 0 1rem"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, .stApp {{
        background: transparent !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        overflow: hidden !important;
    }}

    /* Hide all Streamlit chrome */
    #MainMenu, footer, header,
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    .stDeployButton,
    [data-testid="stHeader"],
    [data-testid="stBottom"] {{ display: none !important; }}

    /* Tight padding for embed blocks */
    .block-container {{
        padding: {padding} !important;
        max-width: 100% !important;
        overflow: hidden !important;
    }}

    /* Make charts fill available width */
    .js-plotly-plot, .plotly {{
        width: 100% !important;
    }}
    .js-plotly-plot .plotly .modebar {{ display: none !important; }}

    /* Responsive chart containers */
    [data-testid="stPlotlyChart"] {{
        width: 100% !important;
    }}
    [data-testid="stPlotlyChart"] > div {{
        width: 100% !important;
    }}

    /* Bento card styling for containers (non-embed only) */
    {"" if embed else f'''
    [data-testid="stVerticalBlockBorderWrapper"] {{
        border: 1px solid {PALETTE['border']} !important;
        border-radius: 12px !important;
        background: {PALETTE['card']} !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
    }}
    '''}

    [data-testid="stHorizontalBlock"] {{ gap: 12px !important; }}

    /* ECharts containers fill width */
    iframe[title="streamlit_echarts.st_echarts"] {{
        width: 100% !important;
    }}
    </style>
    """, unsafe_allow_html=True)
