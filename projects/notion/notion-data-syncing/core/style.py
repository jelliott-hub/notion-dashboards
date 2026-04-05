"""Stripe-inspired styling for Streamlit dashboards and widgets.

Canonical location for the bento/embed styling shared across all apps.
All helpers produce raw HTML strings or Plotly layout dicts — no Streamlit widgets.
"""

import streamlit as st

# ── Palette ──────────────────────────────────────────────────────────
# B4ALL brand colors + Stripe-clean layout
PALETTE = {
    "ink":         "#0D1B2A",    # Navy — primary text
    "secondary":   "#64748B",    # Slate — labels, secondary text
    "tertiary":    "#94A3B8",    # Light slate — subtitles, hints
    "border":      "#E2E8F0",    # Light border
    "grid":        "#F1F5F9",    # Chart gridlines
    "bg":          "#F4F6FA",    # Page background
    "card":        "#FFFFFF",    # Card fill
    "blue":        "#2B7BE9",    # Brand Blue — primary accent
    "blue_dark":   "#1A5FC7",    # Blue Dark — hover, emphasis
    "blue_light":  "#E8F1FD",    # Blue Light — washes, fills
    "navy":        "#0D1B2A",    # Navy — headings
    "green":       "#22C55E",    # Success
    "amber":       "#F59E0B",    # Warning
    "red":         "#E74C3C",    # Error
}

CHART_COLORS = [
    "#2B7BE9",  # Brand Blue
    "#1A5FC7",  # Blue Dark
    "#22C55E",  # Success green
    "#F59E0B",  # Amber
    "#0D1B2A",  # Navy
    "#64748B",  # Slate
    "#8B5CF6",  # Purple accent
    "#EC4899",  # Pink accent
]


# ── CSS injection ────────────────────────────────────────────────────

def inject_css():
    """Inject Stripe-like global styles. Call once at top of app."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* ── Page ──────────────────────────────────────────── */
    .stApp {
        background: #F4F6FA !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', sans-serif !important;
    }

    /* ── Hide Streamlit chrome ─────────────────────────── */
    #MainMenu, footer, header,
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    .stDeployButton,
    [data-testid="stHeader"] { display: none !important; }

    /* ── Bordered containers → bento cards ─────────────── */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        background: #FFFFFF !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
        transition: box-shadow 0.15s ease;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: 0 2px 8px rgba(0,0,0,0.07) !important;
    }

    /* ── Column gaps ───────────────────────────────────── */
    [data-testid="stHorizontalBlock"] { gap: 16px !important; }

    /* ── Clean plotly embeds ────────────────────────────── */
    .js-plotly-plot .plotly .modebar { display: none !important; }

    /* ── Remove default streamlit padding at top ───────── */
    .block-container { padding-top: 2rem !important; }

    /* ── Dataframe styling ─────────────────────────────── */
    [data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }
    </style>
    """, unsafe_allow_html=True)


# ── HTML helpers ─────────────────────────────────────────────────────

def metric_card(label: str, value: str, subtitle: str = "",
                color: str | None = None) -> str:
    """Small metric for rendering inside st.container(border=True).

    Args:
        label: Uppercase caption (e.g. "TOTAL CALLS").
        value: Large formatted number.
        subtitle: Optional secondary line (e.g. delta or context).
        color: Subtitle text color. Defaults to secondary gray.
    """
    sub_html = ""
    if subtitle:
        c = color or PALETTE["secondary"]
        sub_html = (
            f'<div style="font-size:12px;color:{c};margin-top:4px;'
            f'font-weight:500;">{subtitle}</div>'
        )
    return f"""
    <div style="padding:2px 0;">
        <div style="font-size:11px;font-weight:600;color:{PALETTE['secondary']};
                    text-transform:uppercase;letter-spacing:0.6px;">{label}</div>
        <div style="font-size:28px;font-weight:600;color:{PALETTE['ink']};
                    margin:6px 0 0 0;line-height:1.1;letter-spacing:-0.5px;">{value}</div>
        {sub_html}
    </div>
    """


def card_header(title: str, subtitle: str = "", source: str = "") -> str:
    """Subtle header for chart cards with optional data source citation."""
    sub = ""
    if subtitle:
        sub = (
            f'<span style="color:{PALETTE["tertiary"]};font-weight:400;'
            f'margin-left:6px;font-size:12px;">{subtitle}</span>'
        )
    src = ""
    if source:
        src = (
            f'<div style="font-size:10px;color:{PALETTE["tertiary"]};'
            f'margin-top:1px;font-weight:400;">Source: {source}</div>'
        )
    return (
        f'<div style="margin-bottom:4px;">'
        f'<div style="font-size:13px;font-weight:600;color:{PALETTE["ink"]};'
        f'letter-spacing:-0.1px;">{title}{sub}</div>{src}</div>'
    )


def section_label(text: str) -> str:
    """Thin section divider label between card rows."""
    return (
        f'<div style="font-size:11px;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:0.8px;color:{PALETTE["tertiary"]};'
        f'margin:28px 0 12px 0;">{text}</div>'
    )


def page_header(title: str, subtitle: str = "") -> str:
    """Dashboard page title — small and subtle, not a hero."""
    sub = ""
    if subtitle:
        sub = (
            f'<div style="font-size:13px;color:{PALETTE["secondary"]};'
            f'margin-top:3px;">{subtitle}</div>'
        )
    return (
        f'<div style="margin:0 0 24px 0;">'
        f'<div style="font-size:18px;font-weight:600;color:{PALETTE["ink"]};'
        f'letter-spacing:-0.3px;">{title}</div>{sub}</div>'
    )


# ── Chart layout ─────────────────────────────────────────────────────

def chart_layout(**overrides) -> dict:
    """Base Plotly layout dict for Stripe-style charts.

    Transparent background (sits on white card), light gridlines,
    no borders, refined typography. Pass keyword overrides to customize.
    """
    base = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=8, b=0),
        font=dict(
            family="Inter, -apple-system, sans-serif",
            size=11,
            color=PALETTE["secondary"],
        ),
        xaxis=dict(
            gridcolor=PALETTE["grid"],
            zeroline=False,
            showline=False,
            tickfont=dict(size=11, color=PALETTE["secondary"]),
        ),
        yaxis=dict(
            gridcolor=PALETTE["grid"],
            zeroline=False,
            showline=False,
            tickfont=dict(size=11, color=PALETTE["secondary"]),
        ),
        showlegend=False,
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="white",
            bordercolor=PALETTE["border"],
            font=dict(size=12, family="Inter, sans-serif", color=PALETTE["ink"]),
        ),
    )

    # Deep-merge axis overrides
    for axis_key in ("xaxis", "yaxis"):
        if axis_key in overrides:
            base[axis_key] = {**base[axis_key], **overrides.pop(axis_key)}

    base.update(overrides)
    return base
