# B4ALL Notion Database Scaffolding Plan

**Generated:** March 31, 2026
**Scope:** Read-only operational dashboards powered by Supabase data warehouse + HubSpot CRM
**Current State:** Notion workspace is a clean slate — documentation/KB only, zero operational databases exist

---

## Executive Summary

After scanning 49 Supabase data surfaces, 4 HubSpot object types (103K+ records), 994 knowledge base files, Fireflies meeting data, and the full Notion workspace, here's the scaffolding plan for B4ALL's Notion operational layer.

The workspace currently has **zero operational databases** — it's purely a knowledge base. That's actually ideal: clean slate, no migration debt.

**Recommended: 12 interconnected Notion databases** organized into 4 tiers, pulling from the data warehouse via synced/embedded views or manual periodic snapshots.

---

## Tier 1: Core Operational Databases (Build First)

### Database 1: 🏢 Customer Master
**Source:** `mv_customer_intel` (4,154 rows, 125+ columns) + `v_customer_health`
**Purpose:** Single source of truth for every customer — replaces scattered HubSpot/spreadsheet lookups

| Property | Type | Source Column | Notes |
|---|---|---|---|
| Customer Name | Title | customer_name | Primary identifier |
| Client ID | Text | client_id | B4ALL canonical ID |
| Parent Org | Text | parent_customer_name | Roll-up parent (37 groups) |
| Segment | Select | accounting_bucket | Service Center, SaaS, PSC, LE, Public SC, Partner |
| Status | Select | status | Active, Inactive, Churned |
| Health Score | Number | health_score | 0-100 composite |
| TTM Revenue | Number ($$) | ttm_revenue | Trailing 12-month |
| Monthly Avg Revenue | Number ($$) | avg_monthly_revenue | |
| Scan Volume (Monthly) | Number | volume | Contract + Relay |
| Device Count | Number | device_count | Active BLSIDs |
| State | Text | state | Primary state |
| Payment Type | Select | payment_type | ACH/Invoice |
| Last Revenue Month | Date | last_revenue_month | Churn signal |
| Last Interaction | Date | last_interaction | Gone-silent signal |

**Views to Create:**
- **All Active Customers** — Table, filtered status = Active, sorted by TTM Revenue desc
- **At-Risk Customers** — Table, filtered health_score < 50, sorted asc
- **By Segment** — Board, grouped by accounting_bucket
- **Parent Org Roll-Up** — Table, grouped by parent_customer_name with revenue sums
- **Geographic View** — Table, grouped by state

**Risk Flags (Checkbox properties):**
- Revenue Decline (YoY down >30%)
- Gone Silent (no interaction 180+ days)
- Escalation Risk (>2 escalations)
- Ticket Backlog (>5 open)
- AR Risk (>$10K outstanding)
- Churn Risk (composite flag)

---

### Database 2: 🎫 Support Tickets
**Source:** `v_client_tickets` (41 columns) + `fact_tickets` (57,866 rows)
**Purpose:** Ticket triage, SLA monitoring, topic analysis

| Property | Type | Source Column | Notes |
|---|---|---|---|
| Subject | Title | subject | |
| Ticket ID | Text | hubspot_ticket_id | |
| Customer | Relation | → Customer Master | Via client_id |
| Status | Select | status | Open, In Progress, Closed |
| Priority | Select | priority | |
| Pipeline | Select | pipeline | |
| Channel | Select | channel | Email, Phone, Chat |
| Persona | Select | sender_persona | Operator vs Applicant |
| Support Cluster | Text | support_cluster | ML-classified topic |
| Parent Category | Select | parent_category | 25 parent categories |
| Escalation | Checkbox | escalation | |
| Created | Date | created_at | |
| Closed | Date | closed_at | |
| Resolution Hours | Number | resolution_hours | |
| First Response Hours | Number | first_response_hours | |
| SLA Status | Select | sla_status | Met, Breached |
| Agent | Text | agent_name | |
| Ops Disposition | Select | ops_disposition | |
| Support Effort | Select | support_effort | High, Medium, Low |

**Views to Create:**
- **Open Tickets** — Table, filtered status != Closed, sorted by created_at desc
- **Escalations** — Table, filtered escalation = true
- **By Topic** — Board, grouped by parent_category
- **SLA Dashboard** — Table, filtered sla_status = Breached
- **By Customer** — Table, grouped by Customer relation
- **Agent Workload** — Board, grouped by agent_name

---

### Database 3: 💰 Deals Pipeline
**Source:** HubSpot Deals (1,711 records) + `v_client_deals` / `fact_deals`
**Purpose:** Sales pipeline visibility, forecast tracking

| Property | Type | Source Column | Notes |
|---|---|---|---|
| Deal Name | Title | dealname | |
| Customer | Relation | → Customer Master | Via b4all_client_id |
| Pipeline | Select | b4all_pipeline_label | Service Centers, Partnership |
| Stage | Select | b4all_stage_label | Human-readable stages |
| Amount | Number ($$) | amount | |
| Forecast Amount | Number ($$) | hs_forecast_amount | |
| Close Date | Date | closedate | |
| Days in Pipeline | Number | days_in_pipeline | |
| Owner | Person/Text | hubspot_owner_id | Map to team member |
| Closed Won | Checkbox | is_closed_won | |
| Closed Lost | Checkbox | is_closed_lost | |
| Loss Reason | Text | loss_reason | |
| Classification | Select | b4all_classification | |
| Deal Source | Text | deal_source | |

**Views to Create:**
- **Active Pipeline** — Board, grouped by Stage, filtered !closed
- **Won This Quarter** — Table, filtered closed_won + date range
- **Lost Deals** — Table, filtered closed_lost, sorted by amount desc
- **By Owner** — Board, grouped by Owner
- **Forecast** — Table, showing forecast_amount by close_date month

---

### Database 4: 📞 Call Activity Log
**Source:** `fact_calls` (31,772+ rows) + `mv_call_spine`
**Purpose:** Call volume tracking, Bland AI monitoring, queue performance

| Property | Type | Source Column | Notes |
|---|---|---|---|
| Call ID | Title | source_call_id | |
| Customer | Relation | → Customer Master | Via customer_key |
| Source System | Select | source_system | Bland, Dialpad, GoTo |
| Direction | Select | direction | Inbound, Outbound |
| Outcome | Select | outcome | Connected, Abandoned, Voicemail |
| Queue | Text | queue_name | |
| Talk Duration (sec) | Number | talk_duration_seconds | |
| Wait Time (sec) | Number | wait_time_seconds | |
| Call Start | Date | call_start | |
| Has Transcript | Checkbox | has_transcript | |
| Support Cluster | Text | support_cluster | ML topic |
| Transfer Source | Text | transfer_source | NULL = unique call |
| Agent | Text | agent_name | |

**Views to Create:**
- **Today's Calls** — Table, filtered today, sorted by call_start desc
- **Bland AI Calls** — Table, filtered source_system = 'bland'
- **By Queue** — Board, grouped by queue_name
- **Missed/Abandoned** — Table, filtered outcome = abandoned/voicemail
- **Weekly Volume Trend** — (embed Recharts artifact or linked dashboard)

---

## Tier 2: Financial & Performance Databases

### Database 5: 📊 Monthly P&L Snapshot
**Source:** `v_pnl_monthly` + `mv_company_pulse` (38 rows, 49 columns)
**Purpose:** Monthly financial performance at a glance

| Property | Type | Source Column | Notes |
|---|---|---|---|
| Month | Title | month (formatted) | "March 2026" |
| Year | Number | year | |
| Total Income | Number ($$) | total_income | GROSS including passthroughs |
| SaaS Platform Net | Number ($$) | saas_platform_net | |
| Relay Net | Number ($$) | relay_net | |
| Solutions Total | Number ($$) | solutions_total | |
| Support Total | Number ($$) | support_total | |
| COGS Total | Number ($$) | cogs_total | |
| Gross Margin | Number ($$) | gross_margin | |
| Gross Margin % | Number (%) | calculated | gross_margin / total_income |
| Contract Volume | Number | contract_volume | Scans processed |
| Relay Volume | Number | relay_volume | Relay transmissions |
| NRR | Number (%) | nrr | Net Revenue Retention |
| GRR | Number (%) | grr | Gross Revenue Retention |

**Views to Create:**
- **YTD 2026** — Table, filtered year = 2026
- **Trailing 12 Months** — Table, last 12 rows
- **YoY Comparison** — Table, current vs prior year months side by side

---

### Database 6: 💸 AR Aging Tracker
**Source:** `fact_ar_aging` + `dim_customer`
**Purpose:** Collections visibility, outstanding invoice tracking

| Property | Type | Source Column | Notes |
|---|---|---|---|
| Invoice Number | Title | invoice_number | |
| Customer | Relation | → Customer Master | Via customer_key |
| Amount Due | Number ($$) | amount_due | |
| Days Outstanding | Number | days_outstanding | |
| Aging Bucket | Select | aging_bucket | Current, 30, 60, 90, 120+ |
| Invoice Date | Date | invoice_date | |
| Due Date | Date | due_date | |

**Views to Create:**
- **Past Due** — Table, filtered aging_bucket != Current, sorted amount desc
- **By Bucket** — Board, grouped by aging_bucket
- **Top 20 Outstanding** — Table, sorted by amount_due desc, limit 20
- **By Customer** — Table, grouped by Customer relation

---

### Database 7: 📈 Revenue by Customer (Monthly)
**Source:** `mv_customer_revenue_monthly` (52K+ rows)
**Purpose:** Customer-level revenue tracking, product mix, concentration analysis

| Property | Type | Source Column | Notes |
|---|---|---|---|
| Record ID | Title | generated | "Customer - Month - Category" |
| Customer | Relation | → Customer Master | Via client_id |
| Month | Date | revenue_month | |
| Revenue Category | Select | revenue_category | 8 categories |
| Amount | Number ($$) | amount | |
| Is Passthrough | Checkbox | is_passthrough | Gov Fees, SAM Credits |
| Is COGS | Checkbox | is_cogs | |
| Business Line | Text | business_line | |

**Views to Create:**
- **Top 20 Customers (TTM)** — Table, aggregated by customer, sorted desc
- **By Revenue Category** — Board, grouped by revenue_category
- **Passthrough vs Net** — Filtered views for passthrough analysis
- **Concentration Dashboard** — (embed chart showing top customer %)

---

## Tier 3: Workflow & Process Databases

### Database 8: 📋 Implementation Tracker
**Source:** `v_dock_workspace_events` (576 rows) + `v_pandadoc_document_events` (1,744 rows)
**Purpose:** Track new customer onboarding through implementation stages

| Property | Type | Source Column | Notes |
|---|---|---|---|
| Company Name | Title | company_name | From Dock events |
| Customer | Relation | → Customer Master | |
| Client Code | Text | client_code | |
| Current Step | Select | impl_step_name | Dock implementation step |
| Step Number | Number | impl_step_number | |
| Last Activity | Date | event_date | Most recent workspace event |
| Event Type | Select | event_type | workspace_activity, heating_up, re_engage |
| PandaDocs Status | Select | derived | From PandaDoc events |
| Docs Completed | Number | count | Completed PandaDocs |
| Templates Pending | Multi-Select | doc_template | maintenance_agreement, payment_auth, etc. |

**PandaDoc Template Types to Track:**
- maintenance_agreement
- payment_auth
- connection_diagram
- services_agreement
- loaner_agreement
- electronic_payment
- affiliate_membership

**Views to Create:**
- **Active Implementations** — Board, grouped by Current Step
- **Stalled** — Table, filtered last_activity > 14 days ago
- **Docs Pending** — Table, filtered by incomplete PandaDocs
- **By Implementation Step** — Kanban board

---

### Database 9: 🔄 Churn Watchlist
**Source:** `mv_churn_watchlist` (rich churn prediction data)
**Purpose:** Proactive retention — flag and track at-risk customers

| Property | Type | Source Column | Notes |
|---|---|---|---|
| Customer Name | Title | customer_name | |
| Customer | Relation | → Customer Master | |
| Risk Level | Select | risk_level | likely_churned, at_risk, active |
| Churn Logic Type | Select | churn_logic_type | revenue_gap, maintenance |
| Risk Reason | Text | risk_reason | Narrative explanation |
| Months Since Revenue | Number | months_since_revenue | |
| TTM Revenue | Number ($$) | ttm_revenue | |
| Last Revenue Month | Date | last_revenue_month | |
| Payment Type | Select | payment_type | |
| Coverage Months | Number | coverage_months | Maintenance coverage |
| Churn Deadline | Date | churn_deadline | Grace period expiry |
| Consecutive Zero Months | Number | consecutive_zero_months | |
| Business Lines | Multi-Select | business_lines | Array of active lines |
| Device Count | Number | device_count | |

**Views to Create:**
- **Likely Churned** — Table, filtered risk_level = likely_churned
- **At Risk (Saveable)** — Table, filtered risk_level = at_risk, sorted TTM revenue desc
- **By Churn Logic** — Board, grouped by churn_logic_type
- **Expiring Coverage** — Table, sorted by churn_deadline asc
- **Revenue at Risk** — Table, sorted by TTM revenue desc

---

### Database 10: 🤖 Bland AI Performance Log
**Source:** `raw_calls.bland_pulse()` + `raw_calls.bland_topic_pulse()` + `raw_calls.bland_transfer_summary()`
**Purpose:** Monitor AI voice agent "Alex" performance daily

| Property | Type | Source Column | Notes |
|---|---|---|---|
| Date | Title | snapshot_date | Daily snapshot |
| Total Calls | Number | total_calls | |
| Transfer Rate | Number (%) | transfer_rate | Target: <50% |
| Avg Duration (sec) | Number | avg_duration | |
| Short Call % | Number (%) | short_call_pct | <30s = likely failures |
| Completed | Number | completed | |
| Errors | Number | errors | |
| Top Topic | Text | top_topic | From topic_pulse |
| Escalation Rate | Number (%) | escalation_rate | |

**Views to Create:**
- **Last 30 Days** — Table, sorted by date desc
- **Transfer Rate Trend** — (embed Recharts line chart)
- **Topic Breakdown** — Table from topic_pulse

---

## Tier 4: Strategic & Meeting Databases

### Database 11: 🗓️ Meeting Action Items
**Source:** Fireflies meeting transcripts (20+ recent meetings)
**Purpose:** Capture and track action items from team meetings

| Property | Type | Notes |
|---|---|---|
| Action Item | Title | From Fireflies action items |
| Meeting | Text | Meeting title |
| Meeting Date | Date | |
| Owner | Person | Assigned team member |
| Status | Select | Not Started, In Progress, Done |
| Priority | Select | High, Medium, Low |
| Due Date | Date | |
| Workstream | Select | Sales, Engineering, Support, Finance, Partnerships |
| Notes | Text | Context from transcript |

**Views to Create:**
- **My Action Items** — Table, filtered by Owner = me
- **Overdue** — Table, filtered due_date < today AND status != Done
- **By Workstream** — Board, grouped by Workstream
- **By Meeting** — Table, grouped by Meeting

---

### Database 12: 📬 HubSpot Sequence Tracker
**Source:** HubSpot Contacts (28K+) with sequence properties + `raw_hubspot.sequences` (38 sequences)
**Purpose:** Track sales sequence enrollment and engagement

| Property | Type | Source Column | Notes |
|---|---|---|---|
| Contact Name | Title | hs_full_name_or_email | |
| Company | Relation | → Customer Master | Via b4all_client_id |
| Currently Enrolled | Checkbox | hs_sequences_is_enrolled | |
| Sequence Name | Text | hs_latest_sequence_enrolled | |
| Enrolled Date | Date | hs_latest_sequence_enrolled_date | |
| Ended Date | Date | hs_latest_sequence_ended_date | |
| Total Enrollments | Number | hs_sequences_enrolled_count | |
| Response | Text | sequence_response | |
| Lifecycle Stage | Select | lifecyclestage | Lead, Customer |
| Owner | Text | hubspot_owner_id | |
| Classification | Select | b4all_classification | |

**Views to Create:**
- **Currently Enrolled** — Table, filtered is_enrolled = true
- **By Sequence** — Board, grouped by Sequence Name
- **Response Tracking** — Table, filtered response != null
- **By Owner** — Board, grouped by Owner

---

## Embeddable Dashboards & Charts

Notion supports embedded content. For each of these, create a Recharts-powered HTML artifact hosted on Vercel or embed via iframe:

| Dashboard | Data Source | Chart Type | Refresh |
|---|---|---|---|
| **Revenue Trend (12mo)** | mv_customer_revenue_monthly | Multi-line (by business line) | Weekly |
| **Call Volume Heatmap** | fact_calls | Bar chart (by week, by source) | Daily |
| **Support Topic Distribution** | dim_support_cluster | Horizontal bar | Weekly |
| **Customer Concentration** | mv_customer_concentration | Pie + HHI line | Monthly |
| **Retention Waterfall** | mv_revenue_waterfall | Waterfall chart | Monthly |
| **Bland AI Transfer Rate** | bland_pulse() | Line chart (daily trend) | Daily |
| **AR Aging Buckets** | fact_ar_aging | Stacked bar by bucket | Weekly |
| **Health Score Distribution** | v_customer_health | Histogram | Weekly |

---

## Relationship Map

```
Customer Master (hub)
├── Support Tickets (1:many via client_id)
├── Deals Pipeline (1:many via b4all_client_id)
├── Call Activity Log (1:many via customer_key)
├── AR Aging Tracker (1:many via customer_key)
├── Revenue by Customer (1:many via client_id)
├── Implementation Tracker (1:many via client_code)
├── Churn Watchlist (1:1 via client_id)
└── Sequence Tracker (1:many via b4all_client_id)

Monthly P&L Snapshot (standalone — company-level)
Bland AI Performance Log (standalone — system-level)
Meeting Action Items (standalone — team-level)
```

---

## Data Refresh Strategy

Since these are **read-only** Notion databases (no write-back to Supabase), the refresh approach matters:

| Option | Pros | Cons | Recommended For |
|---|---|---|---|
| **Manual CSV Import** | Simple, no infra | Stale data, manual effort | Monthly P&L, AR Aging |
| **Notion API Sync Script** | Automated, scheduled | Requires Edge Function | Customer Master, Tickets, Churn |
| **Embedded Vercel Dashboards** | Real-time, rich charts | Separate hosting | Revenue trends, call heatmaps |
| **HubSpot → Notion Sync** | Native integration | Limited to HubSpot data | Deals, Sequences |

**Recommended Architecture:**
1. Build a Supabase Edge Function that queries matviews and pushes to Notion API (nightly cron)
2. Use HubSpot's native Notion integration for Deals and Contacts
3. Embed Vercel-hosted Recharts dashboards for real-time visualizations
4. Manual monthly refresh for P&L and financial snapshots

---

## Implementation Priority

| Phase | Databases | Timeline | Dependencies |
|---|---|---|---|
| **Phase 1** | Customer Master, Churn Watchlist | Week 1 | Supabase matview data |
| **Phase 2** | Support Tickets, Deals Pipeline | Week 2 | HubSpot sync |
| **Phase 3** | Monthly P&L, AR Aging, Revenue by Customer | Week 3 | Financial data exports |
| **Phase 4** | Call Activity, Bland AI Log | Week 4 | Call data pipeline |
| **Phase 5** | Implementation Tracker, Sequence Tracker, Meeting Items | Week 5 | Dock/PandaDoc/Fireflies data |
| **Phase 6** | Embedded dashboards & charts | Week 6 | Vercel hosting |

---

## Data Sources Inventory (What We Found)

### Supabase (49 surfaces discovered)
- 23 materialized views in analytics schema
- 25 active views in analytics schema
- 1 lookup materialized view
- Key surfaces: mv_customer_intel (4,154 rows), mv_company_pulse (38 rows), fact_calls (31,772), fact_tickets (57,866), mv_customer_revenue_monthly (52K+), fact_ar_aging, mv_churn_watchlist

### HubSpot CRM (103K+ records)
- 1,711 Deals across 3 pipelines with B4ALL custom properties
- 28,149 Contacts with sequence tracking and B4ALL classification
- 23,648 Companies with B4ALL client_id matching and segment tags
- 49,370 Tickets with AI-classified intent, topic, and segment
- 38 Sales Sequences
- 152 Workflows

### Workflow Data in Supabase
- PandaDocs: 1,744 document lifecycle events (7 template types)
- Dock: 576 implementation workspace events with step tracking
- Emails: 63K+ Outlook emails in fact_emails with classification
- Tasks: HubSpot tasks with sequence linkage (3-layer pipeline: raw → cleanup → intelligence)
- Automations: 436 federated automations across 12 sources (dim_automation)

### Fireflies
- 20+ recent meetings with structured action items
- 5 workstreams identified: Sales, Engineering, Support, Finance, Partnerships
- Rich keyword extraction and topic segmentation

### Notion (Current State)
- Pure knowledge base — 994 markdown files, zero operational databases
- 1 teamspace, 2 users, 2 bots
- Clean slate for database scaffolding

### Asana
- Referenced in Notion as connected to HubSpot
- No data in Supabase warehouse
- All task tracking flows through HubSpot tasks pipeline

---

## Key Business Context

- ~$18.5M annual revenue across 4 business lines
- 1,000+ LiveScan locations, primarily CA and FL
- 4,154 customers in master dimension, ~500 truly active
- 37 parent org groups rolling up 378 child locations
- Seasonal peak in August (back-to-school background checks)
- Government hiring leads scan volume by 2-3 months (r=0.76)
- Support team of 4: Greg, Mayuri, Row, Randy
- Bland AI "Alex" handles ~50% of inbound support (23.5% transfer rate last 24h)
- ACH autopay customers are 2x less likely to lapse

---

*This plan was generated from 10 parallel research agents scanning Supabase, HubSpot, Notion, Fireflies, Asana, and the B4ALL knowledge base.*
