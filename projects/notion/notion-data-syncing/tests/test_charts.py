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
