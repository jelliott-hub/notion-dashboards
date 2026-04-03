"""
Chart factory functions for Plotly and ECharts.

All Plotly functions take a DataFrame + column names and return a go.Figure
with the B4ALL brand template applied. ECharts functions return a dict
config for use with st_echarts().

Plotly charts (return go.Figure — render with st.plotly_chart):
    area_chart          — multi-series line/area over time
    horizontal_bar_chart — sorted horizontal bars, optional color mapping
    stacked_bar_chart   — grouped stacked bars
    funnel_chart        — pipeline stage funnel
    heatmap_chart       — pivot heatmap from long-format data
    treemap_chart       — hierarchical treemap
    scatter_timeline    — scatter on date axis with optional bubble sizing
    choropleth_map      — US state choropleth
    status_bars         — horizontal progress bars for reconciliation

ECharts charts (return dict — render with st_echarts):
    gauge_chart         — radial gauge (e.g., margin %, SLA %)
    donut_chart         — donut/pie breakdown
    radar_chart         — multi-axis radar comparison
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from core.theme import COLORS, COLOR_SEQUENCE, plotly_template


def _apply_template(fig: go.Figure) -> go.Figure:
    """Apply B4ALL template and clean up default Plotly chrome."""
    fig.update_layout(template=plotly_template())
    return fig


def _hex_to_rgba(hex_color: str, alpha: float = 0.094) -> str:
    """Convert a 6-digit hex color to an rgba() string."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ---------------------------------------------------------------------------
# Plotly charts (return go.Figure)
# ---------------------------------------------------------------------------


def area_chart(
    df: pd.DataFrame, x: str, y_cols: list[str], title: str,
    fill: bool = True, dash_cols: list[str] | None = None,
) -> go.Figure:
    """
    Multi-series area or line chart over a shared x-axis.

    Args:
        df: DataFrame with one column for x-axis and one or more for y-series.
        x: Column name for the x-axis (typically a date column).
        y_cols: List of column names to plot as separate series.
        title: Chart title.
        fill: If True, fill area under each series. False for plain lines.
        dash_cols: Column names that should render as dashed lines.

    Example::

        fig = area_chart(df, x="report_month",
                         y_cols=["revenue", "cogs"],
                         title="Revenue vs COGS",
                         dash_cols=["cogs"])
        st.plotly_chart(fig, use_container_width=True)
    """
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
    """
    Horizontal bar chart, sorted by value.

    Args:
        df: DataFrame with label and value columns.
        y: Column name for bar labels (displayed on y-axis).
        x: Column name for bar values (displayed on x-axis).
        title: Chart title.
        color: Optional column name to color bars by category.
        color_map: Dict mapping category values to hex colors.
                   Used with color param (e.g., {"HIGH": "#E74C3C"}).

    Example::

        fig = horizontal_bar_chart(df, y="agent_name", x="total_calls",
                                   title="Call Volume by Agent")
        st.plotly_chart(fig, use_container_width=True)
    """
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
    """
    Stacked bar chart with color grouping.

    Args:
        df: Long-format DataFrame with x, y, and color columns.
        x: Column for x-axis categories.
        y: Column for bar heights (numeric).
        color: Column for stack grouping.
        title: Chart title.
        color_map: Optional dict mapping color values to hex colors.

    Example::

        fig = stacked_bar_chart(df, x="source", y="count",
                                color="relevance", title="RFPs by Source")
        st.plotly_chart(fig, use_container_width=True)
    """
    fig = px.bar(
        df, x=x, y=y, color=color, title=title, barmode="stack",
        color_discrete_map=color_map or {},
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    return _apply_template(fig)


def funnel_chart(df: pd.DataFrame, stage: str, value: str, title: str) -> go.Figure:
    """
    Funnel chart for pipeline stages.

    Args:
        df: DataFrame with stage labels and numeric values, ordered top-to-bottom.
        stage: Column name for stage labels.
        value: Column name for stage values (numeric).
        title: Chart title.

    Example::

        fig = funnel_chart(stage_df, stage="deal_stage",
                           value="total_amount", title="Deal Funnel")
        st.plotly_chart(fig, use_container_width=True)
    """
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
    """
    Heatmap from long-format DataFrame (auto-pivots to matrix).

    Args:
        df: Long-format DataFrame with x, y, and z columns.
        x: Column for horizontal axis categories.
        y: Column for vertical axis categories.
        z: Column for cell values (numeric).
        title: Chart title.

    Example::

        fig = heatmap_chart(df, x="month_label", y="gl_name",
                            z="mom_pct_change", title="MoM % by Account")
        st.plotly_chart(fig, use_container_width=True)
    """
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
    """
    Hierarchical treemap chart.

    Args:
        df: DataFrame with hierarchy columns and a numeric values column.
        path: List of column names defining the hierarchy (outer → inner).
        values: Column name for tile sizing (must be positive).
        title: Chart title.
        color: Optional column to color tiles by category.

    Example::

        fig = treemap_chart(df, path=["state_abbr", "priority_tier"],
                            values="count", title="Prospects by State")
        st.plotly_chart(fig, use_container_width=True)
    """
    fig = px.treemap(df, path=path, values=values, title=title, color=color,
                     color_discrete_sequence=COLOR_SEQUENCE)
    return _apply_template(fig)


def scatter_timeline(
    df: pd.DataFrame, x: str, y: str, size: str | None, color: str,
    title: str, color_map: dict | None = None,
) -> go.Figure:
    """
    Scatter plot on a date axis, with optional bubble sizing.

    Args:
        df: DataFrame with date, category, and optional size columns.
        x: Column for x-axis (typically a date).
        y: Column for y-axis categories.
        size: Column for bubble sizing (numeric, or None for uniform dots).
        color: Column for color grouping.
        title: Chart title.
        color_map: Optional dict mapping color values to hex colors.

    Example::

        fig = scatter_timeline(df, x="due_date", y="source",
                               size="amount", color="relevance",
                               title="RFP Timeline")
        st.plotly_chart(fig, use_container_width=True)
    """
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
    """
    US state choropleth map.

    Args:
        df: DataFrame with a column of 2-letter state abbreviations.
        locations: Column name with state abbreviations (e.g., "CA", "TX").
        color: Column for color grouping.
        title: Chart title.
        color_map: Optional dict mapping color values to hex colors.

    Example::

        fig = choropleth_map(df, locations="state_abbr",
                             color="channeler_model",
                             title="Channeler Model by State",
                             color_map={"open": "#22C55E", "closed": "#E74C3C"})
        st.plotly_chart(fig, use_container_width=True)
    """
    fig = px.choropleth(
        df, locations=locations, locationmode="USA-states", color=color,
        scope="usa", title=title,
        color_discrete_map=color_map or {},
        color_discrete_sequence=COLOR_SEQUENCE,
    )
    fig.update_layout(geo=dict(bgcolor=COLORS["bg"], lakecolor=COLORS["white"]))
    return _apply_template(fig)


def status_bars(items: list[dict], title: str) -> go.Figure:
    """
    Horizontal progress bars for reconciliation or completion statuses.

    Args:
        items: List of dicts, each with:
            - "label" (str): bar label
            - "value" (number): current value
            - "max" (number): maximum value (100% reference)
            - "status" (str): one of "success", "warning", "error"
        title: Chart title.

    Example::

        fig = status_bars([
            {"label": "P&L Accounts", "value": 42, "max": 45, "status": "success"},
            {"label": "AR Recon", "value": 70, "max": 100, "status": "warning"},
        ], title="Reconciliation Status")
        st.plotly_chart(fig, use_container_width=True)
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


# ---------------------------------------------------------------------------
# ECharts charts (return dict — render with st_echarts)
# ---------------------------------------------------------------------------


def gauge_chart(
    value: float, title: str, suffix: str = "%",
    min_val: float = 0, max_val: float = 100,
) -> dict:
    """
    Radial gauge chart (ECharts). Good for single KPI percentages.

    Args:
        value: Current value to display.
        title: Label shown below the value.
        suffix: Unit suffix (default "%").
        min_val: Gauge minimum (default 0).
        max_val: Gauge maximum (default 100).

    Returns:
        dict config for st_echarts().

    Example::

        from streamlit_echarts import st_echarts
        st_echarts(gauge_chart(62.4, "Gross Margin"), height="250px")
    """
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
    """
    Donut/pie chart (ECharts). Good for part-of-whole breakdowns.

    Args:
        labels: Category names.
        values: Numeric values (one per label).
        title: Chart title shown above.
        colors: Optional list of hex colors (one per label).
                Defaults to COLOR_SEQUENCE.

    Returns:
        dict config for st_echarts().

    Example::

        st_echarts(donut_chart(
            labels=["Passing", "Failing"],
            values=[42, 3],
            title="Account Status",
            colors=["#22C55E", "#E74C3C"],
        ), height="250px")
    """
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
    """
    Radar/spider chart (ECharts). Good for multi-axis comparison across entities.

    Args:
        indicators: List of axis definitions, each {"name": str, "max": number}.
        series_data: List of series, each {"name": str, "value": [num, ...]}.
                     Values must match indicator order.
        title: Chart title.

    Returns:
        dict config for st_echarts().

    Example::

        st_echarts(radar_chart(
            indicators=[{"name": "Calls", "max": 500}, {"name": "Answer %", "max": 100}],
            series_data=[
                {"name": "Agent A", "value": [320, 92]},
                {"name": "Agent B", "value": [210, 88]},
            ],
            title="Agent Comparison",
        ), height="320px")
    """
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
