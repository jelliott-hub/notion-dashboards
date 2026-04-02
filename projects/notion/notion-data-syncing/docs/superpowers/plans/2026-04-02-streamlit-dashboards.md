# Streamlit Dashboards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 3 Streamlit dashboard apps (Finance, Sales, Support) that query Supabase `notion_sync` views live and embed into Notion hub pages.

**Architecture:** Monorepo with shared `core/` library (DB, theme, components, charts). Each app is a separate Streamlit entrypoint with tabbed views. Plotly for data charts, ECharts for gauges/donuts/radar, custom HTML for KPI strips and detail panels.

**Tech Stack:** Streamlit 1.37+, Plotly 5.18+, streamlit-echarts, psycopg2-binary, pandas

**Spec:** `docs/superpowers/specs/2026-04-02-streamlit-dashboards-design.md`

---

## File Structure

```
notion-data-syncing/
├── apps/
│   ├── finance/
│   │   ├── app.py                 # Finance entrypoint — tab router
│   │   └── tabs/
│   │       ├── __init__.py
│   │       ├── close_dashboard.py # Close Dashboard tab
│   │       ├── pnl.py            # P&L Reconciliation tab
│   │       ├── ar_aging.py       # AR Aging tab
│   │       ├── variance.py       # Variance Analysis tab
│   │       └── accounting_inbox.py # Accounting Inbox tab
│   ├── sales/
│   │   ├── app.py                 # Sales entrypoint — tab router
│   │   └── tabs/
│   │       ├── __init__.py
│   │       ├── rfp_pipeline.py
│   │       ├── deals.py
│   │       ├── opportunities.py
│   │       ├── prospects.py
│   │       ├── state_profiles.py
│   │       └── inbox.py
│   └── support/
│       ├── app.py                 # Support entrypoint — tab router
│       └── tabs/
│           ├── __init__.py
│           ├── calls_weekly.py
│           ├── calls_by_topic.py
│           ├── calls_by_agent.py
│           └── tickets.py
├── core/
│   ├── __init__.py
│   ├── db.py                      # Supabase connection + cached query functions
│   ├── theme.py                   # B4ALL colors, Plotly template, ECharts theme
│   ├── components.py              # KPI strip, detail panel, data table, filter bar
│   └── charts.py                  # Chart factory functions (area, gauge, donut, etc.)
├── tests/
│   ├── __init__.py
│   ├── test_db.py
│   ├── test_theme.py
│   ├── test_components.py
│   └── test_charts.py
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
├── .gitignore
└── requirements.txt
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.streamlit/config.toml`
- Create: `.streamlit/secrets.toml.example`
- Create: `.gitignore`
- Create: `core/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
streamlit>=1.37
plotly>=5.18
streamlit-echarts>=0.4
psycopg2-binary>=2.9
pandas>=2.1
pytest>=8.0
```

- [ ] **Step 2: Create .streamlit/config.toml**

```toml
[server]
headless = true

[browser]
gatherUsageStats = false

[theme]
backgroundColor = "#F4F6FA"
secondaryBackgroundColor = "#FFFFFF"
textColor = "#0D1B2A"
primaryColor = "#2B7BE9"
font = "sans serif"
```

- [ ] **Step 3: Create .streamlit/secrets.toml.example**

```toml
[connections.supabase]
dialect = "postgresql"
host = "db.dozjdswqnzqwvieqvwpe.supabase.co"
port = 5432
database = "postgres"
username = "postgres"
password = "YOUR_SUPABASE_PASSWORD"
```

- [ ] **Step 4: Create .gitignore**

```
__pycache__/
*.pyc
.streamlit/secrets.toml
.env
.venv/
*.egg-info/
.superpowers/
```

- [ ] **Step 5: Create core/__init__.py and tests/__init__.py**

Both empty files.

- [ ] **Step 6: Install dependencies and verify**

Run: `cd /Users/jackelliott/commandcenter/projects/notion/notion-data-syncing && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
Expected: All packages install successfully.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt .streamlit/config.toml .streamlit/secrets.toml.example .gitignore core/__init__.py tests/__init__.py
git commit -m "chore: scaffold Streamlit dashboard project with deps and config"
```

---

## Task 2: Core — Database Layer

**Files:**
- Create: `core/db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_db.py
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd


def test_query_view_returns_dataframe():
    """query_view should return a pandas DataFrame."""
    mock_conn = MagicMock()
    mock_conn.query.return_value = pd.DataFrame({"col": [1, 2, 3]})

    with patch("core.db._get_connection", return_value=mock_conn):
        from core.db import query_view

        result = query_view("finance_close_dashboard")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3


def test_query_view_builds_correct_sql():
    """query_view should query notion_sync.<view_name>."""
    mock_conn = MagicMock()
    mock_conn.query.return_value = pd.DataFrame()

    with patch("core.db._get_connection", return_value=mock_conn):
        from core.db import query_view

        query_view("finance_pnl")
        call_args = mock_conn.query.call_args
        assert "notion_sync.finance_pnl" in call_args[0][0]


def test_query_view_rejects_dangerous_names():
    """query_view should reject view names with SQL injection attempts."""
    from core.db import query_view

    with pytest.raises(ValueError):
        query_view("finance_pnl; DROP TABLE users")

    with pytest.raises(ValueError):
        query_view("finance_pnl--comment")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/jackelliott/commandcenter/projects/notion/notion-data-syncing && source .venv/bin/activate && python -m pytest tests/test_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.db'`

- [ ] **Step 3: Write core/db.py**

```python
# core/db.py
"""Supabase connection and cached query functions for notion_sync views."""

import re
import streamlit as st
import pandas as pd

# Valid view name pattern — alphanumeric + underscores only
_VIEW_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")

# All known notion_sync views
VIEWS = {
    # Finance
    "finance_close_dashboard",
    "finance_pnl",
    "finance_ar_aging",
    "finance_variance",
    "finance_accounting_inbox",
    # Sales
    "sales_rfp_pipeline",
    "sales_deals",
    "sales_opportunities",
    "sales_prospects",
    "sales_state_profiles",
    "sales_inbox",
    # Support
    "calls_weekly",
    "calls_by_agent",
    "calls_by_topic",
    "calls_log",
    "tickets_log",
    "tickets_monthly",
}


def _get_connection():
    """Get or create the Supabase Postgres connection."""
    return st.connection("supabase", type="sql")


def query_view(view_name: str, ttl: int = 300) -> pd.DataFrame:
    """
    Query a notion_sync view and return a cached DataFrame.

    Args:
        view_name: Name of the view in notion_sync schema (e.g., "finance_pnl")
        ttl: Cache time-to-live in seconds (default 5 minutes)

    Returns:
        pd.DataFrame with the query results
    """
    if not _VIEW_NAME_RE.match(view_name):
        raise ValueError(f"Invalid view name: {view_name}")

    return _cached_query(view_name, ttl)


@st.cache_data(ttl=300, show_spinner=False)
def _cached_query(view_name: str, _ttl: int) -> pd.DataFrame:
    """Cached query execution. The _ttl param is prefixed with _ so Streamlit
    doesn't hash it (the decorator's ttl handles caching)."""
    conn = _get_connection()
    return conn.query(f"SELECT * FROM notion_sync.{view_name}", ttl=_ttl)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/jackelliott/commandcenter/projects/notion/notion-data-syncing && source .venv/bin/activate && python -m pytest tests/test_db.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add core/db.py tests/test_db.py
git commit -m "feat: core database layer with cached notion_sync queries"
```

---

## Task 3: Core — Theme

**Files:**
- Create: `core/theme.py`
- Create: `tests/test_theme.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_theme.py
from core.theme import COLORS, plotly_template, echarts_theme


def test_colors_has_all_brand_colors():
    assert COLORS["navy"] == "#0D1B2A"
    assert COLORS["blue"] == "#2B7BE9"
    assert COLORS["blue_dark"] == "#1A5FC7"
    assert COLORS["blue_light"] == "#E8F1FD"
    assert COLORS["bg"] == "#F4F6FA"
    assert COLORS["white"] == "#FFFFFF"
    assert COLORS["border"] == "#E2E8F0"
    assert COLORS["slate"] == "#64748B"
    assert COLORS["success"] == "#22C55E"
    assert COLORS["warning"] == "#F59E0B"
    assert COLORS["error"] == "#E74C3C"


def test_plotly_template_is_valid():
    tpl = plotly_template()
    assert tpl.layout.paper_bgcolor == "#F4F6FA"
    assert tpl.layout.plot_bgcolor == "#FFFFFF"
    assert tpl.layout.font.color == "#0D1B2A"
    assert tpl.layout.colorway is not None
    assert len(tpl.layout.colorway) >= 5


def test_echarts_theme_has_required_keys():
    theme = echarts_theme()
    assert "color" in theme
    assert "backgroundColor" in theme
    assert theme["backgroundColor"] == "#FFFFFF"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_theme.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write core/theme.py**

```python
# core/theme.py
"""B4ALL brand colors and chart theme configurations."""

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
    "#8B5CF6",  # purple for extra series
    "#EC4899",  # pink for extra series
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_theme.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add core/theme.py tests/test_theme.py
git commit -m "feat: B4ALL brand theme for Plotly and ECharts"
```

---

## Task 4: Core — Components

**Files:**
- Create: `core/components.py`
- Create: `tests/test_components.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_components.py
from core.components import kpi_strip_html, detail_panel_html, status_pill_html


def test_kpi_strip_html_renders_all_items():
    items = [
        {"label": "Revenue", "value": "$412K", "color": "#0D1B2A"},
        {"label": "Margin", "value": "62.4%", "color": "#22C55E"},
    ]
    html = kpi_strip_html(items)
    assert "Revenue" in html
    assert "$412K" in html
    assert "Margin" in html
    assert "62.4%" in html
    assert "#22C55E" in html


def test_kpi_strip_html_handles_subtitle():
    items = [{"label": "Test", "value": "123", "color": "#000", "subtitle": "extra info"}]
    html = kpi_strip_html(items)
    assert "extra info" in html


def test_detail_panel_html_renders_fields():
    fields = {"GL Code": "4110", "GL Name": "Support Revenue", "Delta": "$530"}
    html = detail_panel_html("4110 Support Revenue", fields)
    assert "4110 Support Revenue" in html
    assert "GL Code" in html
    assert "Support Revenue" in html
    assert "$530" in html


def test_status_pill_html_applies_correct_colors():
    html = status_pill_html("PASS", "success")
    assert "#22C55E" in html
    assert "PASS" in html

    html = status_pill_html("FAIL", "error")
    assert "#E74C3C" in html

    html = status_pill_html("WARN", "warning")
    assert "#F59E0B" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_components.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write core/components.py**

```python
# core/components.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_components.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add core/components.py tests/test_components.py
git commit -m "feat: reusable KPI strip, detail panel, and status pill components"
```

---

## Task 5: Core — Charts

**Files:**
- Create: `core/charts.py`
- Create: `tests/test_charts.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_charts.py
import pandas as pd
import plotly.graph_objects as go
from core.charts import (
    area_chart,
    horizontal_bar_chart,
    stacked_bar_chart,
    gauge_chart,
    donut_chart,
    status_bars,
)


def test_area_chart_returns_figure():
    df = pd.DataFrame({
        "month": pd.date_range("2025-06-01", periods=6, freq="MS"),
        "revenue": [100, 110, 105, 120, 130, 125],
        "cogs": [40, 42, 41, 45, 48, 47],
    })
    fig = area_chart(df, x="month", y_cols=["revenue", "cogs"], title="Rev vs COGS")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2
    assert fig.layout.title.text == "Rev vs COGS"


def test_horizontal_bar_chart_returns_figure():
    df = pd.DataFrame({"name": ["A", "B", "C"], "value": [10, 20, 15]})
    fig = horizontal_bar_chart(df, y="name", x="value", title="Test")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1


def test_stacked_bar_chart_returns_figure():
    df = pd.DataFrame({
        "source": ["SAM", "SAM", "OpenGov", "OpenGov"],
        "relevance": ["HIGH", "LOW", "HIGH", "LOW"],
        "count": [9, 23, 1, 54],
    })
    fig = stacked_bar_chart(df, x="source", y="count", color="relevance", title="Test")
    assert isinstance(fig, go.Figure)


def test_gauge_chart_returns_dict():
    config = gauge_chart(value=62.4, title="Gross Margin", suffix="%", min_val=0, max_val=100)
    assert isinstance(config, dict)
    assert "series" in config
    assert config["series"][0]["data"][0]["value"] == 62.4


def test_donut_chart_returns_dict():
    config = donut_chart(labels=["Done", "Blocked"], values=[13, 2], title="Progress")
    assert isinstance(config, dict)
    assert "series" in config
    assert config["series"][0]["type"] == "pie"


def test_status_bars_returns_figure():
    items = [
        {"label": "Cash Recon", "value": 100, "max": 100, "status": "success"},
        {"label": "AR Recon", "value": 85, "max": 100, "status": "warning"},
    ]
    fig = status_bars(items, title="Recon Status")
    assert isinstance(fig, go.Figure)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_charts.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write core/charts.py**

```python
# core/charts.py
"""Chart factory functions for Plotly and ECharts."""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from core.theme import COLORS, COLOR_SEQUENCE, plotly_template


def _apply_template(fig: go.Figure) -> go.Figure:
    """Apply B4ALL template and clean up default Plotly chrome."""
    fig.update_layout(template=plotly_template())
    return fig


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
            fillcolor=f"{COLOR_SEQUENCE[i % len(COLOR_SEQUENCE)]}18" if fill else None,
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
    labels = [item["label"] for item in items]
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_charts.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add core/charts.py tests/test_charts.py
git commit -m "feat: chart factory functions for Plotly and ECharts"
```

---

## Task 6: Finance App — Entrypoint + Close Dashboard Tab

**Files:**
- Create: `apps/finance/app.py`
- Create: `apps/finance/tabs/__init__.py`
- Create: `apps/finance/tabs/close_dashboard.py`

This is the first app and first tab — establishes the pattern for all subsequent tabs.

- [ ] **Step 1: Create apps/finance/tabs/__init__.py**

Empty file.

- [ ] **Step 2: Write apps/finance/tabs/close_dashboard.py**

```python
# apps/finance/tabs/close_dashboard.py
"""Close Dashboard tab — month-end close health, blocking items, reconciliation status."""

import streamlit as st
import pandas as pd
from streamlit_echarts import st_echarts
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html, status_pill_html
from core.charts import area_chart, gauge_chart, donut_chart, status_bars


def render():
    df = query_view("finance_close_dashboard")
    if df.empty:
        st.warning("No close dashboard data available.")
        return

    # Month selector
    months = sorted(df["report_month"].unique(), reverse=True)
    selected_month = st.selectbox("Report Month", months, format_func=lambda x: pd.Timestamp(x).strftime("%B %Y"))
    row = df[df["report_month"] == selected_month].iloc[0]

    # --- KPI Strip ---
    health_color = {"GOOD": COLORS["success"], "WARN": COLORS["warning"], "FAIL": COLORS["error"]}.get(
        row["overall_health"], COLORS["slate"])
    kpis = [
        {"label": "Overall Health", "value": row["overall_health"], "color": health_color},
        {"label": "Gross Margin", "value": f"{row['gross_margin_pct']:.1f}%", "color": COLORS["navy"]},
        {"label": "Revenue", "value": f"${row['total_revenue']:,.0f}", "color": COLORS["navy"]},
        {"label": "Failing", "value": str(row["pnl_accounts_failing"]), "color": COLORS["error"],
         "border_color": COLORS["error"] if row["pnl_accounts_failing"] > 0 else None},
    ]
    st.html(kpi_strip_html(kpis))

    # --- Charts Row 1: Revenue trend + Margin gauge ---
    col1, col2 = st.columns([2, 1])

    with col1:
        # Revenue vs COGS trend (all months)
        trend_df = df.sort_values("report_month")
        fig = area_chart(
            trend_df, x="report_month", y_cols=["total_revenue", "total_cogs"],
            title="Revenue vs COGS Trend", dash_cols=["total_cogs"],
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Gross margin gauge
        st_echarts(
            gauge_chart(float(row["gross_margin_pct"]), "Gross Margin"),
            height="250px",
        )
        # Comparison metrics below gauge
        c1, c2 = st.columns(2)
        if len(df) >= 2:
            prior = df.sort_values("report_month", ascending=False).iloc[1]
            c1.metric("Prior Month", f"{prior['gross_margin_pct']:.1f}%")
        c2.metric("Checklist", f"{row['checklist_pct_complete']:.0f}%")

    # --- Charts Row 2: Close progress donut + Recon status bars ---
    col3, col4 = st.columns(2)

    with col3:
        passing = int(row["pnl_accounts_passing"])
        failing = int(row["pnl_accounts_failing"])
        in_progress = max(0, int(row["pnl_accounts_total"]) - passing - failing)
        st_echarts(
            donut_chart(
                labels=["Passing", "In Progress", "Failing"],
                values=[passing, in_progress, failing],
                title="P&L Account Status",
                colors=[COLORS["success"], COLORS["warning"], COLORS["error"]],
            ),
            height="250px",
        )

    with col4:
        recon_items = [
            {"label": "P&L Accounts", "value": passing, "max": int(row["pnl_accounts_total"]),
             "status": "success" if failing == 0 else "warning"},
            {"label": "Cash Recon", "value": 100 if row["cash_recon_status"] == "PASS" else 50,
             "max": 100, "status": "success" if row["cash_recon_status"] == "PASS" else "warning"},
            {"label": "AR Recon", "value": 100 if "PASS" in str(row["ar_recon_status"]) else 70,
             "max": 100, "status": "success" if "PASS" in str(row["ar_recon_status"]) else "warning"},
            {"label": "Clearing", "value": max(0, 100 - int(row["clearing_open_count"]) * 10),
             "max": 100, "status": "success" if row["clearing_open_count"] == 0 else "warning"},
        ]
        fig = status_bars(recon_items, title="Reconciliation Status")
        st.plotly_chart(fig, use_container_width=True)

    # --- Status Pills ---
    cols = st.columns(4)
    for col, (label, status_val) in zip(cols, [
        ("Cash Recon", row["cash_recon_status"]),
        ("AR Recon", row["ar_recon_status"]),
        ("Clearing", row["clearing_status"]),
        ("Catchall", row["catchall_status"]),
    ]):
        status_type = "success" if "PASS" in str(status_val) or "CLEAN" in str(status_val) else (
            "error" if "FAIL" in str(status_val) else "warning")
        col.html(f'<div style="text-align:center;">'
                 f'<div style="font-size:11px;color:{COLORS["slate"]};margin-bottom:4px;">{label}</div>'
                 f'{status_pill_html(str(status_val), status_type)}</div>')

    # --- Blocking Items Table ---
    if row["blocking_items"] and len(row["blocking_items"]) > 0:
        st.markdown(f"#### Blocking Items")
        for item in row["blocking_items"]:
            with st.expander(f"🔴 {item}", expanded=False):
                # When expanded, show detail panel — in a real drill-down this would
                # query the P&L view for the specific GL code
                st.html(detail_panel_html(str(item), {
                    "Status": "Blocking",
                    "Report Month": str(selected_month),
                    "Action": "Review in P&L Reconciliation tab",
                }))
```

- [ ] **Step 3: Write apps/finance/app.py**

```python
# apps/finance/app.py
"""B4ALL Finance Dashboard — Streamlit entrypoint."""

import sys
from pathlib import Path

# Add project root to path so core/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

st.set_page_config(
    page_title="B4ALL Finance Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide sidebar and Streamlit chrome for clean Notion embed
st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stHeader"] { display: none; }
    .block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

st.markdown(f'<h1 style="color:#0D1B2A;margin-bottom:0;">Finance Dashboard</h1>', unsafe_allow_html=True)

# Tab router
tab_close, tab_pnl, tab_ar, tab_variance, tab_inbox = st.tabs([
    "Close Dashboard", "P&L Reconciliation", "AR Aging", "Variance Analysis", "Accounting Inbox",
])

with tab_close:
    from apps.finance.tabs.close_dashboard import render as render_close
    render_close()

with tab_pnl:
    st.info("P&L Reconciliation — coming next task")

with tab_ar:
    st.info("AR Aging — coming soon")

with tab_variance:
    st.info("Variance Analysis — coming soon")

with tab_inbox:
    st.info("Accounting Inbox — coming soon")
```

- [ ] **Step 4: Create .streamlit/secrets.toml with real connection**

The implementing agent should ask the user for the Supabase direct connection password and write it to `.streamlit/secrets.toml`:

```toml
[connections.supabase]
dialect = "postgresql"
host = "db.dozjdswqnzqwvieqvwpe.supabase.co"
port = 5432
database = "postgres"
username = "postgres"
password = "<ASK USER FOR PASSWORD>"
```

- [ ] **Step 5: Test locally**

Run: `cd /Users/jackelliott/commandcenter/projects/notion/notion-data-syncing && source .venv/bin/activate && streamlit run apps/finance/app.py`
Expected: App opens in browser, Close Dashboard tab renders with live data from Supabase.

- [ ] **Step 6: Commit**

```bash
git add apps/finance/app.py apps/finance/tabs/__init__.py apps/finance/tabs/close_dashboard.py
git commit -m "feat: Finance Dashboard entrypoint + Close Dashboard tab with charts"
```

---

## Task 7: Finance — P&L Reconciliation Tab

**Files:**
- Create: `apps/finance/tabs/pnl.py`
- Modify: `apps/finance/app.py` (replace placeholder import)

- [ ] **Step 1: Write apps/finance/tabs/pnl.py**

```python
# apps/finance/tabs/pnl.py
"""P&L Reconciliation tab — GL-level Hub vs QB comparison with delta charts."""

import streamlit as st
import pandas as pd
from streamlit_echarts import st_echarts
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html
from core.charts import horizontal_bar_chart, donut_chart


def render():
    df = query_view("finance_pnl")
    if df.empty:
        st.warning("No P&L data available.")
        return

    # Period selector
    periods = sorted(df["period_start"].unique(), reverse=True)
    selected_period = st.selectbox("Period", periods,
                                   format_func=lambda x: pd.Timestamp(x).strftime("%B %Y"),
                                   key="pnl_period")
    period_df = df[df["period_start"] == selected_period].copy()

    # KPIs
    total = len(period_df)
    passing = len(period_df[period_df["status"] == "PASS"])
    failing = total - passing
    total_delta = period_df["delta"].abs().sum()
    kpis = [
        {"label": "Total Accounts", "value": str(total), "color": COLORS["navy"]},
        {"label": "Passing", "value": str(passing), "color": COLORS["success"]},
        {"label": "Failing", "value": str(failing), "color": COLORS["error"],
         "border_color": COLORS["error"] if failing > 0 else None},
        {"label": "Total |Δ|", "value": f"${total_delta:,.0f}", "color": COLORS["warning"]},
    ]
    st.html(kpi_strip_html(kpis))

    # Charts row
    col1, col2 = st.columns([2, 1])

    with col1:
        # Horizontal bar of deltas sorted by absolute value
        chart_df = period_df[period_df["delta"] != 0].copy()
        chart_df["abs_delta"] = chart_df["delta"].abs()
        chart_df = chart_df.sort_values("abs_delta", ascending=False).head(15)
        chart_df["label"] = chart_df["gl_code"] + " " + chart_df["gl_name"]
        color_map = {True: COLORS["error"], False: COLORS["warning"]}
        chart_df["is_negative"] = chart_df["delta"] < 0
        fig = horizontal_bar_chart(chart_df, y="label", x="abs_delta",
                                   title="Top Deltas by GL Account (|Hub − QB|)")
        # Color bars by sign
        fig.data[0].marker.color = [COLORS["error"] if d < 0 else COLORS["warning"]
                                     for d in chart_df["delta"]]
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st_echarts(
            donut_chart(
                labels=["Passing", "Failing"],
                values=[passing, failing],
                title="Account Status",
                colors=[COLORS["success"], COLORS["error"]],
            ),
            height="250px",
        )

    # Data table with row selection
    st.markdown("#### All Accounts")
    display_df = period_df[["gl_code", "gl_name", "pl_section", "hub_total", "qb_total", "delta", "status"]].copy()
    display_df.columns = ["GL Code", "GL Name", "Section", "Hub Total", "QB Total", "Delta", "Status"]

    # Filter by status
    status_filter = st.radio("Filter", ["All", "Failing Only", "Passing Only"], horizontal=True, key="pnl_filter")
    if status_filter == "Failing Only":
        display_df = display_df[display_df["Status"] != "PASS"]
    elif status_filter == "Passing Only":
        display_df = display_df[display_df["Status"] == "PASS"]

    event = st.dataframe(display_df, use_container_width=True, hide_index=True,
                         on_select="rerun", selection_mode="single-row")

    # Detail panel on row selection
    if event and event.selection and event.selection.rows:
        idx = event.selection.rows[0]
        selected = period_df.iloc[idx]
        st.html(detail_panel_html(
            f"{selected['gl_code']} {selected['gl_name']}",
            {
                "P&L Section": selected["pl_section"],
                "Hub Total": f"${selected['hub_total']:,.2f}",
                "QB Total": f"${selected['qb_total']:,.2f}",
                "Delta": f"${selected['delta']:,.2f}",
                "Status": selected["status"],
                "Source View": selected["source_view"],
                "Note": selected["note"] or "—",
            },
        ))
```

- [ ] **Step 2: Update apps/finance/app.py — replace P&L placeholder**

Replace the placeholder block:

```python
with tab_pnl:
    st.info("P&L Reconciliation — coming next task")
```

With:

```python
with tab_pnl:
    from apps.finance.tabs.pnl import render as render_pnl
    render_pnl()
```

- [ ] **Step 3: Test locally**

Run: `streamlit run apps/finance/app.py`
Expected: P&L Reconciliation tab renders with delta bar chart, donut, filterable table, and row detail panel.

- [ ] **Step 4: Commit**

```bash
git add apps/finance/tabs/pnl.py apps/finance/app.py
git commit -m "feat: P&L Reconciliation tab with delta charts and row detail"
```

---

## Task 8: Finance — AR Aging Tab

**Files:**
- Create: `apps/finance/tabs/ar_aging.py`
- Modify: `apps/finance/app.py` (replace placeholder)

- [ ] **Step 1: Write apps/finance/tabs/ar_aging.py**

```python
# apps/finance/tabs/ar_aging.py
"""AR Aging tab — invoice-level aging with bucket charts and drill-down."""

import streamlit as st
import pandas as pd
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html
from core.charts import stacked_bar_chart, horizontal_bar_chart


BUCKET_ORDER = ["Current", "1-30", "31-60", "61-90", "91-120", "120+"]
BUCKET_COLORS = {
    "Current": COLORS["success"], "1-30": COLORS["blue"],
    "31-60": COLORS["warning"], "61-90": "#F97316",
    "91-120": COLORS["error"], "120+": "#991B1B",
}


def render():
    df = query_view("finance_ar_aging")
    if df.empty:
        st.warning("No AR aging data available.")
        return

    # KPIs
    total_ar = df["amount_due"].sum()
    bucket_totals = df.groupby("aging_bucket")["amount_due"].sum()
    kpis = [
        {"label": "Total AR", "value": f"${total_ar:,.0f}", "color": COLORS["navy"]},
        {"label": "Current", "value": f"${bucket_totals.get('Current', 0):,.0f}", "color": COLORS["success"]},
        {"label": "31-60 Days", "value": f"${bucket_totals.get('31-60', 0):,.0f}", "color": COLORS["warning"]},
        {"label": "90+ Days", "value": f"${bucket_totals.get('91-120', 0) + bucket_totals.get('120+', 0):,.0f}",
         "color": COLORS["error"], "border_color": COLORS["error"]},
    ]
    st.html(kpi_strip_html(kpis))

    # Charts row
    col1, col2 = st.columns([1, 1])

    with col1:
        # Stacked bar by aging bucket
        bucket_df = df.groupby("aging_bucket")["amount_due"].agg(["sum", "count"]).reset_index()
        bucket_df.columns = ["Bucket", "Amount", "Invoices"]
        # Ensure correct order
        bucket_df["sort_key"] = bucket_df["Bucket"].map({b: i for i, b in enumerate(BUCKET_ORDER)})
        bucket_df = bucket_df.sort_values("sort_key")
        fig = horizontal_bar_chart(bucket_df, y="Bucket", x="Amount", title="AR by Aging Bucket")
        fig.data[0].marker.color = [BUCKET_COLORS.get(b, COLORS["slate"]) for b in bucket_df["Bucket"]]
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Top 10 overdue invoices
        overdue = df[df["days_outstanding"] > 30].nlargest(10, "amount_due").copy()
        if not overdue.empty:
            overdue["label"] = overdue["client_id"].fillna("Unknown") + " — " + overdue["invoice_number"].fillna("")
            fig = horizontal_bar_chart(overdue, y="label", x="amount_due", title="Top 10 Overdue Invoices")
            fig.data[0].marker.color = [BUCKET_COLORS.get(b, COLORS["slate"]) for b in overdue["aging_bucket"]]
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("No overdue invoices!")

    # Filterable table
    st.markdown("#### All Invoices")
    bucket_filter = st.multiselect("Filter by Bucket", BUCKET_ORDER, default=BUCKET_ORDER, key="ar_bucket_filter")
    filtered = df[df["aging_bucket"].isin(bucket_filter)].copy()
    display_df = filtered[["client_id", "invoice_number", "invoice_date", "due_date",
                           "amount_due", "days_outstanding", "aging_bucket"]].copy()
    display_df.columns = ["Client", "Invoice #", "Invoice Date", "Due Date", "Amount", "Days Out", "Bucket"]

    event = st.dataframe(display_df.sort_values("Days Out", ascending=False),
                         use_container_width=True, hide_index=True,
                         on_select="rerun", selection_mode="single-row")

    if event and event.selection and event.selection.rows:
        idx = event.selection.rows[0]
        selected = filtered.iloc[idx]
        st.html(detail_panel_html(
            f"Invoice {selected['invoice_number']}",
            {
                "Client ID": selected["client_id"] or "—",
                "Invoice Date": str(selected["invoice_date"]),
                "Due Date": str(selected["due_date"]),
                "Amount Due": f"${selected['amount_due']:,.2f}",
                "Days Outstanding": str(selected["days_outstanding"]),
                "Aging Bucket": selected["aging_bucket"],
                "Report Month": str(selected["report_month"]),
            },
        ))
```

- [ ] **Step 2: Update apps/finance/app.py — replace AR placeholder**

```python
with tab_ar:
    from apps.finance.tabs.ar_aging import render as render_ar
    render_ar()
```

- [ ] **Step 3: Test locally and commit**

```bash
git add apps/finance/tabs/ar_aging.py apps/finance/app.py
git commit -m "feat: AR Aging tab with bucket charts and invoice drill-down"
```

---

## Task 9: Finance — Variance Analysis Tab

**Files:**
- Create: `apps/finance/tabs/variance.py`
- Modify: `apps/finance/app.py` (replace placeholder)

- [ ] **Step 1: Write apps/finance/tabs/variance.py**

```python
# apps/finance/tabs/variance.py
"""Variance Analysis tab — MoM/YoY variance heatmap with flagged account drill-down."""

import streamlit as st
import pandas as pd
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html
from core.charts import heatmap_chart, horizontal_bar_chart


def render():
    df = query_view("finance_variance")
    if df.empty:
        st.warning("No variance data available.")
        return

    # Latest month for KPIs
    latest_month = df["report_month"].max()
    latest = df[df["report_month"] == latest_month]

    flagged = latest[latest["variance_flag"].notna() & (latest["variance_flag"] != "")]
    largest_mom = latest.loc[latest["mom_change"].abs().idxmax()] if not latest.empty else None
    largest_yoy = latest.loc[latest["yoy_change"].abs().idxmax()] if not latest.empty else None

    kpis = [
        {"label": "Flagged Accounts", "value": str(len(flagged)), "color": COLORS["error"] if len(flagged) > 0 else COLORS["success"],
         "border_color": COLORS["error"] if len(flagged) > 0 else None},
        {"label": "Largest MoM Swing", "value": f"${largest_mom['mom_change']:,.0f}" if largest_mom is not None else "—",
         "color": COLORS["navy"], "subtitle": f"{largest_mom['gl_code']} {largest_mom['gl_name']}" if largest_mom is not None else ""},
        {"label": "Largest YoY Swing", "value": f"${largest_yoy['yoy_change']:,.0f}" if largest_yoy is not None else "—",
         "color": COLORS["navy"], "subtitle": f"{largest_yoy['gl_code']} {largest_yoy['gl_name']}" if largest_yoy is not None else ""},
    ]
    st.html(kpi_strip_html(kpis))

    # Charts
    col1, col2 = st.columns([2, 1])

    with col1:
        # Heatmap of MoM % change by GL × month
        heatmap_df = df[df["mom_pct_change"].notna()].copy()
        heatmap_df["gl_label"] = heatmap_df["gl_code"] + " " + heatmap_df["gl_name"]
        heatmap_df["month_label"] = pd.to_datetime(heatmap_df["report_month"]).dt.strftime("%b %Y")
        if not heatmap_df.empty:
            fig = heatmap_chart(heatmap_df, x="month_label", y="gl_label", z="mom_pct_change",
                                title="MoM % Change Heatmap")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Flagged accounts bar
        if not flagged.empty:
            flag_df = flagged.copy()
            flag_df["label"] = flag_df["gl_code"] + " " + flag_df["gl_name"]
            flag_df["abs_mom"] = flag_df["mom_change"].abs()
            fig = horizontal_bar_chart(flag_df, y="label", x="abs_mom", title="Flagged — |MoM Change|")
            fig.data[0].marker.color = COLORS["error"]
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("No flagged variances this month!")

    # Data table
    st.markdown("#### Variance Detail")
    section_filter = st.multiselect("P&L Section", df["pl_section"].dropna().unique().tolist(), key="var_section")
    table_df = latest.copy()
    if section_filter:
        table_df = table_df[table_df["pl_section"].isin(section_filter)]

    display_df = table_df[["gl_code", "gl_name", "pl_section", "current_month_actual",
                           "mom_change", "mom_pct_change", "yoy_change", "yoy_pct_change",
                           "avg_6mo", "variance_flag"]].copy()
    display_df.columns = ["GL", "Name", "Section", "Current", "MoM Δ", "MoM %", "YoY Δ", "YoY %", "6mo Avg", "Flag"]

    event = st.dataframe(display_df, use_container_width=True, hide_index=True,
                         on_select="rerun", selection_mode="single-row")

    if event and event.selection and event.selection.rows:
        idx = event.selection.rows[0]
        sel = table_df.iloc[idx]
        st.html(detail_panel_html(
            f"{sel['gl_code']} {sel['gl_name']}",
            {
                "P&L Section": sel["pl_section"],
                "Current Month": f"${sel['current_month_actual']:,.2f}",
                "Prior Month": f"${sel['prior_month_actual']:,.2f}",
                "MoM Change": f"${sel['mom_change']:,.2f} ({sel['mom_pct_change']:.1f}%)" if pd.notna(sel["mom_pct_change"]) else "—",
                "YTD Actual": f"${sel['ytd_actual']:,.2f}",
                "Prior YTD": f"${sel['prior_ytd_actual']:,.2f}" if pd.notna(sel["prior_ytd_actual"]) else "—",
                "YoY Change": f"${sel['yoy_change']:,.2f} ({sel['yoy_pct_change']:.1f}%)" if pd.notna(sel["yoy_pct_change"]) else "—",
                "6-Month Avg": f"${sel['avg_6mo']:,.2f}" if pd.notna(sel["avg_6mo"]) else "—",
                "Variance Flag": sel["variance_flag"] or "None",
            },
        ))
```

- [ ] **Step 2: Update apps/finance/app.py — replace variance placeholder**

```python
with tab_variance:
    from apps.finance.tabs.variance import render as render_variance
    render_variance()
```

- [ ] **Step 3: Test locally and commit**

```bash
git add apps/finance/tabs/variance.py apps/finance/app.py
git commit -m "feat: Variance Analysis tab with heatmap and flagged account drill-down"
```

---

## Task 10: Finance — Accounting Inbox Tab

**Files:**
- Create: `apps/finance/tabs/accounting_inbox.py`
- Modify: `apps/finance/app.py` (replace placeholder)

- [ ] **Step 1: Write apps/finance/tabs/accounting_inbox.py**

```python
# apps/finance/tabs/accounting_inbox.py
"""Accounting Inbox tab — email handle rates, reply rates, response times."""

import streamlit as st
import pandas as pd
from streamlit_echarts import st_echarts
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html
from core.charts import area_chart, gauge_chart, stacked_bar_chart


def render():
    df = query_view("finance_accounting_inbox")
    if df.empty:
        st.warning("No accounting inbox data available.")
        return

    # Build date column for charting
    df["month_date"] = pd.to_datetime(df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2) + "-01")

    # Latest month aggregates for KPIs
    latest_month = df["month_date"].max()
    latest = df[df["month_date"] == latest_month]
    total_emails = latest["total_emails"].sum()
    total_replied = latest["replied"].sum()
    reply_rate = (total_replied / total_emails * 100) if total_emails > 0 else 0
    avg_response = latest["avg_response_min"].mean()
    unique_cust = latest["unique_customers"].sum()

    kpis = [
        {"label": "Total Emails", "value": f"{total_emails:,}", "color": COLORS["navy"]},
        {"label": "Reply Rate", "value": f"{reply_rate:.1f}%", "color": COLORS["success"] if reply_rate > 80 else COLORS["warning"]},
        {"label": "Avg Response", "value": f"{avg_response:.0f} min", "color": COLORS["navy"]},
        {"label": "Unique Customers", "value": f"{unique_cust:,}", "color": COLORS["navy"]},
    ]
    st.html(kpi_strip_html(kpis))

    # Charts
    col1, col2 = st.columns([2, 1])

    with col1:
        # Monthly volume trend by classification
        trend = df.groupby(["month_date", "email_classification"])["total_emails"].sum().reset_index()
        classifications = trend["email_classification"].unique()
        pivot = trend.pivot(index="month_date", columns="email_classification", values="total_emails").fillna(0).reset_index()
        fig = area_chart(pivot, x="month_date", y_cols=[c for c in classifications if c in pivot.columns],
                         title="Email Volume by Classification", fill=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Reply rate gauge
        st_echarts(
            gauge_chart(reply_rate, "Reply Rate", suffix="%"),
            height="250px",
        )

    # Response time distribution
    if latest["avg_response_min"].notna().any():
        response_df = latest[latest["avg_response_min"].notna()][["folder_category", "avg_response_min", "median_response_min"]].copy()
        if not response_df.empty:
            fig = area_chart(
                response_df.sort_values("avg_response_min"),
                x="folder_category", y_cols=["avg_response_min", "median_response_min"],
                title="Response Time by Folder (min)", fill=False,
            )
            st.plotly_chart(fig, use_container_width=True)

    # Data table
    st.markdown("#### Monthly Breakdown")
    display_df = df[["month_date", "email_classification", "folder_category", "total_emails",
                     "inbound", "outbound", "replied", "reply_rate_pct",
                     "avg_response_min", "conversations"]].copy()
    display_df.columns = ["Month", "Classification", "Folder", "Total", "In", "Out",
                          "Replied", "Reply %", "Avg Resp (min)", "Conversations"]
    display_df = display_df.sort_values(["Month", "Classification"], ascending=[False, True])

    event = st.dataframe(display_df, use_container_width=True, hide_index=True,
                         on_select="rerun", selection_mode="single-row")

    if event and event.selection and event.selection.rows:
        idx = event.selection.rows[0]
        sel = df.iloc[idx]
        st.html(detail_panel_html(
            f"{sel['email_classification']} — {sel['folder_category']}",
            {
                "Period": f"{sel['year']}-{sel['month']:02d}",
                "Total Emails": f"{sel['total_emails']:,}",
                "Inbound": f"{sel['inbound']:,}",
                "Outbound": f"{sel['outbound']:,}",
                "Internal": f"{sel['internal']:,}",
                "Replied": f"{sel['replied']:,}",
                "Reply Rate": f"{sel['reply_rate_pct']:.1f}%",
                "Avg Response (min)": f"{sel['avg_response_min']:.1f}" if pd.notna(sel["avg_response_min"]) else "—",
                "Median Response (min)": f"{sel['median_response_min']:.1f}" if pd.notna(sel["median_response_min"]) else "—",
                "Conversations": f"{sel['conversations']:,}",
                "Avg Thread Depth": f"{sel['avg_thread_depth']:.1f}" if pd.notna(sel["avg_thread_depth"]) else "—",
                "With Attachments": f"{sel['with_attachments']:,}",
            },
        ))
```

- [ ] **Step 2: Update apps/finance/app.py — replace inbox placeholder**

```python
with tab_inbox:
    from apps.finance.tabs.accounting_inbox import render as render_inbox
    render_inbox()
```

- [ ] **Step 3: Test locally and commit**

```bash
git add apps/finance/tabs/accounting_inbox.py apps/finance/app.py
git commit -m "feat: Accounting Inbox tab with volume trends and reply rate gauge"
```

---

## Task 11: Sales App — Entrypoint + RFP Pipeline Tab

**Files:**
- Create: `apps/sales/app.py`
- Create: `apps/sales/tabs/__init__.py`
- Create: `apps/sales/tabs/rfp_pipeline.py`

- [ ] **Step 1: Create apps/sales/tabs/__init__.py**

Empty file.

- [ ] **Step 2: Write apps/sales/tabs/rfp_pipeline.py**

```python
# apps/sales/tabs/rfp_pipeline.py
"""RFP Pipeline tab — trailing 30-day procurement opportunities by source and relevance."""

import streamlit as st
import pandas as pd
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html
from core.charts import stacked_bar_chart, scatter_timeline

RELEVANCE_COLORS = {"HIGH": COLORS["error"], "MEDIUM": COLORS["warning"], "LOW": COLORS["slate"]}


def render():
    df = query_view("sales_rfp_pipeline")
    if df.empty:
        st.warning("No RFP pipeline data available.")
        return

    # KPIs
    high = len(df[df["relevance"] == "HIGH"])
    medium = len(df[df["relevance"] == "MEDIUM"])
    low = len(df[df["relevance"] == "LOW"])
    total_amount = df["amount"].sum()

    kpis = [
        {"label": "Total RFPs (30d)", "value": str(len(df)), "color": COLORS["navy"]},
        {"label": "HIGH", "value": str(high), "color": COLORS["error"], "border_color": COLORS["error"]},
        {"label": "MEDIUM", "value": str(medium), "color": COLORS["warning"]},
        {"label": "Total Value", "value": f"${total_amount:,.0f}" if pd.notna(total_amount) else "—", "color": COLORS["navy"]},
    ]
    st.html(kpi_strip_html(kpis))

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        # Stacked bar by source × relevance
        count_df = df.groupby(["source", "relevance"]).size().reset_index(name="count")
        fig = stacked_bar_chart(count_df, x="source", y="count", color="relevance",
                                title="RFPs by Source × Relevance", color_map=RELEVANCE_COLORS)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Timeline scatter — due_date on x, source on y, bubble size = amount
        scatter_df = df[df["due_date"].notna()].copy()
        if not scatter_df.empty:
            scatter_df["amount_display"] = scatter_df["amount"].fillna(1)
            fig = scatter_timeline(scatter_df, x="due_date", y="source", size="amount_display",
                                   color="relevance", title="Deadlines by Source",
                                   color_map=RELEVANCE_COLORS)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No deadlines available for scatter view.")

    # Data table
    st.markdown("#### All Opportunities")
    relevance_filter = st.multiselect("Relevance", ["HIGH", "MEDIUM", "LOW"],
                                      default=["HIGH", "MEDIUM"], key="rfp_rel_filter")
    filtered = df[df["relevance"].isin(relevance_filter)] if relevance_filter else df

    display_df = filtered[["title", "agency", "source", "state", "relevance",
                           "posted_date", "due_date", "amount", "status"]].copy()
    display_df.columns = ["Title", "Agency", "Source", "State", "Relevance",
                          "Posted", "Deadline", "Amount", "Status"]

    event = st.dataframe(display_df, use_container_width=True, hide_index=True,
                         on_select="rerun", selection_mode="single-row")

    if event and event.selection and event.selection.rows:
        idx = event.selection.rows[0]
        sel = filtered.iloc[idx]
        fields = {
            "Source": sel["source"],
            "Record Type": sel["record_type"],
            "Solicitation ID": sel["solicitation_id"] or "—",
            "Agency": sel["agency"] or "—",
            "State": sel["state"] or "—",
            "Procurer Level": sel["procurer_level"],
            "Posted": str(sel["posted_date"]),
            "Deadline": str(sel["due_date"]) if pd.notna(sel["due_date"]) else "—",
            "Amount": f"${sel['amount']:,.0f}" if pd.notna(sel["amount"]) else "—",
            "Status": sel["status"] or "—",
            "Relevance": sel["relevance"],
        }
        if sel["source_url"]:
            fields["Source URL"] = sel["source_url"]
        st.html(detail_panel_html(sel["title"][:80], fields))
```

- [ ] **Step 3: Write apps/sales/app.py**

```python
# apps/sales/app.py
"""B4ALL Sales Dashboard — Streamlit entrypoint."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

st.set_page_config(page_title="B4ALL Sales Dashboard", page_icon="📈", layout="wide",
                   initial_sidebar_state="collapsed")

st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stHeader"] { display: none; }
    .block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 style="color:#0D1B2A;margin-bottom:0;">Sales Dashboard</h1>', unsafe_allow_html=True)

tab_rfp, tab_deals, tab_opps, tab_prospects, tab_states, tab_inbox = st.tabs([
    "RFP Pipeline", "Deals", "Opportunities", "Prospects", "State Profiles", "Inbox",
])

with tab_rfp:
    from apps.sales.tabs.rfp_pipeline import render as render_rfp
    render_rfp()

with tab_deals:
    st.info("Deals — coming next task")

with tab_opps:
    st.info("Opportunities — coming soon")

with tab_prospects:
    st.info("Prospects — coming soon")

with tab_states:
    st.info("State Profiles — coming soon")

with tab_inbox:
    st.info("Inbox — coming soon")
```

- [ ] **Step 4: Test locally and commit**

```bash
git add apps/sales/app.py apps/sales/tabs/__init__.py apps/sales/tabs/rfp_pipeline.py
git commit -m "feat: Sales Dashboard entrypoint + RFP Pipeline tab"
```

---

## Task 12: Sales — Deals Tab

**Files:**
- Create: `apps/sales/tabs/deals.py`
- Modify: `apps/sales/app.py`

- [ ] **Step 1: Write apps/sales/tabs/deals.py**

```python
# apps/sales/tabs/deals.py
"""Deals tab — pipeline funnel, deal value charts, stage drill-down."""

import streamlit as st
import pandas as pd
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html
from core.charts import funnel_chart, stacked_bar_chart


def render():
    df = query_view("sales_deals")
    if df.empty:
        st.warning("No deals data available.")
        return

    # KPIs
    total_deals = len(df)
    open_deals = len(df[~df["is_closed_won"] & ~df["is_closed_lost"]])
    won = len(df[df["is_closed_won"]])
    total_value = df[~df["is_closed_lost"]]["amount"].sum()

    kpis = [
        {"label": "Total Deals", "value": str(total_deals), "color": COLORS["navy"]},
        {"label": "Open", "value": str(open_deals), "color": COLORS["blue"]},
        {"label": "Won", "value": str(won), "color": COLORS["success"]},
        {"label": "Pipeline Value", "value": f"${total_value:,.0f}" if pd.notna(total_value) else "—", "color": COLORS["navy"]},
    ]
    st.html(kpi_strip_html(kpis))

    col1, col2 = st.columns(2)

    with col1:
        # Funnel by stage
        stage_counts = df.groupby("deal_stage").size().reset_index(name="count")
        stage_counts = stage_counts.sort_values("count", ascending=False)
        fig = funnel_chart(stage_counts, stage="deal_stage", value="count", title="Deal Funnel by Stage")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Value by pipeline
        pipeline_val = df.groupby("pipeline")["amount"].sum().reset_index()
        pipeline_val = pipeline_val.sort_values("amount", ascending=False)
        if not pipeline_val.empty:
            from core.charts import horizontal_bar_chart
            fig = horizontal_bar_chart(pipeline_val, y="pipeline", x="amount", title="Deal Value by Pipeline")
            st.plotly_chart(fig, use_container_width=True)

    # Data table
    st.markdown("#### All Deals")
    pipeline_filter = st.multiselect("Pipeline", df["pipeline"].dropna().unique().tolist(), key="deals_pipeline")
    filtered = df[df["pipeline"].isin(pipeline_filter)] if pipeline_filter else df

    display_df = filtered[["deal_name", "deal_stage", "pipeline", "amount", "close_date",
                           "days_in_pipeline", "customer_name"]].copy()
    display_df.columns = ["Deal", "Stage", "Pipeline", "Amount", "Close Date", "Days in Pipeline", "Customer"]

    event = st.dataframe(display_df.sort_values("Amount", ascending=False),
                         use_container_width=True, hide_index=True,
                         on_select="rerun", selection_mode="single-row")

    if event and event.selection and event.selection.rows:
        idx = event.selection.rows[0]
        sel = filtered.iloc[idx]
        st.html(detail_panel_html(
            sel["deal_name"][:80],
            {
                "Stage": sel["deal_stage"],
                "Pipeline": sel["pipeline"],
                "Amount": f"${sel['amount']:,.2f}" if pd.notna(sel["amount"]) else "—",
                "Close Date": str(sel["close_date"]) if pd.notna(sel["close_date"]) else "—",
                "Days in Pipeline": str(sel["days_in_pipeline"]),
                "Customer": sel["customer_name"] or "—",
                "Client ID": sel["client_id"] or "—",
                "Source": sel["deal_source"] or "—",
                "Agent": sel["agent_name"] or "—",
                "Status": "Won" if sel["is_closed_won"] else ("Lost" if sel["is_closed_lost"] else "Open"),
            },
        ))
```

- [ ] **Step 2: Update apps/sales/app.py**

Replace `st.info("Deals — coming next task")` with:

```python
    from apps.sales.tabs.deals import render as render_deals
    render_deals()
```

- [ ] **Step 3: Test and commit**

```bash
git add apps/sales/tabs/deals.py apps/sales/app.py
git commit -m "feat: Sales Deals tab with funnel and pipeline value charts"
```

---

## Task 13: Sales — Opportunities Tab

**Files:**
- Create: `apps/sales/tabs/opportunities.py`
- Modify: `apps/sales/app.py`

- [ ] **Step 1: Write apps/sales/tabs/opportunities.py**

```python
# apps/sales/tabs/opportunities.py
"""Opportunities tab — gov bids, recompetes, federal unified view."""

import streamlit as st
import pandas as pd
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html
from core.charts import heatmap_chart, stacked_bar_chart


def render():
    df = query_view("sales_opportunities")
    if df.empty:
        st.warning("No opportunities data available.")
        return

    kpis = [
        {"label": "Total", "value": str(len(df)), "color": COLORS["navy"]},
        {"label": "Gov Bids", "value": str(len(df[df["source_type"] == "gov_bid"])), "color": COLORS["blue"]},
        {"label": "Recompetes", "value": str(len(df[df["source_type"] == "recompete"])), "color": COLORS["blue_dark"]},
        {"label": "Federal", "value": str(len(df[df["source_type"] == "federal"])), "color": COLORS["success"]},
    ]
    st.html(kpi_strip_html(kpis))

    col1, col2 = st.columns(2)

    with col1:
        # Heatmap: source_type × urgency_tier
        heat_df = df.groupby(["source_type", "urgency_tier"]).size().reset_index(name="count")
        if not heat_df.empty:
            fig = heatmap_chart(heat_df, x="urgency_tier", y="source_type", z="count",
                                title="Opportunities: Source × Urgency")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Stacked bar by source
        count_df = df.groupby(["source_type", "urgency_tier"]).size().reset_index(name="count")
        fig = stacked_bar_chart(count_df, x="source_type", y="count", color="urgency_tier",
                                title="Volume by Source")
        st.plotly_chart(fig, use_container_width=True)

    # Table
    st.markdown("#### All Opportunities")
    source_filter = st.multiselect("Source", df["source_type"].unique().tolist(), key="opp_source")
    filtered = df[df["source_type"].isin(source_filter)] if source_filter else df

    display_df = filtered[["title", "source_type", "agency", "state", "relevance",
                           "urgency_tier", "date_posted", "deadline", "amount"]].copy()
    display_df.columns = ["Title", "Source", "Agency", "State", "Relevance",
                          "Urgency", "Posted", "Deadline", "Amount"]

    event = st.dataframe(display_df, use_container_width=True, hide_index=True,
                         on_select="rerun", selection_mode="single-row")

    if event and event.selection and event.selection.rows:
        idx = event.selection.rows[0]
        sel = filtered.iloc[idx]
        fields = {
            "Source Type": sel["source_type"],
            "Agency": sel["agency"] or "—",
            "State": sel["state"] or "—",
            "Relevance": sel["relevance"] or "—",
            "Urgency": sel["urgency_tier"] or "—",
            "Posted": str(sel["date_posted"]) if pd.notna(sel["date_posted"]) else "—",
            "Deadline": str(sel["deadline"]) if pd.notna(sel["deadline"]) else "—",
            "Amount": f"${sel['amount']:,.0f}" if pd.notna(sel["amount"]) else "—",
        }
        if sel.get("source_url"):
            fields["URL"] = sel["source_url"]
        if sel.get("description"):
            fields["Description"] = str(sel["description"])[:200]
        st.html(detail_panel_html(sel["title"][:80], fields))
```

- [ ] **Step 2: Update app.py, test, commit**

Replace placeholder, then:

```bash
git add apps/sales/tabs/opportunities.py apps/sales/app.py
git commit -m "feat: Sales Opportunities tab with heatmap and source breakdown"
```

---

## Task 14: Sales — Prospects Tab

**Files:**
- Create: `apps/sales/tabs/prospects.py`
- Modify: `apps/sales/app.py`

- [ ] **Step 1: Write apps/sales/tabs/prospects.py**

```python
# apps/sales/tabs/prospects.py
"""Prospects tab — scored prospect database with treemap and score distribution."""

import streamlit as st
import pandas as pd
import plotly.express as px
from core.db import query_view
from core.theme import COLORS, COLOR_SEQUENCE, plotly_template
from core.components import kpi_strip_html, detail_panel_html
from core.charts import treemap_chart


def render():
    df = query_view("sales_prospects")
    if df.empty:
        st.warning("No prospect data available.")
        return

    total_rev = df["est_annual_revenue"].sum()
    kpis = [
        {"label": "Total Prospects", "value": f"{len(df):,}", "color": COLORS["navy"]},
        {"label": "Tier 1A", "value": str(len(df[df["priority_tier"] == "1A"])), "color": COLORS["error"],
         "border_color": COLORS["error"]},
        {"label": "States Covered", "value": str(df["state_abbr"].nunique()), "color": COLORS["blue"]},
        {"label": "Est. Annual Rev", "value": f"${total_rev:,.0f}" if pd.notna(total_rev) else "—", "color": COLORS["navy"]},
    ]
    st.html(kpi_strip_html(kpis))

    col1, col2 = st.columns(2)

    with col1:
        # Treemap: state → priority_tier
        tree_df = df.groupby(["state_abbr", "priority_tier"]).agg(
            count=("entity_name", "size"),
            est_rev=("est_annual_revenue", "sum"),
        ).reset_index()
        fig = treemap_chart(tree_df, path=["state_abbr", "priority_tier"], values="count",
                            title="Prospects by State × Priority Tier")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Score distribution histogram
        fig = px.histogram(df, x="priority_score", nbins=30, title="Priority Score Distribution",
                           color_discrete_sequence=[COLORS["blue"]])
        fig.update_layout(template=plotly_template())
        st.plotly_chart(fig, use_container_width=True)

    # Table
    st.markdown("#### Prospect List")
    tier_filter = st.multiselect("Priority Tier", sorted(df["priority_tier"].dropna().unique().tolist()), key="prosp_tier")
    state_filter = st.multiselect("State", sorted(df["state_abbr"].dropna().unique().tolist()), key="prosp_state")
    filtered = df.copy()
    if tier_filter:
        filtered = filtered[filtered["priority_tier"].isin(tier_filter)]
    if state_filter:
        filtered = filtered[filtered["state_abbr"].isin(state_filter)]

    display_df = filtered[["entity_name", "state_abbr", "priority_tier", "priority_score",
                           "effective_vertical", "est_annual_revenue", "est_annual_volume",
                           "fee_per_scan", "size_category"]].copy()
    display_df.columns = ["Entity", "State", "Tier", "Score", "Vertical", "Est Rev", "Est Vol", "Fee/Scan", "Size"]

    event = st.dataframe(display_df.sort_values("Score", ascending=False),
                         use_container_width=True, hide_index=True,
                         on_select="rerun", selection_mode="single-row")

    if event and event.selection and event.selection.rows:
        idx = event.selection.rows[0]
        sel = filtered.iloc[idx]
        st.html(detail_panel_html(
            sel["entity_name"][:80],
            {
                "ORI Code": sel["ori_code"] or "—",
                "State": sel["state_abbr"],
                "County": sel["county"] or "—",
                "City": sel["city"] or "—",
                "Vertical": sel["effective_vertical"],
                "Vertical Cluster": sel["vertical_cluster"] or "—",
                "Priority Tier": sel["priority_tier"],
                "Priority Score": str(sel["priority_score"]),
                "Volume Score": str(sel["volume_score"]),
                "Accessibility Score": str(sel["accessibility_score"]),
                "Score Reason": sel["score_reason"] or "—",
                "Est Annual Volume": f"{sel['est_annual_volume']:,.0f}" if pd.notna(sel["est_annual_volume"]) else "—",
                "Est Annual Revenue": f"${sel['est_annual_revenue']:,.0f}" if pd.notna(sel["est_annual_revenue"]) else "—",
                "Fee per Scan": f"${sel['fee_per_scan']:.2f}" if pd.notna(sel["fee_per_scan"]) else "—",
                "Employee Count": str(sel["employee_count"]) if pd.notna(sel["employee_count"]) else "—",
                "Demand Type": sel["demand_type"] or "—",
                "Is B4ALL Customer": "Yes" if sel["is_b4all_customer"] else "No",
                "Contact": sel["contact_name"] or "—",
                "Contact Domain": sel["contact_domain"] or "—",
            },
        ))
```

- [ ] **Step 2: Update app.py, test, commit**

```bash
git add apps/sales/tabs/prospects.py apps/sales/app.py
git commit -m "feat: Sales Prospects tab with treemap and score distribution"
```

---

## Task 15: Sales — State Profiles Tab

**Files:**
- Create: `apps/sales/tabs/state_profiles.py`
- Modify: `apps/sales/app.py`

- [ ] **Step 1: Write apps/sales/tabs/state_profiles.py**

```python
# apps/sales/tabs/state_profiles.py
"""State Profiles tab — choropleth map, fee comparison, and full state detail."""

import streamlit as st
import pandas as pd
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html
from core.charts import choropleth_map, horizontal_bar_chart

CHANNELER_COLORS = {
    "open": COLORS["success"],
    "closed": COLORS["error"],
    "hybrid": COLORS["warning"],
    "limited": COLORS["slate"],
}


def render():
    df = query_view("sales_state_profiles")
    if df.empty:
        st.warning("No state profile data available.")
        return

    kpis = [
        {"label": "States", "value": str(len(df)), "color": COLORS["navy"]},
        {"label": "Open Market", "value": str(len(df[df["channeler_model"] == "open"])), "color": COLORS["success"]},
        {"label": "B4ALL States", "value": str(df["b4all_has_contract"].sum()), "color": COLORS["blue"]},
        {"label": "Avg Composite Score", "value": f"{df['composite_score'].mean():.1f}", "color": COLORS["navy"]},
    ]
    st.html(kpi_strip_html(kpis))

    col1, col2 = st.columns(2)

    with col1:
        fig = choropleth_map(df, locations="state_abbr", color="channeler_model",
                             title="Channeler Model by State", color_map=CHANNELER_COLORS)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fee_df = df[df["state_processing_fee"].notna()].copy()
        fee_df = fee_df.sort_values("state_processing_fee", ascending=True)
        fig = horizontal_bar_chart(fee_df, y="state_abbr", x="state_processing_fee",
                                   title="State Processing Fee")
        st.plotly_chart(fig, use_container_width=True)

    # Table
    st.markdown("#### All State Profiles")
    display_df = df[["state_abbr", "channeler_model", "state_processing_fee",
                     "b4all_has_contract", "b4all_location_count", "composite_score",
                     "demand_score", "volume_score"]].copy()
    display_df.columns = ["State", "Model", "Fee", "B4ALL Contract", "B4ALL Locations",
                          "Composite", "Demand", "Volume"]

    event = st.dataframe(display_df.sort_values("Composite", ascending=False),
                         use_container_width=True, hide_index=True,
                         on_select="rerun", selection_mode="single-row")

    if event and event.selection and event.selection.rows:
        idx = event.selection.rows[0]
        sel = df.iloc[idx]
        st.html(detail_panel_html(
            f"{sel['state_abbr']} — {sel['state_agency_name'] or 'State Profile'}",
            {
                "Channeler Model": sel["channeler_model"] or "—",
                "Incumbent Vendor": sel["incumbent_vendor"] or "—",
                "Contract Expiry": str(sel["contract_expiry_date"]) if pd.notna(sel["contract_expiry_date"]) else "—",
                "State Fee": f"${sel['state_processing_fee']:.2f}" if pd.notna(sel["state_processing_fee"]) else "—",
                "FBI Fee": f"${sel['fbi_processing_fee']:.2f}" if pd.notna(sel["fbi_processing_fee"]) else "—",
                "Typical Rolling Fee": f"${sel['typical_rolling_fee']:.2f}" if pd.notna(sel["typical_rolling_fee"]) else "—",
                "Est Total Applicant Cost": f"${sel['est_total_applicant_cost']:.2f}" if pd.notna(sel["est_total_applicant_cost"]) else "—",
                "Civil FP Volume": f"{sel['civil_fingerprint_volume']:,}" if pd.notna(sel["civil_fingerprint_volume"]) else "—",
                "LiveScan Volume": f"{sel['livescan_volume']:,}" if pd.notna(sel["livescan_volume"]) else "—",
                "B4ALL Locations": str(sel["b4all_location_count"]),
                "IdentoGO Locations": str(sel["identogo_location_count"]),
                "Certifix Locations": str(sel["certifix_location_count"]),
                "Total Operators": str(sel["total_operator_count"]),
                "Composite Score": f"{sel['composite_score']:.1f}",
                "Notes": sel["notes"] or "—",
            },
        ))
```

- [ ] **Step 2: Update app.py, test, commit**

```bash
git add apps/sales/tabs/state_profiles.py apps/sales/app.py
git commit -m "feat: Sales State Profiles tab with choropleth map and fee comparison"
```

---

## Task 16: Sales — Inbox Tab

**Files:**
- Create: `apps/sales/tabs/inbox.py`
- Modify: `apps/sales/app.py`

- [ ] **Step 1: Write apps/sales/tabs/inbox.py**

```python
# apps/sales/tabs/inbox.py
"""Sales Inbox tab — rolling email feed with detail expansion."""

import streamlit as st
import pandas as pd
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html


def render():
    df = query_view("sales_inbox")
    if df.empty:
        st.warning("No inbox data available.")
        return

    kpis = [
        {"label": "Total Emails", "value": str(len(df)), "color": COLORS["navy"]},
        {"label": "Unread", "value": str(len(df[~df["is_read"]])), "color": COLORS["warning"],
         "border_color": COLORS["warning"] if len(df[~df["is_read"]]) > 0 else None},
        {"label": "With Attachments", "value": str(len(df[df["has_attachments"]])), "color": COLORS["blue"]},
    ]
    st.html(kpi_strip_html(kpis))

    # Table — this is a feed, minimal charts
    st.markdown("#### Recent Emails")
    display_df = df[["received_at", "from_name", "subject", "mailbox",
                     "importance", "is_read", "has_attachments"]].copy()
    display_df.columns = ["Received", "From", "Subject", "Mailbox", "Importance", "Read", "Attachments"]
    display_df = display_df.sort_values("Received", ascending=False)

    event = st.dataframe(display_df, use_container_width=True, hide_index=True,
                         on_select="rerun", selection_mode="single-row")

    if event and event.selection and event.selection.rows:
        idx = event.selection.rows[0]
        sel = df.sort_values("received_at", ascending=False).iloc[idx]
        st.html(detail_panel_html(
            sel["subject"][:80] if sel["subject"] else "No Subject",
            {
                "From": f"{sel['from_name']} <{sel['from_address']}>",
                "Received": str(sel["received_at"]),
                "Mailbox": sel["mailbox"],
                "Folder": sel["folder_path"] or "—",
                "Direction": sel["direction"] or "—",
                "Importance": sel["importance"] or "Normal",
                "Preview": sel["body_preview"][:300] if sel["body_preview"] else "—",
            },
        ))
```

- [ ] **Step 2: Update app.py, test, commit**

```bash
git add apps/sales/tabs/inbox.py apps/sales/app.py
git commit -m "feat: Sales Inbox tab with email feed and detail expansion"
```

---

## Task 17: Support App — Entrypoint + Calls Weekly Tab

**Files:**
- Create: `apps/support/app.py`
- Create: `apps/support/tabs/__init__.py`
- Create: `apps/support/tabs/calls_weekly.py`

- [ ] **Step 1: Create apps/support/tabs/__init__.py**

Empty file.

- [ ] **Step 2: Write apps/support/tabs/calls_weekly.py**

```python
# apps/support/tabs/calls_weekly.py
"""Calls Weekly tab — stacked area by source system, department breakdown."""

import streamlit as st
import pandas as pd
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html
from core.charts import area_chart, stacked_bar_chart


def render():
    df = query_view("calls_weekly")
    if df.empty:
        st.warning("No weekly call data available.")
        return

    # Latest week KPIs
    latest_week = df["call_week"].max()
    latest = df[df["call_week"] == latest_week]
    total = latest["total_calls"].sum()
    answered = latest["answered"].sum()
    rate = (answered / total * 100) if total > 0 else 0

    kpis = [
        {"label": "Latest Week", "value": pd.Timestamp(latest_week).strftime("%b %d"), "color": COLORS["navy"]},
        {"label": "Total Calls", "value": f"{total:,}", "color": COLORS["navy"]},
        {"label": "Answered", "value": f"{answered:,}", "color": COLORS["success"]},
        {"label": "Answer Rate", "value": f"{rate:.1f}%", "color": COLORS["success"] if rate > 80 else COLORS["warning"]},
    ]
    st.html(kpi_strip_html(kpis))

    col1, col2 = st.columns(2)

    with col1:
        # Stacked area by source_system
        source_df = df.groupby(["call_week", "source_system"])["total_calls"].sum().reset_index()
        pivot = source_df.pivot(index="call_week", columns="source_system", values="total_calls").fillna(0).reset_index()
        cols = [c for c in pivot.columns if c != "call_week"]
        fig = area_chart(pivot, x="call_week", y_cols=cols, title="Call Volume by Source System")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Department breakdown grouped bar
        dept_df = df.groupby(["call_week", "department"])["total_calls"].sum().reset_index()
        fig = stacked_bar_chart(dept_df, x="call_week", y="total_calls", color="department",
                                title="Calls by Department")
        st.plotly_chart(fig, use_container_width=True)

    # Table
    st.markdown("#### Weekly Detail")
    display_df = df[["call_week", "department", "source_system", "total_calls", "answered",
                     "abandoned", "answer_rate", "avg_talk_min", "avg_wait_min"]].copy()
    display_df.columns = ["Week", "Dept", "Source", "Total", "Answered", "Abandoned",
                          "Answer %", "Avg Talk (min)", "Avg Wait (min)"]

    st.dataframe(display_df.sort_values("Week", ascending=False),
                 use_container_width=True, hide_index=True)
```

- [ ] **Step 3: Write apps/support/app.py**

```python
# apps/support/app.py
"""B4ALL Support Dashboard — Streamlit entrypoint."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

st.set_page_config(page_title="B4ALL Support Dashboard", page_icon="🎧", layout="wide",
                   initial_sidebar_state="collapsed")

st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stHeader"] { display: none; }
    .block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 style="color:#0D1B2A;margin-bottom:0;">Support Dashboard</h1>', unsafe_allow_html=True)

tab_weekly, tab_topic, tab_agent, tab_tickets = st.tabs([
    "Calls Weekly", "Calls by Topic", "Calls by Agent", "Tickets",
])

with tab_weekly:
    from apps.support.tabs.calls_weekly import render as render_weekly
    render_weekly()

with tab_topic:
    st.info("Calls by Topic — coming next task")

with tab_agent:
    st.info("Calls by Agent — coming soon")

with tab_tickets:
    st.info("Tickets — coming soon")
```

- [ ] **Step 4: Test locally and commit**

```bash
git add apps/support/app.py apps/support/tabs/__init__.py apps/support/tabs/calls_weekly.py
git commit -m "feat: Support Dashboard entrypoint + Calls Weekly tab"
```

---

## Task 18: Support — Calls by Topic Tab

**Files:**
- Create: `apps/support/tabs/calls_by_topic.py`
- Modify: `apps/support/app.py`

- [ ] **Step 1: Write apps/support/tabs/calls_by_topic.py**

```python
# apps/support/tabs/calls_by_topic.py
"""Calls by Topic tab — treemap and trend lines by support category."""

import streamlit as st
import pandas as pd
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html
from core.charts import treemap_chart, area_chart


def render():
    df = query_view("calls_by_topic")
    if df.empty:
        st.warning("No topic data available.")
        return

    # Latest month KPIs
    latest = df["call_month"].max()
    latest_df = df[df["call_month"] == latest]
    top_category = latest_df.groupby("support_category")["total_calls"].sum().idxmax() if not latest_df.empty else "—"

    kpis = [
        {"label": "Topics", "value": str(df["support_topic"].nunique()), "color": COLORS["navy"]},
        {"label": "Categories", "value": str(df["support_category"].nunique()), "color": COLORS["blue"]},
        {"label": "Top Category", "value": top_category, "color": COLORS["navy"]},
        {"label": "Latest Month Calls", "value": f"{latest_df['total_calls'].sum():,}", "color": COLORS["navy"]},
    ]
    st.html(kpi_strip_html(kpis))

    col1, col2 = st.columns(2)

    with col1:
        # Treemap by support_category → support_topic
        tree_df = latest_df.groupby(["support_category", "support_topic"])["total_calls"].sum().reset_index()
        fig = treemap_chart(tree_df, path=["support_category", "support_topic"],
                            values="total_calls", title="Call Volume by Category → Topic")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Trend lines for top 5 categories
        top5 = df.groupby("support_category")["total_calls"].sum().nlargest(5).index
        trend = df[df["support_category"].isin(top5)].groupby(
            ["call_month", "support_category"])["total_calls"].sum().reset_index()
        pivot = trend.pivot(index="call_month", columns="support_category", values="total_calls").fillna(0).reset_index()
        cols = [c for c in pivot.columns if c != "call_month"]
        fig = area_chart(pivot, x="call_month", y_cols=cols, title="Top 5 Categories — Trend", fill=False)
        st.plotly_chart(fig, use_container_width=True)

    # Table with drill-down to calls_log
    st.markdown("#### Topic Detail")
    display_df = latest_df[["support_category", "support_topic", "total_calls",
                            "answered", "avg_talk_min", "unique_customers"]].copy()
    display_df.columns = ["Category", "Topic", "Calls", "Answered", "Avg Talk (min)", "Unique Customers"]

    event = st.dataframe(display_df.sort_values("Calls", ascending=False),
                         use_container_width=True, hide_index=True,
                         on_select="rerun", selection_mode="single-row")

    # Drill into calls_log for selected topic
    if event and event.selection and event.selection.rows:
        idx = event.selection.rows[0]
        sel = latest_df.iloc[idx]
        st.markdown(f"##### Calls for: {sel['support_topic']}")
        calls = query_view("calls_log")
        topic_calls = calls[calls["support_topic"] == sel["support_topic"]].sort_values("call_date", ascending=False)
        st.dataframe(
            topic_calls[["call_date", "agent_name", "customer_name", "talk_minutes", "resolution_method"]].head(20),
            use_container_width=True, hide_index=True,
        )
```

- [ ] **Step 2: Update app.py, test, commit**

```bash
git add apps/support/tabs/calls_by_topic.py apps/support/app.py
git commit -m "feat: Calls by Topic tab with treemap and calls_log drill-down"
```

---

## Task 19: Support — Calls by Agent Tab

**Files:**
- Create: `apps/support/tabs/calls_by_agent.py`
- Modify: `apps/support/app.py`

- [ ] **Step 1: Write apps/support/tabs/calls_by_agent.py**

```python
# apps/support/tabs/calls_by_agent.py
"""Calls by Agent tab — radar chart, leaderboard, agent drill-down."""

import streamlit as st
import pandas as pd
from streamlit_echarts import st_echarts
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html
from core.charts import radar_chart, horizontal_bar_chart


def render():
    df = query_view("calls_by_agent")
    if df.empty:
        st.warning("No agent data available.")
        return

    latest = df["call_month"].max()
    latest_df = df[df["call_month"] == latest]

    top_agent = latest_df.loc[latest_df["total_calls"].idxmax(), "agent_name"] if not latest_df.empty else "—"
    best_rate = latest_df.loc[latest_df["answer_rate"].idxmax(), "agent_name"] if not latest_df.empty else "—"

    kpis = [
        {"label": "Agents", "value": str(len(latest_df)), "color": COLORS["navy"]},
        {"label": "Top Volume", "value": top_agent, "color": COLORS["blue"]},
        {"label": "Best Answer Rate", "value": best_rate, "color": COLORS["success"]},
    ]
    st.html(kpi_strip_html(kpis))

    col1, col2 = st.columns(2)

    with col1:
        # Radar chart for top agents
        top_agents = latest_df.nlargest(5, "total_calls")
        if not top_agents.empty:
            max_calls = top_agents["total_calls"].max()
            max_talk = top_agents["total_talk_min"].max()
            indicators = [
                {"name": "Calls", "max": int(max_calls * 1.2)},
                {"name": "Answer Rate", "max": 100},
                {"name": "Talk Time", "max": float(max_talk * 1.2)},
            ]
            series = [
                {"name": row["agent_name"],
                 "value": [int(row["total_calls"]), float(row["answer_rate"]), float(row["total_talk_min"])]}
                for _, row in top_agents.iterrows()
            ]
            st_echarts(radar_chart(indicators, series, "Agent Performance Radar"), height="350px")

    with col2:
        # Leaderboard bar
        fig = horizontal_bar_chart(latest_df, y="agent_name", x="total_calls", title="Call Volume Leaderboard")
        st.plotly_chart(fig, use_container_width=True)

    # Table
    st.markdown("#### Agent Detail")
    display_df = latest_df[["agent_name", "total_calls", "answered", "answer_rate",
                            "total_talk_min", "avg_talk_min", "avg_wait_min"]].copy()
    display_df.columns = ["Agent", "Calls", "Answered", "Answer %", "Total Talk (min)", "Avg Talk", "Avg Wait"]

    event = st.dataframe(display_df.sort_values("Calls", ascending=False),
                         use_container_width=True, hide_index=True,
                         on_select="rerun", selection_mode="single-row")

    if event and event.selection and event.selection.rows:
        idx = event.selection.rows[0]
        sel = latest_df.iloc[idx]
        st.markdown(f"##### Recent Calls for: {sel['agent_name']}")
        calls = query_view("calls_log")
        agent_calls = calls[calls["agent_name"] == sel["agent_name"]].sort_values("call_date", ascending=False)
        st.dataframe(
            agent_calls[["call_date", "customer_name", "support_topic", "talk_minutes",
                         "call_status", "resolution_method"]].head(20),
            use_container_width=True, hide_index=True,
        )
```

- [ ] **Step 2: Update app.py, test, commit**

```bash
git add apps/support/tabs/calls_by_agent.py apps/support/app.py
git commit -m "feat: Calls by Agent tab with radar chart and leaderboard"
```

---

## Task 20: Support — Tickets Tab

**Files:**
- Create: `apps/support/tabs/tickets.py`
- Modify: `apps/support/app.py`

- [ ] **Step 1: Write apps/support/tabs/tickets.py**

```python
# apps/support/tabs/tickets.py
"""Tickets tab — burndown, SLA gauge, pipeline funnel, ticket drill-down."""

import streamlit as st
import pandas as pd
from streamlit_echarts import st_echarts
from core.db import query_view
from core.theme import COLORS
from core.components import kpi_strip_html, detail_panel_html
from core.charts import area_chart, gauge_chart, funnel_chart


def render():
    monthly = query_view("tickets_monthly")
    log = query_view("tickets_log")

    if monthly.empty:
        st.warning("No ticket data available.")
        return

    # Latest month KPIs
    latest_month = monthly["report_month"].max()
    latest = monthly[monthly["report_month"] == latest_month]
    opened = latest["tickets_opened"].sum()
    closed = latest["tickets_closed"].sum()
    sla_pct = latest["sla_resolution_on_time_pct"].mean()
    avg_resolution = latest["avg_resolution_hours"].mean()

    kpis = [
        {"label": "Opened", "value": f"{opened:,}", "color": COLORS["navy"]},
        {"label": "Closed", "value": f"{closed:,}", "color": COLORS["success"]},
        {"label": "SLA On Time", "value": f"{sla_pct:.0f}%", "color": COLORS["success"] if sla_pct > 80 else COLORS["warning"]},
        {"label": "Avg Resolution (hrs)", "value": f"{avg_resolution:.1f}", "color": COLORS["navy"]},
    ]
    st.html(kpi_strip_html(kpis))

    col1, col2 = st.columns([2, 1])

    with col1:
        # Burndown — opened vs closed trend
        trend = monthly.groupby("report_month").agg(
            opened=("tickets_opened", "sum"),
            closed=("tickets_closed", "sum"),
        ).reset_index().sort_values("report_month")
        fig = area_chart(trend, x="report_month", y_cols=["opened", "closed"],
                         title="Tickets Opened vs Closed", fill=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # SLA gauge
        st_echarts(gauge_chart(float(sla_pct), "SLA Compliance", suffix="%"), height="250px")

    # Pipeline funnel from log
    if not log.empty:
        pipeline_counts = log.groupby("pipeline").size().reset_index(name="count")
        pipeline_counts = pipeline_counts.sort_values("count", ascending=False)
        fig = funnel_chart(pipeline_counts, stage="pipeline", value="count", title="Tickets by Pipeline")
        st.plotly_chart(fig, use_container_width=True)

    # Ticket log table
    st.markdown("#### Recent Tickets")
    if not log.empty:
        display_df = log[["created_at", "subject", "status", "priority", "pipeline",
                          "customer_name", "sla_status", "resolution_hours"]].copy()
        display_df.columns = ["Created", "Subject", "Status", "Priority", "Pipeline",
                              "Customer", "SLA", "Resolution (hrs)"]

        event = st.dataframe(display_df.sort_values("Created", ascending=False),
                             use_container_width=True, hide_index=True,
                             on_select="rerun", selection_mode="single-row")

        if event and event.selection and event.selection.rows:
            idx = event.selection.rows[0]
            sel = log.sort_values("created_at", ascending=False).iloc[idx]
            st.html(detail_panel_html(
                sel["subject"][:80] if sel["subject"] else "Ticket",
                {
                    "Ticket ID": str(sel["hubspot_ticket_id"]),
                    "Status": sel["status"],
                    "Priority": sel["priority"] or "—",
                    "Pipeline": sel["pipeline"],
                    "Source": sel["source"] or "—",
                    "Channel": sel["channel"] or "—",
                    "Intent": sel["ticket_intent"] or "—",
                    "Classification": sel["ticket_classification"] or "—",
                    "Customer": sel["customer_name"] or "—",
                    "Client ID": sel["client_id"] or "—",
                    "Created": str(sel["created_at"]),
                    "Closed": str(sel["closed_at"]) if pd.notna(sel["closed_at"]) else "Open",
                    "Resolution Hours": f"{sel['resolution_hours']:.1f}" if pd.notna(sel["resolution_hours"]) else "—",
                    "First Response Hours": f"{sel['first_response_hours']:.1f}" if pd.notna(sel["first_response_hours"]) else "—",
                    "SLA Status": sel["sla_status"] or "—",
                    "Thread Summary": sel["thread_summary"][:200] if sel["thread_summary"] else "—",
                },
            ))
```

- [ ] **Step 2: Update app.py, test, commit**

```bash
git add apps/support/tabs/tickets.py apps/support/app.py
git commit -m "feat: Tickets tab with burndown, SLA gauge, and pipeline funnel"
```

---

## Task 21: Final Integration — Test All Apps + Deployment Config

**Files:**
- Modify: `apps/finance/app.py` (verify all placeholders replaced)
- Modify: `apps/sales/app.py` (verify all placeholders replaced)
- Modify: `apps/support/app.py` (verify all placeholders replaced)

- [ ] **Step 1: Verify all app.py files have no remaining placeholders**

Grep for `st.info` in all app.py files — should return zero results:

Run: `grep -r "st.info" apps/*/app.py`
Expected: No output (all placeholders replaced by real tab imports).

- [ ] **Step 2: Run all tests**

Run: `cd /Users/jackelliott/commandcenter/projects/notion/notion-data-syncing && source .venv/bin/activate && python -m pytest tests/ -v`
Expected: All tests pass.

- [ ] **Step 3: Smoke test each app locally**

Run each app one at a time to verify it loads without errors:

```bash
streamlit run apps/finance/app.py --server.port 8501
# Open http://localhost:8501, verify all 5 tabs render
# Ctrl+C to stop

streamlit run apps/sales/app.py --server.port 8502
# Open http://localhost:8502, verify all 6 tabs render
# Ctrl+C to stop

streamlit run apps/support/app.py --server.port 8503
# Open http://localhost:8503, verify all 4 tabs render
# Ctrl+C to stop
```

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: complete Streamlit dashboards — Finance, Sales, Support

3 apps with 15 tabs total, querying 17 notion_sync views via Supabase.
Plotly + ECharts charts, B4ALL brand colors, full drill-down interaction.
Ready for Streamlit Cloud deployment."
```

- [ ] **Step 5: Document deployment steps for user**

Print these instructions:

```
DEPLOYMENT — Streamlit Community Cloud:

1. Push this repo to GitHub (or a subfolder of commandcenter)
2. Go to share.streamlit.io → "New app"
3. For each app:
   - Repository: <your-repo>
   - Branch: main
   - Main file path: apps/finance/app.py (or sales/app.py, support/app.py)
   - App URL: pick a slug (e.g., b4all-finance)
4. In each app's Settings → Secrets, paste your secrets.toml content
5. Copy the public URL for each app

NOTION EMBEDDING:
1. Open the Finance Hub page in Notion
2. Type /embed
3. Paste the Streamlit Cloud URL for the Finance app
4. Resize the embed block to full width
5. Repeat for Sales Hub and Support Hub
```
