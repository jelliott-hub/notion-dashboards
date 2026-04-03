"""Chart factory functions for Plotly and ECharts."""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from core.theme import COLORS, COLOR_SEQUENCE, plotly_template


def _apply_template(fig: go.Figure) -> go.Figure:
    """Apply B4ALL template and clean up default Plotly chrome."""
    fig.update_layout(template=plotly_template())
    return fig


def _hex_to_rgba(hex_color: str, alpha: float = 0.094) -> str:
    """Convert a 6-digit hex color to an rgba() string. Alpha 0.094 ≈ hex 18."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def area_chart(
    df: pd.DataFrame, x: str, y_cols: list[str], title: str,
    fill: bool = True, dash_cols: list[str] | None = None,
) -> go.Figure:
    """Multi-series area/line chart."""
    fig = go.Figure()
    for i, col in enumerate(y_cols):
        is_dashed = dash_cols and col in dash_cols
        fig.add_trace(go.Scatter(
            x=df[x], y=df[col], name=col.replace("_", " ").title(),
            mode="lines", fill="tozeroy" if fill and i == 0 else ("tonexty" if fill and i > 0 else None),
            line=dict(color=COLOR_SEQUENCE[i % len(COLOR_SEQUENCE)], width=2.5,
                      dash="dash" if is_dashed else "solid"),
            fillcolor=_hex_to_rgba(COLOR_SEQUENCE[i % len(COLOR_SEQUENCE)]) if fill else None,
        ))
    fig.update_layout(title=title, hovermode="x unified")
    return _apply_template(fig)


def horizontal_bar_chart(
    df: pd.DataFrame, y: str, x: str, title: str,
    color: str | None = None, color_map: dict | None = None,
) -> go.Figure:
    """Horizontal bar chart, sorted by value."""
    df_sorted = df.sort_values(x, ascending=True)
    if color and color_map:
        colors = df_sorted[color].map(color_map).fillna(COLORS["slate"])
        fig = go.Figure(go.Bar(
            y=df_sorted[y], x=df_sorted[x], orientation="h",
            marker_color=colors.tolist(),
        ))
    else:
        fig = go.Figure(go.Bar(
            y=df_sorted[y], x=df_sorted[x], orientation="h",
            marker_color=COLORS["blue"],
        ))
    fig.update_layout(title=title, yaxis=dict(autorange="reversed"))
    return _apply_template(fig)


def stacked_bar_chart(
    df: pd.DataFrame, x: str, y: str, color: str, title: str,
    color_map: dict | None = None,
) -> go.Figure:
    """Stacked bar chart with color grouping."""
    fig = px.bar(
        df, x=x, y=y, color=color, title=title, barmode="stack",
        color_discrete_map=color_map or {},
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    return _apply_template(fig)


def funnel_chart(df: pd.DataFrame, stage: str, value: str, title: str) -> go.Figure:
    """Funnel chart for pipeline stages."""
    fig = go.Figure(go.Funnel(
        y=df[stage], x=df[value],
        marker=dict(color=COLOR_SEQUENCE[:len(df)]),
        textinfo="value+percent initial",
    ))
    fig.update_layout(title=title)
    return _apply_template(fig)


def heatmap_chart(
    df: pd.DataFrame, x: str, y: str, z: str, title: str,
) -> go.Figure:
    """Heatmap from long-format DataFrame."""
    pivot = df.pivot_table(index=y, columns=x, values=z, aggfunc="first")
    fig = go.Figure(go.Heatmap(
        z=pivot.values, x=pivot.columns.astype(str), y=pivot.index.astype(str),
        colorscale=[[0, COLORS["blue_light"]], [0.5, COLORS["blue"]], [1, COLORS["blue_dark"]]],
        texttemplate="%{z:.1f}%", textfont=dict(size=10),
    ))
    fig.update_layout(title=title)
    return _apply_template(fig)


def treemap_chart(
    df: pd.DataFrame, path: list[str], values: str, title: str,
    color: str | None = None,
) -> go.Figure:
    """Treemap chart."""
    fig = px.treemap(df, path=path, values=values, title=title, color=color,
                     color_discrete_sequence=COLOR_SEQUENCE)
    return _apply_template(fig)


def scatter_timeline(
    df: pd.DataFrame, x: str, y: str, size: str | None, color: str,
    title: str, color_map: dict | None = None,
) -> go.Figure:
    """Scatter plot on a date axis, with optional bubble sizing."""
    fig = px.scatter(
        df, x=x, y=y, size=size, color=color, title=title,
        color_discrete_map=color_map or {},
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    return _apply_template(fig)


def choropleth_map(
    df: pd.DataFrame, locations: str, color: str, title: str,
    color_map: dict | None = None,
) -> go.Figure:
    """US state choropleth map."""
    fig = px.choropleth(
        df, locations=locations, locationmode="USA-states", color=color,
        scope="usa", title=title,
        color_discrete_map=color_map or {},
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    fig.update_layout(geo=dict(bgcolor=COLORS["bg"], lakecolor=COLORS["white"]))
    return _apply_template(fig)


# --- ECharts configs (return dicts, rendered via st_echarts) ---

def gauge_chart(
    value: float, title: str, suffix: str = "%",
    min_val: float = 0, max_val: float = 100,
) -> dict:
    """ECharts gauge config."""
    return {
        "series": [{
            "type": "gauge",
            "startAngle": 200,
            "endAngle": -20,
            "min": min_val,
            "max": max_val,
            "data": [{"value": value, "name": title}],
            "detail": {
                "formatter": f"{{value}}{suffix}",
                "fontSize": 28,
                "fontWeight": "bold",
                "color": COLORS["navy"],
                "offsetCenter": [0, "60%"],
            },
            "title": {"fontSize": 12, "color": COLORS["slate"], "offsetCenter": [0, "85%"]},
            "axisLine": {
                "lineStyle": {
                    "width": 12,
                    "color": [
                        [value / max_val, {"type": "linear", "x": 0, "y": 0, "x2": 1, "y2": 0,
                                           "colorStops": [
                                               {"offset": 0, "color": COLORS["blue"]},
                                               {"offset": 1, "color": COLORS["success"]},
                                           ]}],
                        [1, COLORS["border"]],
                    ],
                }
            },
            "pointer": {"show": False},
            "axisTick": {"show": False},
            "splitLine": {"show": False},
            "axisLabel": {"show": False},
        }],
    }


def donut_chart(
    labels: list[str], values: list[int | float], title: str,
    colors: list[str] | None = None,
) -> dict:
    """ECharts donut/pie config."""
    data = [{"value": v, "name": l} for l, v in zip(labels, values)]
    return {
        "title": {"text": title, "left": "center", "textStyle": {"fontSize": 12, "color": COLORS["slate"]}},
        "series": [{
            "type": "pie",
            "radius": ["50%", "75%"],
            "center": ["50%", "55%"],
            "data": data,
            "label": {"show": False},
            "emphasis": {"label": {"show": True, "fontSize": 14, "fontWeight": "bold"}},
            "itemStyle": {"borderRadius": 6, "borderColor": COLORS["white"], "borderWidth": 2},
            "color": colors or COLOR_SEQUENCE[:len(labels)],
        }],
    }


def radar_chart(
    indicators: list[dict], series_data: list[dict], title: str,
) -> dict:
    """ECharts radar config. indicators: [{"name": str, "max": num}].
    series_data: [{"name": str, "value": [num, ...]}]."""
    return {
        "title": {"text": title, "left": "center", "textStyle": {"fontSize": 12, "color": COLORS["slate"]}},
        "radar": {"indicator": indicators, "shape": "polygon"},
        "series": [{
            "type": "radar",
            "data": series_data,
            "areaStyle": {"opacity": 0.15},
            "lineStyle": {"width": 2},
            "color": COLOR_SEQUENCE[:len(series_data)],
        }],
    }


def status_bars(items: list[dict], title: str) -> go.Figure:
    """
    Horizontal progress bars for reconciliation statuses.
    Each item: {"label": str, "value": num, "max": num, "status": str}
    """
    status_colors = {"success": COLORS["success"], "warning": COLORS["warning"], "error": COLORS["error"]}
    fig = go.Figure()
    for item in items:
        pct = item["value"] / item["max"] * 100 if item["max"] else 0
        color = status_colors.get(item["status"], COLORS["blue"])
        fig.add_trace(go.Bar(
            y=[item["label"]], x=[pct], orientation="h",
            marker_color=color, showlegend=False,
            text=f"{pct:.0f}%", textposition="inside",
        ))
    fig.update_layout(
        title=title, xaxis=dict(range=[0, 100], showticklabels=False),
        barmode="overlay", height=40 * len(items) + 80,
    )
    return _apply_template(fig)
