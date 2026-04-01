# B4ALL Command Center

Central workspace for all Biometrics4ALL (B4ALL) data infrastructure, automation, and operations tooling.

## Supabase

**The ONLY Supabase project is B4All-Hub (`dozjdswqnzqwvieqvwpe`).** No other project exists. All schemas, data, edge functions, and cron jobs live here.

## HubSpot Safety

All HubSpot write operations (create, update, delete, archive, merge, batch) require explicit user confirmation before execution. Read-only operations (search, get, list) may proceed freely.

## Project Map

| Directory | Purpose | Has CLAUDE.md |
|---|---|---|
| `projects/automation-layer/` | Automation registry — 447 automations, SLO health, dependency graph | Yes |
| `projects/resolution-wizard/` | HubSpot resolution pipeline — identity matching, writeback, diffs | Yes |
| `projects/finance-wizard/` | Finance/P&L tooling | No |
| `projects/bland-hub/` | Bland AI voice agent management | No |
| `projects/notion/` | Supabase → Notion data sync | Yes |
| `projects/file-drive-analysis/` | File/drive analysis tooling | No |
| `projects/security-hardening/` | Security audit and hardening | No |
| `knowledge-base/` | Obsidian vault — schema docs, templates | — |
| `scripts/` | Shared scripts | — |
| `supabase/` | Supabase CLI config, migrations | — |

## Key Identifiers

- `client_id` is the universal join key across all customer data
- HubSpot company names follow `Name|CLIENT_ID|LSID` convention (intentional)
- `b4all_client_id` property in HubSpot is dead — `client_id` is the operational field
- `b4all_classification` is an enum (Client/Lead/Vendor/System)

## Data Querying Rules

- **Always use analytics matviews/views** — never query `raw_*` schemas directly
- **Revenue = GROSS** (includes gov fee passthroughs) — never restate as net
- **Volume** comes from `mv_unit_economics_monthly.volume` only — never COUNT(*) on revenue tables
- **Calls** come from `mv_call_spine` — use `WHERE transfer_source IS NULL` to avoid double-counting
- **SELECT only** — never INSERT, UPDATE, DELETE, CREATE, ALTER, DROP, or REFRESH

## Directory Discipline

When launching Claude from this directory, you have access to all subprojects. For focused work on a single workstream, launch Claude from that project's directory instead — it will pick up its own CLAUDE.md with detailed context.
