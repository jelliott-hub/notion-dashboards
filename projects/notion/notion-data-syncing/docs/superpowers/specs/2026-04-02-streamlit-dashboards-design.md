# Streamlit Dashboards for Notion Embeds — Design Spec

## Purpose

Replace Notion database sync (CSV, WhaleSync, MCP page creation) with Streamlit apps that query Supabase `notion_sync` views live and embed into Notion hub pages via `/embed` blocks. This gives B4ALL interactive, chart-forward dashboards with full drill-down — something Notion tables cannot do natively.

## Architecture

**Monorepo with shared core.** Single repo at `notion-data-syncing/` containing:

```
apps/
  finance/        # Finance Dashboard (Streamlit entrypoint)
  sales/          # Sales Dashboard (Streamlit entrypoint)
  support/        # Support Dashboard (Streamlit entrypoint)
core/
  db.py           # Supabase connection (single client, connection pooling)
  theme.py        # B4ALL brand colors, Plotly/ECharts theme configs
  components.py   # Reusable: KPI strip, detail panel, filter bar, data table
  charts.py       # Chart factory functions (area, gauge, donut, treemap, etc.)
requirements.txt
.streamlit/
  config.toml     # Theme overrides (background, text, accent colors)
```

Each app is a separate Streamlit entrypoint deployed independently. Shared `core/` library provides consistent theming, DB access, and reusable components.

## Brand Colors

All dashboards use the B4ALL palette:

| Role | Color | Hex |
|------|-------|-----|
| Headings, primary text | Navy | `#0D1B2A` |
| Accents, active tabs, links | Brand Blue | `#2B7BE9` |
| Blue Dark (hover, secondary) | Blue Dark | `#1A5FC7` |
| Detail panels, info callouts | Blue Light | `#E8F1FD` |
| Page background, row backgrounds | Off-white | `#F4F6FA` |
| Cards, containers | White | `#FFFFFF` |
| Borders | Border | `#E2E8F0` |
| Labels, body text | Slate | `#64748B` |
| Pass/success | Green | `#22C55E` |
| Warning/caution | Amber | `#F59E0B` |
| Failing/error | Red | `#E74C3C` |

## Charting Libraries

**Plotly + ECharts hybrid:**

- **Plotly** (`st.plotly_chart`) — area charts, bar charts, scatter plots, funnels, treemaps, heatmaps, choropleth maps. Handles data-heavy interactive charts with hover, zoom, and click events.
- **ECharts** (`streamlit-echarts`) — gauge dials, animated donuts, radar charts, progress rings. WebGL-rendered for smooth animations and visual polish.
- **Custom `st.components.v1.html`** — KPI strips, status pills, and detail panels rendered as branded HTML for pixel-perfect control.

## Interaction Model

Three levels of drill-down on every tab:

1. **KPI cards / chart segments** — Click to filter. Clicking a KPI card or chart segment (e.g., "3 failing" or a bar segment) applies a filter to the data table below, showing only that subset.
2. **Data table rows** — Click to expand. Clicking a row in the filtered table opens a detail panel below the table showing all fields for that record, related context, and source view links.
3. **Cross-tab navigation** — Status pills and certain chart elements can jump to another tab with pre-applied filters (e.g., clicking "AR Recon: DELTA" on Close Dashboard jumps to the AR Aging tab filtered to the delta records).

Implementation: `streamlit-plotly-events` for Plotly click callbacks, `st.session_state` for filter state, `st.query_params` for cross-tab deep links.

## Data Layer

All data comes from `notion_sync` schema on B4All-Hub (`dozjdswqnzqwvieqvwpe`).

Connection: `psycopg2` or `st.connection("postgresql")` with Supabase direct connection string. Connection pooled, queries cached via `@st.cache_data(ttl=300)` (5-minute TTL).

No writes. SELECT only.

## App 1: Finance Dashboard

**Notion embed location:** Finance Hub page
**Tabs:** 5

### Tab: Close Dashboard
- **KPI strip:** Overall Health, Gross Margin, Revenue, Failing Accounts count
- **Charts:**
  - Revenue vs COGS 12-month area chart (Plotly) with margin shading
  - Gross margin radial gauge (ECharts) with 6mo avg and YoY
  - Close checklist donut (ECharts) — done/in-progress/blocked
  - Reconciliation status bars (Plotly) — P&L, Cash, AR, Clearing
- **Drill-down:** Click status bar → filtered blocking items table → row detail with GL breakdown
- **Source view:** `notion_sync.finance_close_dashboard`

### Tab: P&L Reconciliation
- **KPI strip:** Total accounts, passing/failing count, total delta
- **Charts:**
  - Horizontal bar chart of deltas by GL account (Plotly), sorted by absolute delta
  - Pass/fail donut (ECharts)
- **Drill-down:** Click bar → detail panel with hub_total, qb_total, delta, source_view, note
- **Source view:** `notion_sync.finance_pnl`

### Tab: AR Aging
- **KPI strip:** Total AR, 30/60/90/120+ bucket totals
- **Charts:**
  - Stacked bar by aging bucket (Plotly)
  - Top 10 overdue invoices horizontal bar
- **Drill-down:** Click bucket → filtered invoice table → row detail with customer, invoice dates, amount
- **Source view:** `notion_sync.finance_ar_aging`

### Tab: Variance Analysis
- **KPI strip:** Flagged accounts count, largest MoM swing, largest YoY swing
- **Charts:**
  - Heatmap of MoM % change by GL account × month (Plotly)
  - Flagged accounts bar chart sorted by variance magnitude
- **Drill-down:** Click cell/bar → detail panel with 6-month trend, all variance metrics
- **Source view:** `notion_sync.finance_variance`

### Tab: Accounting Inbox
- **KPI strip:** Reply rate %, avg response time (min), total email volume, unique customers
- **Charts:**
  - Monthly volume trend line by classification (Plotly)
  - Reply rate gauge (ECharts)
  - Response time distribution bar chart
- **Drill-down:** Click month/classification → filtered table by folder_category → row detail with thread metrics
- **Source view:** `notion_sync.finance_accounting_inbox`

## App 2: Sales Dashboard

**Notion embed location:** Sales Hub page
**Tabs:** 6

### Tab: RFP Pipeline
- **Charts:**
  - Stacked bar by source × relevance HIGH/MEDIUM/LOW (Plotly)
  - Timeline scatter with deadline bubbles sized by amount
- **Drill-down:** Click segment → filtered table → row detail with description, source URL, agency
- **Source view:** `notion_sync.sales_rfp_pipeline`

### Tab: Deals
- **Charts:**
  - Funnel chart by deal stage (Plotly)
  - Deal value bar chart by pipeline
- **Drill-down:** Click stage → deals in that stage → row detail
- **Source view:** `notion_sync.sales_deals`

### Tab: Opportunities
- **Charts:**
  - Heatmap by source_type × urgency_tier (Plotly)
  - Timeline chart with posted_date → deadline range bars
- **Drill-down:** Click cell → filtered opportunity list → row detail
- **Source view:** `notion_sync.sales_opportunities`

### Tab: Prospects
- **Charts:**
  - Treemap by state × priority_tier (Plotly)
  - Score distribution histogram
- **Drill-down:** Click state/tier → prospect list → row detail with est_annual_revenue, score breakdown
- **Source view:** `notion_sync.sales_prospects`

### Tab: State Profiles
- **Charts:**
  - Choropleth map colored by channeler_model (Plotly)
  - Fee per scan comparison bars by state
- **Drill-down:** Click state → full profile panel with all 21 fields
- **Source view:** `notion_sync.sales_state_profiles`

### Tab: Inbox
- **Charts:** Volume sparkline (lightweight — this is a feed, not an analytics tab)
- **Drill-down:** Row click → email detail
- **Source view:** `notion_sync.sales_inbox`

## App 3: Support Dashboard

**Notion embed location:** Support Hub page
**Tabs:** 4

### Tab: Calls Weekly
- **Charts:**
  - Stacked area by source_system — Bland vs DialPad (Plotly)
  - Department breakdown grouped bars
- **Drill-down:** Click week → daily breakdown table
- **Source view:** `notion_sync.calls_weekly`

### Tab: Calls by Topic
- **Charts:**
  - Treemap by support_category (Plotly)
  - Month-over-month trend lines for top topics
- **Drill-down:** Click topic → call list for that topic
- **Source view:** `notion_sync.calls_by_topic`

### Tab: Calls by Agent
- **Charts:**
  - Radar chart per agent — volume, avg duration, etc. (ECharts)
  - Leaderboard horizontal bars
- **Drill-down:** Click agent → their calls
- **Source view:** `notion_sync.calls_by_agent`

### Tab: Tickets
- **Charts:**
  - Burndown chart — open vs closed over time (Plotly)
  - SLA compliance gauge (ECharts)
  - Pipeline funnel by stage
- **Drill-down:** Click bucket/stage → ticket list → row detail
- **Source views:** `notion_sync.tickets_log`, `notion_sync.tickets_monthly`

### Detail data views (not tabs — used for drill-down)
- `notion_sync.calls_log` (2,667 rows) — individual call records. When a user clicks a week/topic/agent in the tabs above, the detail table queries `calls_log` filtered to that selection.
- `notion_sync.tickets_log` (722 rows) — also used as both a summary source (Tickets tab) and row-level detail for drill-down.

## Deployment

**Streamlit Community Cloud** (free tier):
- Connect GitHub repo
- Deploy each app as a separate Streamlit app pointing to its entrypoint (`apps/finance/app.py`, etc.)
- Supabase connection string stored in Streamlit secrets (`.streamlit/secrets.toml` locally, Streamlit Cloud secrets UI for production)
- Each app gets its own public URL → embed into corresponding Notion hub page

## Notion Embedding

Each hub page gets an `/embed` block with the Streamlit app URL. Streamlit's default sidebar can be hidden via `config.toml` or `?embed=true` query param to keep the embed clean.

```toml
# .streamlit/config.toml
[ui]
hideTopBar = true

[theme]
backgroundColor = "#F4F6FA"
secondaryBackgroundColor = "#FFFFFF"
textColor = "#0D1B2A"
primaryColor = "#2B7BE9"
```

## Dependencies

```
streamlit>=1.32
plotly>=5.18
streamlit-echarts>=0.4
streamlit-plotly-events>=0.0.6
psycopg2-binary>=2.9
pandas>=2.1
```
