"""Reusable UI components rendered as branded HTML via st.html()."""

from core.theme import COLORS

_STATUS_COLORS = {
    "success": COLORS["success"],
    "warning": COLORS["warning"],
    "error": COLORS["error"],
    "info": COLORS["blue"],
    "neutral": COLORS["slate"],
}


def kpi_strip_html(items: list[dict]) -> str:
    """
    Render a horizontal strip of KPI cards as HTML.

    Each item: {"label": str, "value": str, "color": str, "subtitle": str (optional),
                "border_color": str (optional — left accent border)}
    """
    cards = []
    for item in items:
        border = f"border-left:3px solid {item['border_color']};" if item.get("border_color") else ""
        subtitle = f'<div style="font-size:11px;color:{COLORS["slate"]};">{item["subtitle"]}</div>' if item.get("subtitle") else ""
        cards.append(f"""
        <div style="background:{COLORS['white']};border:1px solid {COLORS['border']};{border}
                     border-radius:8px;padding:12px 18px;flex:1;min-width:120px;">
            <div style="font-size:10px;color:{COLORS['slate']};text-transform:uppercase;
                        letter-spacing:0.5px;font-weight:500;">{item['label']}</div>
            <div style="font-size:24px;font-weight:700;color:{item['color']};margin:2px 0;">
                {item['value']}</div>
            {subtitle}
        </div>""")

    return f"""<div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap;">
        {''.join(cards)}
    </div>"""


def detail_panel_html(title: str, fields: dict) -> str:
    """
    Render an expandable detail panel with key-value pairs.

    Args:
        title: Panel header text
        fields: dict of {label: value} pairs to display
    """
    rows = []
    for label, value in fields.items():
        rows.append(f"""
            <div style="display:flex;justify-content:space-between;padding:6px 0;
                        border-bottom:1px solid {COLORS['bg']};">
                <span style="color:{COLORS['slate']};font-size:12px;">{label}</span>
                <span style="color:{COLORS['navy']};font-weight:500;font-size:12px;">{value}</span>
            </div>""")

    return f"""
    <div style="background:{COLORS['blue_light']};border:1px solid {COLORS['blue']};
                border-radius:8px;padding:16px;margin-top:12px;">
        <div style="font-size:14px;font-weight:600;color:{COLORS['navy']};margin-bottom:10px;">
            {title}</div>
        <div style="background:{COLORS['white']};border-radius:6px;padding:10px;
                    border:1px solid {COLORS['border']};">
            {''.join(rows)}
        </div>
    </div>"""


def status_pill_html(text: str, status: str) -> str:
    """
    Render a colored status pill (PASS, FAIL, WARN, etc.).

    Args:
        text: Display text
        status: One of "success", "warning", "error", "info", "neutral"
    """
    color = _STATUS_COLORS.get(status, COLORS["slate"])
    return f"""<span style="background:{color}18;color:{color};padding:3px 10px;
               border-radius:12px;font-size:11px;font-weight:600;">{text}</span>"""
