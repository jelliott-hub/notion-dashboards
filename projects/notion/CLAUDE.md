# B4ALL Notion Workspace

Company intranet in Notion — 11 top-level content hubs with ~500+ articles as standalone pages, plus a searchable Knowledge Base database with metadata for ~1000 articles from the Git KB repo.

## Current State (as of 2026-04-02)

### Teamspace
- **Biometrics4All** (`32f13d36-77c3-81de-8884-00425628f22c`) — the one teamspace, Jack is owner
- API limitation: can't create pages directly under a teamspace. Create under a page that's in the teamspace, or create at workspace root and drag in manually.

### Live Hub Pages

All hubs follow the same pattern: a top-level page with a summary table (section / articles / covers), then child sub-pages per section, then individual article pages under each section. Full article content lives on the article pages themselves — NOT in the KB database.

| Hub | ID | Articles | Sections | Icon |
|-----|----|----------|----------|------|
| Customer Success | `33613d36-77c3-8109-a97b-f8a8eb19e900` | 101 | 7 (Applicant Support, Operator Support, Billing & Disputes, Submissions & Status, Account Mgmt, Workflows, Escalation Directory) | headset_gray |
| Engineering | `33613d36-77c3-816f-a774-c4d21c11341b` | 120 | 6 (Applicant Services, Development, Infrastructure, LiveScan Platform, Thin Client, Upgrader Tools) | database_gray |
| Growth (Sales) | `33613d36-77c3-818f-91fc-eb46ca7e9c12` | 78 | 8 (Competitors, Conversations, Partnerships, Pricing, Process, Products, RFPs, Reference) | bullseye_gray |
| Accounting & Finance | `33613d36-77c3-803e-89a9-c0bae5151976` | 61 | 9 (Receivables, Reconciliation, Compliance & Tax, Month-End Close, Payables, Policies, CoA, Reference, Decision Tree) | chart-area_gray |
| Implementation | `33613d36-77c3-8138-ab41-eb2c26ce29ba` | 45 | 10 (Accounts, CBID, Client Configs, Integrations, Onboarding, Portals, Reference, System Config, System Deployment, Glossary) | follow_gray |
| Products | `33613d36-77c3-81ee-9922-f161f57f3094` | 24 | 6 (Applicant Services, Cardscan, Channeling, CMS ThinClient, Enrollment API, LiveScan) | subtask_gray |
| Tools | `33613d36-77c3-813c-b7c0-eca31fc3b7f3` | 18 | 5 (Bland AI, Dialpad, HubSpot, Dock, Pandadoc) + Tool Tracker database | cursor-click_gray |
| Getting Started | `33713d36-77c3-81b6-b243-efbf48a843b4` | 7 | flat (Business Foundations, Contract Code Hierarchy, CSR Reference, Glossary, Onboarding Guide, State Routing, Training Curriculum) | compass_gray |
| Templates | `33613d36-77c3-8178-a0c8-ce9bb2034730` | 9 categories | 9 (Email-Accounting, Email-Customer, Email-Operational, Forms-Compliance, Forms-Financial, Internal-Operational, Quotes-And-Contracts, Sales-Outreach, Attachments) + Template Categories database | checklist_gray |
| Compliance | `33713d36-77c3-8151-a8b9-ef2876972a80` | varies | 3 (HR, Security, Vendor) | none |
| Company Knowledge Base | `5deacb87-0209-4dfb-bfe6-b735bf31cfdb` | — | Contains the KB database inline | book-closed_gray |

### Live Databases

| Database | ID | Data Source ID | Parent | Status |
|----------|----|----------------|--------|--------|
| Knowledge Base | `1772e0c0-8b5f-45cf-8066-47f43212393c` | `c7c5503e-b003-4e56-8e8b-f40fb27fdc69` | Company Knowledge Base | ~1000 articles, metadata only (no article body content). 9 filtered views. |
| Template Categories | `33713d36-77c3-80b9-b8ed-e1a7e626afdf` | `2611f335-267c-49e3-a1d7-26f94464bca5` | Templates hub | Template categorization |
| Tool Tracker | `33713d36-77c3-80b9-b8ed-e1a7e626afdf` | `33713d36-77c3-819a-a7cb-000ba879979b` | Tools hub | Tool inventory |

### Trashed (do not reference or recreate)

**Pages:** B4ALL Home `4e371f20`, Support Hub `33613d36...80db`, Sales Hub `1d8d1553`, B4ALL Knowledge Base page `33413d36...816d`

**Databases (from Sales Hub):** RFPs & Proposals, Deals Pipeline, Inbox Feed, Opportunities, State Profiles, Prospects, Regulatory Changes — all trashed. The database-per-hub approach was abandoned because Notion API truncates/mangles article content pushed as child blocks.

**Databases (from prior POC):** Customer Directory, Call Volume Daily, Deal Pipeline, Device Directory, Ticket Board — all deleted.

### KB Database Schema

```sql
CREATE TABLE "Knowledge Base" (
  "Article" TITLE,
  "Section" SELECT('templates', 'technical', 'customer-success', 'states', 'sales',
                    'finance', 'implementation', 'compliance', 'products', 'tools', 'getting-started'),
  "Category" RICH_TEXT,
  "Type" SELECT('Reference', 'SOP', 'Policy', 'Guide'),
  "Status" SELECT('active', 'current', 'needs_review', 'archived'),
  "Owner" SELECT('operations', 'customer-success', 'sales', 'controller',
                  'implementation', 'compliance', 'engineering', 'support'),
  "Audience" MULTI_SELECT('operations', 'sales', 'support', 'finance', 'engineering',
                           'implementation', 'compliance', 'hr', 'executive', 'all-staff'),
  "Description" RICH_TEXT,
  "File Path" RICH_TEXT,
  "Last Reviewed" DATE
)
```

### KB Database Views (9 views)

| View | Type | Filter |
|------|------|--------|
| Default view | table | none |
| Support — Call Intake | table | audience:support AND category contains "call-intake" |
| Support — Escalations | table | audience:support AND category contains "escalation" |
| Support — All Articles | table | audience:support, grouped by Section |
| Support — Needs Review | board | audience:support AND status:needs_review, grouped by Section |
| Support — State Reference | table | section:states |
| Support — Products & Tools | table | audience:support AND section in (products, tools, technical) |
| Support — Templates | gallery | section:templates AND audience:support |
| Getting Started | table | section:getting-started |
| Customer Success — All Articles | table | section:customer-success |

## Architecture

### How content is organized

```
Hub Page (e.g., "Engineering")
  ├── Summary table: section / article count / what it covers
  ├── Section sub-page (e.g., "LiveScan Platform")
  │     ├── Article page (full content, styled per style guide)
  │     ├── Article page
  │     └── ...
  ├── Section sub-page (e.g., "Thin Client")
  │     └── ...
  └── ...
```

Articles are standalone Notion pages with full content — NOT database rows. The KB database is a separate searchable index with metadata only. The two are not linked yet.

### What was tried and abandoned
- **Linked database views on hub pages** — Notion AI built intranet-style hub pages with embedded KB database views. Trashed because database rows couldn't render full article content.
- **Article content push to KB database pages** — Plan to push markdown as child blocks hit Notion API limits (~2000-char blocks, truncation, formatting loss).
- **Operational databases synced from Supabase** — 7 databases created under Sales Hub from `notion_sync` views. All trashed.

### Open question
The KB database (~1000 metadata rows) and the hub article pages (~500+ full-content pages) are currently disconnected. The KB database knows about articles by file path but doesn't link to the actual Notion pages in the hubs. Connecting them would let users search/filter in the KB database and click through to the full article.

## Supabase

- **Only project:** B4All-Hub (`dozjdswqnzqwvieqvwpe`)
- Source data lives in `analytics` schema (fact tables, matviews, dims)
- `notion_sync` schema has 12 views (6 support, 6 sales) — built but not actively feeding Notion
- **SELECT only** — never INSERT/UPDATE/DELETE unless explicitly authorized

## Key Matviews (for future operational sync)

- `analytics.mv_call_spine` — denormalized call data (all sources, deduped, department-tagged)
- `analytics.mv_customer_intel` — enriched customer 360
- `analytics.dim_customer` — core customer dimension
- `analytics.dim_org` — team directory (people, queues, phone lines)

## Rules

- NEVER query any Supabase project other than B4All-Hub
- Always use `data_source_id` (not `database_id`) for Notion writes
- Select options must exist in Notion schema before writing rows with new values
- Teamspace ID cannot be used as a page parent — use a page within the teamspace
- Do NOT create pages via MCP — they land in Recents, not sidebar. User hates it.
- Article style guide at `style-guide/notion-article-style-guide.md` — no colored headings, no covers on articles, no emoji except warning callouts

## Streamlit Dashboards (`notion-data-syncing/`)

### Project Structure

```
notion-data-syncing/
  core/               # Shared library — charts, components, db, theme
  apps/
    finance/app.py    # Finance Dashboard (5 tabs)
    sales/app.py      # Sales Dashboard (5 tabs)
    support/app.py    # Support Dashboard (4 tabs)
    _template/        # Copy-paste skeleton for new dashboards
  tests/              # pytest suite for core/
  requirements.txt
  .streamlit/config.toml
```

Run any dashboard: `streamlit run apps/<name>/app.py`

### Creating a New Dashboard

1. Copy `apps/_template/` to `apps/<your_dashboard>/`
2. Edit `app.py`: set title, page icon, define tabs
3. For each tab, copy `tabs/example_tab.py` to `tabs/<tab_name>.py`
4. In each tab's `render()`: call `query_view("view_name")`, build KPIs, pick charts, set table columns
5. Run with `streamlit run apps/<your_dashboard>/app.py`

### Data Layer (`core/db.py`)

```python
from core.db import query_view

df = query_view("finance_pnl")                        # notion_sync schema (default)
df = query_view("mv_call_spine", schema="analytics")   # any exposed schema
```

- Returns a pandas DataFrame with auto type coercion (dates, numbers, booleans)
- Cached for 5 minutes in Streamlit runtime
- New tabs should NOT manually call `pd.to_numeric` / `pd.to_datetime` — `query_view` handles it

### Chart Catalog (`core/charts.py`)

All Plotly charts return `go.Figure` — render with `st.plotly_chart(fig, use_container_width=True)`.
All ECharts charts return `dict` — render with `st_echarts(config, height="250px")`.

| Function | Type | Use For |
|----------|------|---------|
| `area_chart(df, x, y_cols, title)` | Plotly | Time series trends, multi-line |
| `horizontal_bar_chart(df, y, x, title)` | Plotly | Ranked lists, leaderboards |
| `stacked_bar_chart(df, x, y, color, title)` | Plotly | Category breakdowns over groups |
| `funnel_chart(df, stage, value, title)` | Plotly | Pipeline stages |
| `heatmap_chart(df, x, y, z, title)` | Plotly | Cross-tab intensity (auto-pivots) |
| `treemap_chart(df, path, values, title)` | Plotly | Hierarchical part-of-whole |
| `scatter_timeline(df, x, y, size, color, title)` | Plotly | Date scatter with bubble sizing |
| `choropleth_map(df, locations, color, title)` | Plotly | US state maps |
| `status_bars(items, title)` | Plotly | Reconciliation progress bars |
| `gauge_chart(value, title)` | ECharts | Single KPI percentage |
| `donut_chart(labels, values, title)` | ECharts | Part-of-whole breakdown |
| `radar_chart(indicators, series_data, title)` | ECharts | Multi-axis entity comparison |

Optional params on most charts: `color_map` (dict of value→hex), `color` (column name for grouping). See docstrings in `core/charts.py` for full signatures and examples.

### UI Components (`core/components.py`)

All return HTML strings — render with `st.html()`.

| Function | Use For |
|----------|---------|
| `kpi_strip_html(items)` | Row of metric cards at top of tab |
| `detail_panel_html(title, fields)` | Key-value drill-through on row select |
| `status_pill_html(text, status)` | Colored badge (PASS/FAIL/WARN) |

### Theme (`core/theme.py`)

- `COLORS` dict: navy, blue, blue_dark, blue_light, bg, white, border, slate, success, warning, error
- `COLOR_SEQUENCE`: 8-color palette for multi-series charts
- `plotly_template()`: full Plotly template (auto-applied by chart functions)
- `echarts_theme()`: ECharts theme dict

### Standard Tab Pattern

Every tab follows this structure:

```python
def render():
    df = query_view("view_name")
    if df.empty:
        st.warning("No data available.")
        return

    # KPIs
    st.html(kpi_strip_html([...]))

    # Charts in columns
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(some_chart(df, ...), use_container_width=True)
    with col2:
        st_echarts(gauge_chart(...), height="250px")

    # Data table with row selection
    event = st.dataframe(df[table_cols], on_select="rerun", selection_mode="single-row", ...)

    # Detail panel on selection
    if event.selection.get("rows", []):
        row = df.loc[show_df.index[event.selection["rows"][0]]]
        st.html(detail_panel_html("Title", {"Field": str(row["col"])}))
```

### Available notion_sync Views (17)

**Finance:** finance_close_dashboard, finance_pnl, finance_ar_aging, finance_variance, finance_accounting_inbox
**Sales:** sales_rfp_pipeline, sales_deals, sales_opportunities, sales_prospects, sales_state_profiles, sales_inbox
**Support:** calls_weekly, calls_by_topic, calls_by_agent, calls_log, tickets_monthly, tickets_log

### Available analytics Views/Matviews

Use with `query_view("name", schema="analytics")`:
- `mv_call_spine` — denormalized call data (all sources, deduped, department-tagged)
- `mv_customer_intel` — enriched customer 360
- `dim_customer` — core customer dimension
- `dim_org` — team directory (people, queues, phone lines)

## Reference Documents

- `reference/B4ALL_Notion_Database_Scaffolding_Plan.md` — Historical. Database-per-hub approach was abandoned.
- `reference/notion_data_model_blueprint.md` — Aspirational MDM architecture. Directional guide only.
- `reference/B4ALL_Notion_Architecture_Blueprint.md` — Hub structure reference. The hubs are now built as standalone page trees, not database-backed views.
