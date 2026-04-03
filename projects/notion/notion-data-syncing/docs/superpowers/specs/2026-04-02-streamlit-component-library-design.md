# Streamlit Component Library — Design Spec

**Date:** 2026-04-02
**Goal:** Make the `core/` layer so self-documenting that a fresh Claude session can build a new dashboard from zero in one shot.

## Problem

The current core library works but isn't self-describing. A new Claude would need to read every source file, guess at conventions, and repeat boilerplate patterns found in existing tabs. Type coercion is duplicated across 14 tab files. The db layer is hardcoded to `notion_sync`.

## Design

### 1. Schema-flexible `core/db.py`

`query_view` gains an optional `schema` parameter (default `"notion_sync"`). The REST API's `Accept-Profile` header already supports arbitrary schemas — we just parameterize it.

```python
query_view("mv_call_spine", schema="analytics")
query_view("finance_pnl")  # defaults to notion_sync
```

`_coerce_types` stays as the single source of truth for REST API type conversion. New tabs should NOT repeat `pd.to_numeric` calls — the core layer handles it.

### 2. Chart catalog (`core/charts.py`)

No new chart types. Every existing function gets a docstring with:
- One-line description
- Parameter descriptions with types
- DataFrame shape requirement (what columns, what types)
- 3-line usage example

Available charts:
- `area_chart` — multi-series line/area over time
- `horizontal_bar_chart` — sorted horizontal bars, optional color mapping
- `stacked_bar_chart` — grouped stacked bars via px.bar
- `funnel_chart` — pipeline/stage funnel
- `heatmap_chart` — pivot heatmap from long-format data
- `treemap_chart` — hierarchical treemap via px.treemap
- `scatter_timeline` — scatter on date axis with optional bubble sizing
- `choropleth_map` — US state map
- `gauge_chart` — ECharts gauge (returns dict)
- `donut_chart` — ECharts donut/pie (returns dict)
- `radar_chart` — ECharts radar (returns dict)
- `status_bars` — horizontal progress bars for reconciliation

### 3. UI components (`core/components.py`)

Same treatment — docstrings with examples:
- `kpi_strip_html` — horizontal row of KPI cards
- `detail_panel_html` — expandable key-value detail panel
- `status_pill_html` — colored status badge

### 4. Theme (`core/theme.py`)

Add module docstring describing the color system. No code changes.

### 5. Dashboard template (`apps/_template/`)

Copy-paste skeleton, not a framework:
- `app.py` — entrypoint with `set_page_config`, CSS chrome hiding, title, tab router
- `tabs/_template_tab.py` — standard tab pattern: query, KPIs, charts in columns, data table with selection, detail panel

### 6. CLAUDE.md component catalog

A new section in the project CLAUDE.md with:
- Chart function signatures and what data shape each expects
- UI component signatures
- `query_view` API with schema parameter
- Step-by-step recipe: "To create a new dashboard..."
- Pattern reference: the standard tab structure

## What doesn't change

- No base classes, frameworks, or metaclasses
- No changes to existing working tabs
- No new dependencies
- Chart functions stay as plain functions: DataFrame in, figure out

## Success criteria

A fresh Claude session can:
1. Read CLAUDE.md and know every available component
2. Copy `apps/_template/`, rename it, fill in specifics
3. Have a working dashboard on the first try
