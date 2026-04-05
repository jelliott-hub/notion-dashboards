# Notion Data Syncing

## Overview
Supabase `notion_sync` schema contains clean, summary-level views designed to port into Notion databases. Views sit on top of analytics matviews/dims/raw tables — no data duplication.

## notion_sync Schema — Current Views

### Support (calls + tickets)
| View | Source | Rows | Description |
|---|---|---|---|
| `calls_weekly` | `analytics.mv_call_spine` | ~152 | Week x dept x source_system. Deduped, excludes after-hours. |
| `calls_by_agent` | `analytics.mv_call_spine` | ~22 | Month x agent performance. |
| `calls_by_topic` | `analytics.mv_call_spine` | ~555 | Month x support_category/topic. |
| `calls_log` | `analytics.mv_call_spine` | ~2,700 | Rolling 30-day individual calls. No transfer legs, no after-hours. |
| `tickets_monthly` | `analytics.mv_ticket_ops_monthly` | ~42 | Month x pipeline SLA dashboard. |
| `tickets_log` | `analytics.fact_tickets` + `dim_customer` | ~722 | Rolling 30-day tickets. Excludes AUTO_CLOSE noise. |

### Sales (Daniel's workspace)
| View | Source | Rows | Description |
|---|---|---|---|
| `sales_deals` | `analytics.v_client_deals` | ~339 | All non-lost deals. Board by stage, filter by pipeline. |
| `sales_inbox` | `raw_emails.messages` | ~83 | Rolling 3-day feed from dalmodovar + sales mailbox. No junk/deleted/sent. |
| `sales_opportunities` | `market.v_gov_bid_alerts` + `v_recompete_pipeline` + `v_federal_pipeline` | ~1,430 | Unified & normalized with source_type column. |
| `sales_state_profiles` | `market.dim_state_profile` | 51 | State-by-state playbook: channeler model, fees, scores, competitors. |
| `sales_regulatory_changes` | `market.v_regulatory_inbox` | 3 | New fingerprinting mandates (sales triggers). |
| `sales_prospects` | `market.v_prospect_scored` | ~3,085 | Top-tier prospects only (Tier 1A/1B/2/3). Scored & ranked. |

### Accounting Email (under Finance, NOT Support)
Not yet created as notion_sync views, but planned:
| View | Source | Rows | Description |
|---|---|---|---|
| `acct_email_queue` | `analytics.v_email_queue_snapshot` | 10 | Live backlog by assignee/folder. |
| `acct_email_throughput` | `analytics.v_email_completion_monthly` | 64 | Monthly email completion by assignee. |

## Notion Databases Created

### Sales Hub (parent page: 1d8d15530fe642468c9447d092f869e0)

| Database | Notion DB ID | Data Source ID | Status |
|---|---|---|---|
| Deals Pipeline | `be4c0e102edf4681a880febfcda0a615` | `047af068-9ff5-457a-91b8-23eb984c9e61` | Schema only (empty) |
| Inbox Feed | `60749fe04d324d13b4e65574a8377505` | `4971734b-b3b2-4487-9b12-a967ccf0c975` | Schema only (empty) |
| Opportunities | `f68f3711e8804d66a72b818a52b148c4` | `0d862a34-adad-43e6-8808-4b6ea4d06a18` | Schema only (empty) |
| State Profiles | `64fad32f896340babacad746d103d29d` | `4724f118-f20e-4b8b-968b-27719cd54ab5` | POPULATED (51 rows) |
| Regulatory Changes | `64809ea40a0b43369f5626bcd5dd4b69` | `be34c37b-c45d-40fe-9ff2-9e1313b63dd5` | POPULATED (3 rows) |
| Prospects | `254588a57681454fabdb5ed144d5e4e1` | `5732db7f-eb0b-4f90-88ca-ea2494063ff5` | Schema only (empty) |

## Supabase Migrations Applied

1. `notion_sync_call_views` — calls_weekly, calls_by_agent, calls_by_topic, calls_log
2. `notion_sync_replace_calls_by_customer_with_log` — dropped calls_by_customer, added calls_log (rolling 30-day)
3. `notion_sync_sales_views_v2` — all 6 sales_* views
4. `notion_sync_support_ticket_views` — tickets_monthly, tickets_log
5. `notion_sync_fix_tickets_log_include_unclassified` — fixed tickets_log to include unclassified tickets (exclude only AUTO_CLOSE)

## Data Population Strategy (TODO)

**Populated via Notion MCP:**
- State Profiles (51 rows) — done
- Regulatory Changes (3 rows) — done

**Needs sync solution for remaining databases:**
- Deals (339 rows), Inbox (83), Opportunities (1,430), Prospects (3,085)
- Support views not yet in Notion

**Options considered:**
- WhaleSync — Postgres-to-Notion sync, charges per record (record = row)
- Supabase Edge Function + Cron — free, custom code, ~20 min full sync at 3 req/sec
- CSV export → manual Notion import — quickest interim solution
- n8n workflow — visual, already connected

**CSV Export approach (in progress):**
- psycopg2 installed in `/tmp/csv-export` venv
- Target export dir: `~/commandcenter/notion-exports/`
- Script not yet written

## Key Notes

- `v_email_queue_snapshot` and `v_email_completion_monthly` are ACCOUNTING inbox, not Support
- Raw email mailboxes synced: accounting (107K), dalmodovar (28K), sales (27K) — no support mailbox
- All call views filter `transfer_source IS NULL` (dedup) and `exclude_from_metrics = false` (no after-hours)
- calls_weekly separates Bland vs DialPad via `source_system` column
- tickets_log excludes `ops_disposition = 'AUTO_CLOSE'` (noise + notification auto-closes)
- sales_prospects filtered to Tier 1A/1B/2/3 only (~3K vs 29K full set)
- sales_opportunities normalized across 3 source views with different schemas into common columns

## Next Steps

- [ ] Export all notion_sync views as CSVs for manual Notion import
- [ ] Build Finance views (pnl_monthly, ar_aging, close_dashboard, variance_analysis, payment_processors)
- [ ] Build Executive views (company_pulse, cohort_retention, anomalies, insight views)
- [ ] Set up automated sync pipeline (WhaleSync, Edge Function, or n8n)
- [ ] Create Notion databases for Support and Finance hubs
