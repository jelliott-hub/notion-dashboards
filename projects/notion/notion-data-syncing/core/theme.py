"""
B4ALL brand colors and chart theme configurations.

Color palette:
    COLORS["navy"]       — #0D1B2A  primary text, headings
    COLORS["blue"]       — #2B7BE9  primary accent, links
    COLORS["blue_dark"]  — #1A5FC7  hover states, secondary accent
    COLORS["blue_light"] — #E8F1FD  panel backgrounds, highlights
    COLORS["bg"]         — #F4F6FA  page background
    COLORS["white"]      — #FFFFFF  card backgrounds, plot area
    COLORS["border"]     — #E2E8F0  borders, grid lines
    COLORS["slate"]      — #64748B  secondary text, labels
    COLORS["success"]    — #22C55E  positive status (pass, won, on-time)
    COLORS["warning"]    — #F59E0B  caution status (warn, pending)
    COLORS["error"]      — #E74C3C  negative status (fail, overdue, lost)

COLOR_SEQUENCE is an 8-color palette for multi-series charts.

Usage::

    from core.theme import COLORS, COLOR_SEQUENCE, plotly_template

    # Direct color access
    fig.update_layout(paper_bgcolor=COLORS["bg"])

    # Apply full template to a Plotly figure
    fig.update_layout(template=plotly_template())

    # ECharts theme dict
    from core.theme import echarts_theme
    theme = echarts_theme()
"""

import plotly.graph_objects as go

COLORS = {
    "navy": "#0D1B2A",
    "blue": "#2B7BE9",
    "blue_dark": "#1A5FC7",
    "blue_light": "#E8F1FD",
    "bg": "#F4F6FA",
    "white": "#FFFFFF",
    "border": "#E2E8F0",
    "slate": "#64748B",
    "success": "#22C55E",
    "warning": "#F59E0B",
    "error": "#E74C3C",
}

# Plotly color sequence for multi-series charts
COLOR_SEQUENCE = [
    COLORS["blue"],
    COLORS["blue_dark"],
    COLORS["success"],
    COLORS["warning"],
    COLORS["error"],
    COLORS["slate"],
    "#8B5CF6",  # purple
    "#EC4899",  # pink
]


def plotly_template() -> go.layout.Template:
    """Return a Plotly template configured with B4ALL brand colors."""
    return go.layout.Template(
        layout=go.Layout(
            paper_bgcolor=COLORS["bg"],
            plot_bgcolor=COLORS["white"],
            font=dict(family="Inter, system-ui, sans-serif", color=COLORS["navy"], size=12),
            colorway=COLOR_SEQUENCE,
            margin=dict(l=40, r=20, t=40, b=40),
            xaxis=dict(
                gridcolor=COLORS["border"],
                linecolor=COLORS["border"],
                zerolinecolor=COLORS["border"],
            ),
            yaxis=dict(
                gridcolor=COLORS["border"],
                linecolor=COLORS["border"],
                zerolinecolor=COLORS["border"],
            ),
            hoverlabel=dict(
                bgcolor=COLORS["white"],
                bordercolor=COLORS["border"],
                font_color=COLORS["navy"],
                font_size=12,
            ),
        )
    )


def echarts_theme() -> dict:
    """Return an ECharts theme dict configured with B4ALL brand colors."""
    return {
        "color": COLOR_SEQUENCE,
        "backgroundColor": COLORS["white"],
        "textStyle": {"color": COLORS["navy"]},
        "title": {"textStyle": {"color": COLORS["navy"]}, "subtextStyle": {"color": COLORS["slate"]}},
        "legend": {"textStyle": {"color": COLORS["slate"]}},
        "gauge": {
            "axisLine": {"lineStyle": {"color": [[0.3, COLORS["error"]], [0.7, COLORS["warning"]], [1, COLORS["success"]]]}},
        },
    }
