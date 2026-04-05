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

    # Auto-height JS for embed mode: measures viewport, resizes Plotly/ECharts to fill
    auto_height_js = ""
    if embed:
        auto_height_js = """
    <script>
    function autoResizeCharts() {
        const vh = window.innerHeight;
        // Leave room for header if present, otherwise fill fully
        const headerEl = document.querySelector('[data-testid="stMarkdownContainer"]');
        const headerH = headerEl ? headerEl.offsetHeight + 8 : 0;
        const chartH = Math.max(vh - headerH - 16, 200);

        // Resize Plotly charts
        document.querySelectorAll('.js-plotly-plot').forEach(el => {
            el.style.height = chartH + 'px';
            const plotDiv = el.querySelector('.plot-container');
            if (plotDiv) plotDiv.style.height = chartH + 'px';
            const svgContainer = el.querySelector('.svg-container');
            if (svgContainer) svgContainer.style.height = chartH + 'px';
            if (window.Plotly && el.data) {
                window.Plotly.relayout(el, {height: chartH});
            }
        });

        // Resize ECharts iframes
        document.querySelectorAll('iframe[title*="echarts"]').forEach(el => {
            el.style.height = chartH + 'px';
        });
    }

    // Run on load and on resize
    const observer = new MutationObserver(() => {
        clearTimeout(window._resizeTimer);
        window._resizeTimer = setTimeout(autoResizeCharts, 150);
    });
    observer.observe(document.body, {childList: true, subtree: true});
    window.addEventListener('resize', () => {
        clearTimeout(window._resizeTimer);
        window._resizeTimer = setTimeout(autoResizeCharts, 100);
    });
    // Initial run after Streamlit renders
    setTimeout(autoResizeCharts, 500);
    setTimeout(autoResizeCharts, 1500);
    </script>
    """

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

    {"/* Embed mode: fill viewport */" if embed else ""}
    {'''
    html, body, .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    .main .block-container {
        height: 100vh !important;
        max-height: 100vh !important;
        overflow: hidden !important;
    }
    ''' if embed else ""}

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
    iframe[title*="echarts"] {{
        width: 100% !important;
    }}
    </style>
    {auto_height_js}
    """, unsafe_allow_html=True)
