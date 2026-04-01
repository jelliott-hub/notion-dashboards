# B4ALL Notion Data Project

Writes operational data from Supabase (B4All-Hub) into Notion workspace via MCP.

## Supabase

- **Only project:** B4All-Hub (`dozjdswqnzqwvieqvwpe`)
- Source data lives in `analytics` schema (fact tables, matviews, dims)
- `notion_sync` schema exists but is currently empty — reserved for future sync tracking tables

## Notion Workspace

- **B4ALL Home** — top-level page
- **Support Hub** (`33513d36-77c3-8126-9ef3-c1adb9235955`) — call data, tickets, customer lookup
- **Sales Hub** (`33513d36-77c3-8199-ade8-d362f90eca65`)
- **Finance Hub** (`33513d36-77c3-8163-a736-e984542f58eb`)
- **Executive Hub** (`33513d36-77c3-8148-9e91-de6fa1e3a3df`)
- **Automations Hub** (`33513d36-77c3-8101-acb4-c589b555ef45`)

## Active Databases in Notion

| Database | Notion ID | Hub | Source | Status |
|----------|-----------|-----|--------|--------|
| Customer Directory | `1240a41e-fa9a-4dee-98f7-a1a62a91364f` | Support | `analytics.dim_customer` | 20 rows loaded (POC) |
| Call Volume Daily | `7b68e6f5-6a82-4875-93fd-513f2e393fd5` | Support | `analytics.mv_call_spine` | 71 rows, trailing 30d |

## How Data Gets Into Notion

**Direct MCP writes.** No edge functions, no sync engine. Query Supabase, push via `notion-create-pages` with `data_source_id`.

Pattern:
1. Query `analytics.*` on B4All-Hub for the data
2. `notion-create-database` if the DB doesn't exist yet
3. `notion-create-pages` with `parent: { data_source_id: "..." }` to push rows
4. For refreshes: trash old DB, recreate, repush (until we build incremental)

## Key Matviews

- `analytics.mv_call_spine` — denormalized call data (all sources, deduped, department-tagged)
- `analytics.mv_customer_intel` — enriched customer 360 (exists but needs refresh)
- `analytics.dim_customer` — core customer dimension
- `analytics.dim_org` — team directory (people, queues, phone lines)

## Rules

- NEVER query any Supabase project other than B4All-Hub
- Always use `data_source_id` (not `database_id`) for Notion writes
- Refresh `mv_call_spine` before pushing call data: `REFRESH MATERIALIZED VIEW analytics.mv_call_spine`
- Select options must be added to Notion schema before writing rows with new values
