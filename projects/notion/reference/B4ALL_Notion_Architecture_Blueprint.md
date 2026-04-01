# B4ALL Notion Workspace Architecture Blueprint

**Date:** March 31, 2026
**Author:** Jack Elliott + Claude (Architecture Session)
**Status:** READY FOR REVIEW
**Companion Doc:** B4ALL_Notion_Hub_Vision_Brief.md (Data Sync Layer)

---

## Executive Summary

This document architects B4ALL's entire Notion workspace — not just the Supabase data sync layer (covered in the Vision Brief), but the **complete information architecture** that turns Notion into B4ALL's company intranet, operational nervous system, and employee home base. It synthesizes findings from five parallel research streams: the 996-article knowledge base, Supabase data warehouse (465 tables across 25+ schemas), Microsoft Teams organizational signals, HubSpot CRM structure, Outlook communication patterns, and current Notion best practices for enterprise workspaces.

The architecture is organized into three layers:

1. **Functional Hubs** — The core content and data workspaces employees actually use daily
2. **Organizational Overlay** — Teamspaces, permissions, navigation, and governance that control who sees what
3. **Onboarding Layer** — Self-service new hire experience that uses the other two layers

---

## Current State Assessment

### What Exists Today

| Asset | State | Notes |
|-------|-------|-------|
| Notion Workspace | Active | "Jack Elliott's Space HQ" teamspace |
| Users | 1 human + 2 bots | Jack Elliott + Notion MCP + antigravity bot |
| B4ALL Knowledge Base | Imported | ~1,000 articles, flat page structure |
| Operational Dashboards | Live | 5 dashboards syncing from Supabase every 20min |
| Supabase Data Warehouse | Production | 465 tables, 25+ schemas, 45+ materialized views |
| Knowledge Base (filesystem) | Production | 996 markdown files, 10 top-level sections |
| Microsoft Teams | Active | 2 teams, 8 channels, 28 team members, 4,958 messages |
| HubSpot CRM | Active | 1,627 deals, 23,287 companies, 152 workflows |
| Outlook/Email | Active | 162,626 emails, 6,615 senders, 3 mailboxes |

### Key Insight

B4ALL is a **28-person company** (identified from Teams data) with 5 distinct operational personas (Support, Sales, Finance, Executive, Automations/Ops). The workspace needs to feel like a personalized intranet for each persona while maintaining a unified company identity. The existing Operational Dashboards page proves the Supabase→Notion sync pattern works. The knowledge base import establishes Notion as the documentation home. What's missing is **the connective tissue** — the hub structure, navigation, cross-references, and organizational intelligence that turns a collection of pages and databases into a living workspace.

---

## LAYER 1: FUNCTIONAL HUBS

The workspace is organized around **7 Functional Hubs**. Each hub is a top-level page containing related databases, documentation, and dashboards. The hub model follows a "hub-and-spoke" pattern where each hub serves a clear behavioral purpose — people come to it when they need something specific.

### Hub Architecture Overview

```
🏠 B4ALL Home (Company Portal)
│
├── 🎧 Support Hub
├── 💰 Sales Hub
├── 📊 Finance Hub
├── 👔 Executive Hub
├── ⚙️ Automations Hub
├── 📚 Knowledge Base
└── 👋 Welcome to B4ALL (Onboarding)
```

---

### HUB 0: 🏠 B4ALL Home (Company Portal)

**Purpose:** The front door. Every employee lands here. It's the intranet homepage that provides ambient awareness without requiring anyone to dig.

**Behavioral Trigger:** "What's happening at the company?" — checked daily, especially at day start and before meetings.

**Page Structure:**

```
🏠 B4ALL Home
├── Company Pulse Widget (inline DB view from Executive Hub)
│   └── Latest month: revenue, ticket closure rate, NRR%, call answer rate
├── 📢 Company Announcements (database)
│   └── Pinned + chronological, with author and audience tags
├── 🗓️ Company Calendar (database)
│   └── Key dates: maintenance windows, board meetings, compliance deadlines, team events
├── 👥 Team Directory (database)
│   └── Name, role, department, email, phone, photo, manager, start date
├── 🔗 Quick Links
│   └── ApplicantServices.com | ThinClient/CMS | HubSpot | QuickBooks | Dialpad | Keeper | CATO VPN
├── 🏗️ Active Projects (inline DB view)
│   └── Filtered to in-progress projects across all departments
└── 📊 Operational Dashboards (existing page — relocated under Home)
    └── Calls Monthly, Ticket Ops, Deal Pipeline, Automation Inventory, Automation Queues
```

**Key Databases:**

#### DB: Company Announcements
| Property | Type | Purpose |
|----------|------|---------|
| Title | Title | Announcement headline |
| Type | Select | Update / Policy Change / Milestone / Alert / Welcome |
| Audience | Multi-Select | All / Support / Sales / Finance / Engineering / Leadership |
| Author | Person | Who posted it |
| Date | Date | When posted |
| Priority | Select | Pinned / Normal / FYI |
| Status | Status | Active / Archived |

- **Views:** "Active Announcements" (default, filtered to Active, sorted by Priority then Date DESC), "My Department" (filtered to user's audience tag)
- **Sync:** Manual — this is human-authored content, not warehouse data
- **Governance:** Any teamspace admin can post. Jack or Brigid pin items.

#### DB: Team Directory
| Property | Type | Purpose |
|----------|------|---------|
| Name | Title | Full name |
| Role | Rich Text | Job title |
| Department | Select | Support / Sales / Finance / Engineering / Executive / Operations |
| Email | Email | @biometrics4all.com address |
| Phone | Phone | Direct line |
| Manager | Relation (self) | Reports to |
| Start Date | Date | Hire date |
| Status | Select | Active / On Leave / Departed |
| Hub Access | Multi-Select | Support / Sales / Finance / Executive / Automations |

- **Source:** Seeded from `raw_microsoft.user_email_lookup` (28 members identified) + manual enrichment
- **Views:** "All Team" (gallery with photos), "By Department" (board grouped by Department), "Org Chart" (list sorted by Manager relation)
- **Why not synced?** Team data changes rarely and benefits from human-curated fields (photos, bios, phone numbers) that don't exist in the warehouse

#### DB: Company Calendar
| Property | Type | Purpose |
|----------|------|---------|
| Event | Title | Event name |
| Date | Date | Start/end date |
| Type | Select | Maintenance Window / Board Meeting / Compliance Deadline / All-Hands / Team Event / Holiday |
| Owner | Person | Responsible party |
| Department | Multi-Select | Affected departments |
| Notes | Rich Text | Details |

- **Views:** "Calendar" (calendar view by Date), "Upcoming" (table filtered to future dates, sorted ASC), "By Type" (board grouped by Type)

---

### HUB 1: 🎧 Support Hub

**Purpose:** Everything a support rep needs during a call, ticket review, or daily standup. The most time-critical hub — sub-second lookups matter here.

**Behavioral Triggers:**
- "Who is this customer?" → Customer Directory
- "What's their device info?" → Device Directory
- "What's open?" → Ticket Board
- "Did they call recently?" → Call Log
- "How do I handle this?" → Knowledge Base (Support section)

**Page Structure:**

```
🎧 Support Hub
├── 📋 My Day (filtered view)
│   └── Open tickets assigned to me + recent calls for my customers
├── 🏢 Customer Directory (DB 1 from Vision Brief)
├── 🎫 Ticket Board (DB 2)
├── 📞 Call Log — Rolling 7 Days (DB 3)
├── 🖥️ Device Directory (DB 4)
├── 📈 Support Metrics
│   └── Monthly closure rate, avg response/resolution time, escalation count
│   └── Source: v_ticket_summary WHERE client_id IS NULL
├── 📚 Support Playbooks (linked view from Knowledge Base)
│   └── Filtered to: customer-success/*, products/*, technical/livescan-platform/*
└── 🔥 Escalation Tracker
    └── Linked view of Ticket Board filtered to escalation = true
```

**"My Day" Page Design:**

This is the default landing within Support Hub. It's a dashboard page that embeds filtered views:

1. **My Open Tickets** — Ticket Board filtered to `owner = @me AND status != Closed`
2. **Recent Calls for My Customers** — Call Log filtered to customers in my ticket queue
3. **Customers Needing Attention** — Customer Directory filtered to `days_since_interaction > 30 OR active_ticket_count > 3`
4. **Today's Support Metrics** — Inline summary: tickets opened today, closed today, avg response time today

**Databases:** All 4 databases (Customer Directory, Ticket Board, Call Log, Device Directory) are fully specified in the Vision Brief with schemas, sync cadences, and source views. They live under Support Hub but are **cross-referenced by every other hub** via the `client_id` relation through Customer Directory.

**Cross-Hub Relations:**
- Customer Directory → relates to Ticket Board, Call Log, Device Directory, Deal Pipeline, AR Aging, Unit Economics (via client_id)
- This makes Customer Directory the **master hub database** — the single node everything connects through

---

### HUB 2: 💰 Sales Hub

**Purpose:** Pipeline management, prospecting intelligence, and market strategy. Used daily for pipeline review and weekly for strategic planning.

**Behavioral Triggers:**
- "Where do my deals stand?" → Deal Pipeline
- "Who should I call in [state]?" → Prospect Priority
- "What's the competitive picture?" → Market Intelligence
- "Is anything changing regulatorily?" → Regulatory Inbox

**Page Structure:**

```
💰 Sales Hub
├── 🎯 Pipeline Dashboard
│   └── Board view of Deal Pipeline grouped by stage
│   └── Monthly win rate, avg cycle time, pipeline value by stage
├── 📊 Deal Pipeline (DB 5 from Vision Brief)
├── 🗺️ Market Intelligence — State Profiles (DB 6)
├── 🎯 Prospect Priority List (DB 7)
├── 📰 Regulatory Inbox (DB 8)
├── 💼 Sales Playbooks (linked view from Knowledge Base)
│   └── Filtered to: sales/playbooks/*, sales/pricing/*, sales/proposals/*
├── 📧 Sales Templates (linked view from Knowledge Base)
│   └── Filtered to: templates/sales-outreach/*, templates/quotes-and-contracts/*
└── 🏢 Customer Directory (linked view — Sales perspective)
    └── Filtered to: accounting_bucket = 'PSP' OR 'SAM' with revenue columns visible
```

**Pipeline Dashboard Design:**

The dashboard page aggregates deal intelligence:

1. **Pipeline Board** — Deal Pipeline as board view, grouped by stage, cards showing deal_name, customer_name, amount, days_in_stage
2. **Pipeline Summary** — From `mv_deal_pipeline_monthly`: deals created, won, lost this month; win rate; avg cycle time; total pipeline value
3. **My Deals** — Filtered to `owner = @me`
4. **Hot Prospects** — Prospect Priority List filtered to `priority_score > 80`, top 20

**HubSpot Integration Note:** The Deal Pipeline database syncs from `analytics.v_client_deals` which is a processed view of HubSpot data. There are 3 active pipelines (Service Centers at 1,015 deals, SaaS at 91 deals, RFPs at 3 deals). The sync preserves HubSpot's stage structure:

- **Service Centers:** Appointment Scheduled → Qualified → Presentation → Decision Maker Bought-In → Generate & Send Proposal → Negotiation → Closed Won/Lost
- **SaaS:** Discovery → Solution Alignment → Evaluation → Proposal & Negotiation → Commitment → Closed Won/Lost
- **RFPs:** RFP Identified → Analysis → [additional stages]

**Market Intelligence Views:**
- "Open Markets" — filtered to `channeler_model = open` (where B4ALL can operate)
- "Expansion Priority" — sorted by `composite_score DESC` (highest opportunity first)
- "By State" — gallery view with state profile cards showing demand score, competitors, penetration

---

### HUB 3: 📊 Finance Hub

**Purpose:** GL reference, customer identity reconciliation, AR collections, and unit economics. Used during journal entries, invoicing, reconciliation, and contract renewals.

**Behavioral Triggers:**
- "What GL code is this?" → GL Account Reference
- "Which customer is this in QuickBooks?" → Customer Identity Crosswalk
- "Who owes us?" → AR Aging Board
- "What's the fee-per-scan?" → Unit Economics

**Page Structure:**

```
📊 Finance Hub
├── 📖 GL Account / Contract Code Reference (DB 9 from Vision Brief)
├── 🔄 Customer Identity Crosswalk (DB 10)
├── 💵 AR Aging Board (DB 11)
├── 📐 Unit Economics (DB 12)
├── 📋 Finance Playbooks (linked view from Knowledge Base)
│   └── Filtered to: finance/*, including month-end close procedures
├── 📧 Finance Templates (linked view from Knowledge Base)
│   └── Filtered to: templates/email-accounting/*, templates/forms-financial/*
└── 🏢 Customer Directory (linked view — Finance perspective)
    └── Showing: customer_name, accounting_bucket, ar_balance, ttm_net_revenue, status
```

**AR Aging Board Design:**

This is the most action-oriented Finance database. Views:

1. **Board View** — Grouped by `aging_bucket` (Current, 1-30, 31-60, 61-90, 90+), sorted by `amount_due DESC`
2. **Top Debtors** — Table view sorted by `amount_due DESC`, top 25
3. **By Customer** — Table view grouped by `customer_name` with rollup of total outstanding
4. **Collections Focus** — Filtered to `aging_bucket IN ('61-90', '90+')` — these are the ones that need calls

**Identity Crosswalk Note:** This is a critical Finance tool because B4ALL's customer identifiers span 3 systems that don't always agree: QuickBooks (qb_customer_id), ThinClient (client_id/LSID), and HubSpot (hs_primary_company_id). The crosswalk lets Finance answer "which entity in system B matches this entity in system A?" without asking anyone.

---

### HUB 4: 👔 Executive Hub

**Purpose:** Monday morning pulse check, board prep, retention monitoring, and weekly operating rhythm. Designed for Brigid + leadership to get a 30-second "is the business healthy?" read.

**Behavioral Triggers:**
- "How's the business doing?" → Company Pulse
- "Who's at risk?" → Customer Health Board
- "Why did revenue change?" → Revenue Retention Waterfall
- "How did we do this week?" → Strety Scorecard

**Page Structure:**

```
👔 Executive Hub
├── 🫀 Company Pulse (DB 13 from Vision Brief)
│   └── Single-row-per-month executive dashboard
├── ⚠️ Customer Health Board (DB 14)
│   └── Filtered to customers with ≥1 active risk flag
├── 🌊 Revenue Retention Waterfall (DB 15)
│   └── Monthly bridge: beginning → changes → ending, NRR%, GRR%
├── 📊 Strety Scorecard (DB 16)
│   └── Weekly metrics: resolution hours, Bland AI %, call handling, escalations, sales win ratio
├── 🏢 Customer Directory (linked view — Executive perspective)
│   └── Showing: health_score, risk_flags, ttm_net_revenue, revenue_trend, tenure
└── 📈 Board Prep Resources
    └── Links to Revenue Waterfall, Customer Health, Company Pulse filtered views for board decks
```

**Company Pulse Page Design:**

This is the "executive homepage." It should show:

1. **Current Month Card** — Latest row from `mv_company_pulse` displayed as a rich page with key metrics highlighted: MRR, NRR%, ticket closure rate, call answer rate, active customer count
2. **Trend Table** — Last 6 months side-by-side for quick trend spotting
3. **Customer Health Summary** — Count of customers by health flag (red/yellow/green)
4. **Strety Snapshot** — Latest week's scorecard metrics inline

**Customer Health Board Views:**
- "At Risk" (default) — Filtered to `health_score < 50`, sorted by health_score ASC (worst first)
- "By Risk Type" — Board grouped by primary flag type (Revenue Decline, Gone Silent, Escalation Risk, Ticket Backlog, AR Risk)
- "Watch List" — Filtered to `health_score 50-70` (not critical but needs monitoring)

---

### HUB 5: ⚙️ Automations Hub

**Purpose:** The machine's control room. Used by Jack and anyone managing B4ALL's automation infrastructure (596 automations across multiple engines).

**Behavioral Triggers:**
- "Is the machine okay?" → Operations Summary
- "Are all chains green?" → Chain Health Monitor
- "What's broken?" → Incident Queue
- "Should we promote this draft?" → Draft Performance
- "What's waiting for review?" → Review Queue

**Page Structure:**

```
⚙️ Automations Hub
├── 🟢 Operations Summary (DB 22 from Vision Brief)
│   └── Single-row pulse: total automations, healthy/degraded/failing counts, open incidents
├── 🔗 Chain Health Monitor (DB 18)
│   └── Chain-level and step-level health with drill-down
├── 🚨 Incident Queue (DB 19)
│   └── Grouped by severity, filtered to open by default
├── 📋 Automation Registry (DB 17)
│   └── Full inventory: name, domain, engine, health, fire count, success rate
├── ✏️ Draft Performance (DB 20)
│   └── Approval rates, zero-edit rates, lane2 readiness for auto-send promotion
├── 📥 Review Queue (DB 21)
│   └── Opportunities, proposed configs, impact estimates awaiting review
└── 📚 Automations Playbooks (linked view from Knowledge Base)
    └── Filtered to: technical/*, projects/automation-*
```

**Operations Summary Page Design:**

This is the "ops homepage" — designed for a 10-second morning check:

1. **Health Banner** — Large status indicator: "ALL SYSTEMS GREEN" or "X INCIDENTS OPEN"
2. **Key Metrics** — Total automations, healthy %, open incidents, critical incidents, pending remediations
3. **Chain Health Grid** — Visual grid showing each chain as green/yellow/red
4. **Recent Incidents** — Last 5 incidents with status and time-to-ack

---

### HUB 6: 📚 Knowledge Base

**Purpose:** The existing 996-article knowledge base, restructured from a flat import into a navigable wiki organized by the same taxonomy as the filesystem.

**Current State:** Imported as a single page ("B4ALL Knowledge Base") with ~1,000 articles underneath. Needs restructuring into proper sections with navigation.

**Target Structure:**

```
📚 Knowledge Base
├── 🚀 Getting Started
│   ├── Company Overview (start-here, system-architecture, glossary)
│   ├── New Hire Orientation (week 1-3 learning paths)
│   └── Reference (quick reference materials)
├── 📦 Products
│   ├── Live Scan (LS4G)
│   ├── ApplicantServices.com
│   ├── CardScan
│   ├── CMS / ThinClient
│   ├── Enrollment API
│   └── FBI Channeling
├── 🔧 Technical
│   ├── LiveScan Platform (config, hardware, troubleshooting)
│   ├── Thin Client (CMS admin procedures)
│   ├── ApplicantServices (backend platform)
│   ├── Infrastructure
│   ├── Development
│   └── HubSpot (CRM technical reference)
├── 🎧 Customer Success
│   ├── Operator Support
│   ├── Applicant Support
│   ├── Submissions & Status
│   ├── Account Management
│   ├── Billing & Disputes
│   └── Workflows
├── 💼 Sales
│   ├── Playbooks
│   ├── Pricing
│   ├── New Providers
│   ├── Prospecting
│   └── Proposals
├── 💵 Finance
│   ├── Accounting Policies
│   ├── Chart of Accounts
│   ├── Payables & Receivables
│   ├── Reconciliation
│   └── Month-End Close
├── 🏗️ Implementation
│   ├── Client Onboarding
│   ├── System Deployment
│   └── CBID Configuration
├── 🔒 Compliance & Security
│   ├── CJIS & Federal
│   ├── Data Governance
│   ├── Security Policies
│   ├── HR Policies
│   └── Vendor Compliance
├── 🗺️ States
│   ├── California, Florida, New York, Illinois, Nevada, Oregon...
│   ├── Federal Programs
│   └── Tribal Nations
└── 📝 Templates
    ├── Quotes & Contracts
    ├── Customer Emails
    ├── Internal Operational
    └── Financial Forms
```

**Knowledge Base as Wiki:**

The Knowledge Base should be converted to a Notion Wiki (available on Business/Enterprise plans), which enables:
- **Verification badges** — Mark articles as reviewed and up-to-date
- **Article owners** — Assign knowledge ownership to specific people
- **Expiration dates** — Articles auto-flag when they need re-review
- **Notion AI Q&A** — Employees can ask natural language questions and get answers from the KB

**Article Database Properties (for Wiki conversion):**

| Property | Type | Purpose |
|----------|------|---------|
| Title | Title | Article name |
| Section | Select | Getting Started / Products / Technical / Customer Success / Sales / Finance / Implementation / Compliance / States / Templates |
| Audience | Multi-Select | Support / Sales / Finance / Engineering / All |
| Status | Status | Current / Needs Review / Archived |
| Owner | Person | Content owner responsible for accuracy |
| Last Reviewed | Date | Last verification date |
| Tags | Multi-Select | Live Scan / ApplicantServices / CardScan / ThinClient / Troubleshooting / SOP / Policy / etc. |

---

## LAYER 2: ORGANIZATIONAL OVERLAY

This layer controls who sees what, how people navigate, and who governs each section.

### Teamspace Architecture

Notion Teamspaces provide the permission boundary. Based on B4ALL's size (28 people) and departmental structure:

| Teamspace | Type | Members | Contains |
|-----------|------|---------|----------|
| **B4ALL** (General) | Open | Everyone (28) | 🏠 Home, 📚 Knowledge Base, 👋 Onboarding |
| **Support** | Closed | Greg, Mayuri, Rowealth, Randy + Support team | 🎧 Support Hub |
| **Sales** | Closed | Randy + Sales team, Daniel Almodovar | 💰 Sales Hub |
| **Finance** | Private | Finance team (Kathy Zimmerman, Christy, + others) | 📊 Finance Hub |
| **Leadership** | Private | Brigid Mulcahy, Daniel Almodovar, Jack Elliott | 👔 Executive Hub |
| **Operations** | Closed | Jack Elliott + Ops team | ⚙️ Automations Hub |

**Why this structure?**

- **Open Teamspace (B4ALL):** Contains everything everyone should see — Home, KB, Onboarding. Transparency by default.
- **Closed Teamspaces (Support, Sales, Operations):** Visible in sidebar but requires membership. Departmental work that's not sensitive but not relevant to everyone.
- **Private Teamspaces (Finance, Leadership):** Invisible to non-members. AR aging data, unit economics, P&L insights, and customer health flags are sensitive and shouldn't be casually browsable.

### Permission Matrix

| Content | Support | Sales | Finance | Leadership | Ops | Everyone |
|---------|---------|-------|---------|------------|-----|----------|
| 🏠 Home | Full | Full | Full | Full | Full | Full |
| 📚 Knowledge Base | Full | Full | Full | Full | Full | Full |
| 🎧 Support Hub | Full | View | View | Full | Full | — |
| 💰 Sales Hub | View | Full | View | Full | View | — |
| 📊 Finance Hub | — | — | Full | Full | — | — |
| 👔 Executive Hub | — | — | View | Full | View | — |
| ⚙️ Automations Hub | — | — | — | Full | Full | — |

**"View" access** means the database is shared as a linked view with comment-only permissions. The team can see the data but can't modify it.

**Cross-Hub Database Sharing:**

Customer Directory is the most shared database. It lives in Support Hub (source of truth) but is exposed as linked views in every other hub with persona-appropriate columns visible:

| Hub | Customer Directory Columns Shown |
|-----|----------------------------------|
| Support | All 30 curated columns (full context for calls) |
| Sales | customer_name, accounting_bucket, ttm_net_revenue, revenue_trend, status, deal count |
| Finance | customer_name, accounting_bucket, ar_balance, qb_customer_id, status |
| Executive | customer_name, health_score, risk_flags, ttm_net_revenue, tenure |
| Automations | customer_name, client_id, status, active_ticket_count |

### Navigation Design: The Three-Click Rule

Every piece of information should be reachable in 3 clicks or fewer from the sidebar:

**Click 1 → Sidebar Hub** (e.g., "🎧 Support Hub")
**Click 2 → Section/Database** (e.g., "Customer Directory")
**Click 3 → Specific Record** (e.g., "Acme Corp customer page")

To enforce this:

1. **Lock the sidebar** — Prevent individual users from rearranging the global structure
2. **Hub pages are the navigation layer** — Each hub page has clear sections with linked database views and quick links
3. **No deep nesting** — Maximum 2 levels of sub-pages within any hub
4. **Consistent iconography** — Every hub and major section has an emoji icon for instant visual recognition

### Sidebar Structure (Locked)

```
SIDEBAR (All Users See):
━━━━━━━━━━━━━━━━━━━━━━
🏠 B4ALL Home
📚 Knowledge Base
👋 Welcome to B4ALL

YOUR TEAMSPACES:
━━━━━━━━━━━━━━━━━━━━━━
[Varies by role — only joined teamspaces appear]
🎧 Support Hub        ← Support team members
💰 Sales Hub          ← Sales team members
📊 Finance Hub        ← Finance team members
👔 Executive Hub      ← Leadership members
⚙️ Automations Hub    ← Ops team members
```

### Governance Model

| Role | Who | Powers |
|------|-----|--------|
| **Workspace Owner** | Jack Elliott | Full settings, billing, security, audit log access |
| **Workspace Admin** | Brigid Mulcahy | Member management, teamspace creation |
| **Teamspace Owners** | Department leads | Manage their teamspace's members, pages, permissions |
| **Members** | Everyone else | Edit within their teamspaces, view shared content |

**Content Governance Rules:**

1. **Database owners** — Each synced database has a designated human owner who validates data quality and flags sync issues
2. **Knowledge Base ownership** — Each KB section has an owner (e.g., Customer Success section owned by Greg Khanoyan, Sales section owned by Daniel Almodovar)
3. **Quarterly audit** — Review permissions, archive stale content, verify KB article freshness
4. **No ad-hoc databases** — New databases require approval to prevent schema sprawl (consistent with the /stevewozniak gatekeeper principle)

---

## LAYER 3: ONBOARDING LAYER

### Design Philosophy

New hire onboarding should be **self-service first, human-guided second.** The knowledge base already has a structured `getting-started/new-hire-orientation/` section with week-by-week learning paths. The Notion onboarding layer turns this into an interactive, trackable experience.

### Onboarding Hub Structure

```
👋 Welcome to B4ALL
├── 🎉 Welcome Page
│   └── Company mission, values, "what we do in 60 seconds"
│   └── Photo/video of the team
│   └── "Your first week" quick overview
├── ✅ Your Onboarding Checklist (database)
│   └── Personalized checklist generated per new hire
├── 📅 Day-by-Day Schedule
│   ├── Day 1: Orientation & Setup
│   ├── Day 2-3: Product Deep Dive
│   ├── Week 1: Shadow & Learn
│   └── Week 2-4: Ramp & Practice
├── 🧭 Find Your Way Around
│   └── Visual map of the Notion workspace
│   └── "Where to find X" quick reference
│   └── Key contacts by question type
├── 📚 Required Reading (linked views from KB)
│   └── start-here.md, system-architecture.md, glossary.md
│   └── Role-specific articles based on department
├── 🔑 Access & Tools Setup
│   └── System access checklist (HubSpot, ThinClient, Dialpad, etc.)
│   └── Tool-by-tool setup guides
│   └── Password management (Keeper Security)
│   └── VPN setup (CATO)
└── 🤝 Your Buddy & Manager
    └── Assigned onboarding buddy
    └── 30-60-90 day check-in schedule
    └── 1:1 template
```

### Onboarding Checklist Database

| Property | Type | Purpose |
|----------|------|---------|
| Task | Title | What needs to be done |
| Category | Select | Setup / Reading / Training / Meeting / Admin |
| Timeline | Select | Day 1 / Week 1 / Week 2 / Week 3 / Week 4 / 30-Day / 60-Day / 90-Day |
| Status | Status | Not Started / In Progress / Complete |
| Owner | Select | New Hire / Manager / IT / HR |
| Department | Select | All / Support / Sales / Finance / Engineering |
| Priority | Select | Required / Recommended / Optional |
| Link | URL | Link to resource, article, or tool |
| Notes | Rich Text | Additional context |

**Views:**
- "My Checklist" — Filtered to new hire's department, grouped by Timeline
- "Manager View" — Grouped by new hire, showing completion % as rollup
- "Overdue" — Filtered to Status != Complete AND Timeline < today

### Role-Based Onboarding Paths

Based on the existing knowledge base orientation content, each department has a tailored reading and training path:

**Support Team Onboarding (Weeks 1-3):**
- Week 1: Company overview, system architecture, product family overview, glossary, support call types
- Week 2: Live Scan deep dive, ThinClient basics, HubSpot ticketing, common troubleshooting
- Week 3: Advanced troubleshooting, state-specific procedures (starting with CA), call shadowing

**Sales Team Onboarding (Weeks 1-3):**
- Week 1: Company overview, product family, sales playbooks, pricing structure
- Week 2: HubSpot CRM training, deal pipeline stages, market intelligence review
- Week 3: Prospecting playbooks, proposal templates, competitive landscape

**Finance Team Onboarding (Weeks 1-3):**
- Week 1: Company overview, chart of accounts, GL code reference, accounting policies
- Week 2: QuickBooks orientation, customer identity crosswalk, AR procedures
- Week 3: Month-end close procedures, reconciliation workflows, compliance

### Notion AI Integration for Onboarding

With Notion AI Q&A enabled (Business/Enterprise plan):
- New hires can ask natural language questions like "How do I handle a stuck transaction?" and get instant answers from the KB
- The "Find Your Way Around" page can include a Notion AI Q&A widget as the primary search interface
- AI Autofill can auto-generate summaries of long KB articles for quick scanning during orientation

---

## CROSS-CUTTING CONCERNS

### Database Relation Map

The `client_id` field is the universal join key across all synced databases. Here's the complete relation graph:

```
                    ┌─────────────────┐
                    │   CUSTOMER      │
                    │   DIRECTORY     │
                    │   (DB 1)        │
                    │   client_id PK  │
                    └────────┬────────┘
                             │
         ┌───────────┬───────┼───────┬────────────┬──────────┐
         │           │       │       │            │          │
    ┌────┴────┐ ┌────┴──┐ ┌──┴───┐ ┌┴─────────┐ ┌┴────────┐ ┌┴──────────┐
    │ Ticket  │ │ Call  │ │Device│ │ Deal     │ │AR Aging │ │ Unit      │
    │ Board   │ │ Log   │ │ Dir  │ │ Pipeline │ │ Board   │ │ Economics │
    │ (DB 2)  │ │(DB 3) │ │(DB 4)│ │ (DB 5)   │ │(DB 11)  │ │ (DB 12)   │
    └─────────┘ └───────┘ └──────┘ └──────────┘ └─────────┘ └───────────┘
```

**Relation Implementation in Notion:**

Use Notion Relations to link databases via `client_id`. When a support rep is looking at a customer page, they can see:
- Related tickets (rollup: count of open tickets)
- Related calls (rollup: last call date)
- Related devices (rollup: count of active devices)
- Related deals (rollup: total pipeline value)
- AR status (rollup: total amount due)

This creates the "full picture" experience described in the Vision Brief — one click on a customer reveals everything across all systems.

### Sync Architecture Integration

The Vision Brief defines the complete sync architecture (Supabase → Notion via Edge Function). This organizational overlay adds:

1. **Sync Health Widget** — A small section on the 🏠 Home page showing last sync time per database and any sync errors
2. **Sync ownership** — Each database in the cadence table (Vision Brief) has an assigned human owner who's responsible for validating data quality
3. **Stale data alerts** — If a database hasn't synced within 2x its expected cadence, flag it on the Home page

### Search & Discovery Strategy

**Notion AI Q&A** is the primary discovery mechanism. With the KB wiki + synced databases, employees can:
- Search for customers by name across all databases
- Ask questions about procedures and get KB article answers
- Find templates by describing what they need

**Search optimization:**
- Consistent naming conventions across all databases (e.g., always `customer_name`, never `client_name` vs `company_name`)
- Rich tagging on KB articles (Tags multi-select)
- Department-based audience tags on announcements and articles

### Notification Strategy

Notion doesn't have traditional "push notifications" like an intranet, but we can simulate ambient awareness:

1. **Company Announcements database** — Pinned announcements appear at the top of Home for everyone
2. **@mentions in comments** — Use Notion comments to tag people on specific database records that need attention
3. **Notion AI daily digest** (if available on plan) — Auto-summarize what changed across databases
4. **Slack integration** — Connect Notion to Slack so database changes (new announcements, new incidents) post to relevant channels
5. **Calendar reminders** — Company Calendar events with upcoming deadlines surface in Notion's calendar view

---

## IMPLEMENTATION ROADMAP

### Phase 0: Foundation Setup (Week 1)

**Goal:** Establish the skeleton structure before any content migration or data sync.

1. Create Teamspaces: B4ALL (Open), Support (Closed), Sales (Closed), Finance (Private), Leadership (Private), Operations (Closed)
2. Create 7 hub pages (🏠 Home, 🎧 Support, 💰 Sales, 📊 Finance, 👔 Executive, ⚙️ Automations, 📚 Knowledge Base) + 👋 Onboarding
3. Create core databases: Team Directory, Company Announcements, Company Calendar
4. Seed Team Directory from Microsoft Teams user data (28 members)
5. Lock sidebar structure
6. Invite team members to workspace and assign to appropriate teamspaces

### Phase 1: Knowledge Base Restructure (Week 1-2)

**Goal:** Transform the flat KB import into navigable, wiki-enabled sections.

1. Restructure existing "B4ALL Knowledge Base" page into 10 section pages matching filesystem taxonomy
2. Enable Wiki features (verification, ownership, expiration)
3. Assign section owners
4. Create linked views in each hub pointing to their relevant KB sections
5. Enable Notion AI Q&A over the workspace

### Phase 2: Data Sync Layer — Foundation (Weeks 2-3)

**Goal:** Deploy the sync infrastructure and first databases (from Vision Brief Phases 1-2).

1. Create `sync` schema in Supabase (notion_queue, notion_watermarks, notion_db_map)
2. Deploy `notion-sync-worker` Edge Function
3. Sync Customer Directory (DB 1) — the master database everything else links to
4. Sync Device Directory (DB 4)
5. Sync Ticket Board (DB 2) + Call Log (DB 3)
6. Create cross-database relations
7. Build Support Hub "My Day" dashboard
8. Relocate existing Operational Dashboards under 🏠 Home

### Phase 3: Sales + Finance + Executive (Weeks 3-4)

**Goal:** Light up the remaining persona hubs (from Vision Brief Phases 3-4).

1. Sync Deal Pipeline (DB 5) + Market Intelligence (DB 6) + Prospect Priority (DB 7) + Regulatory Inbox (DB 8)
2. Sync GL Reference (DB 9) + Customer Identity Crosswalk (DB 10) + AR Aging (DB 11) + Unit Economics (DB 12)
3. Sync Company Pulse (DB 13) + Customer Health Board (DB 14) + Revenue Waterfall (DB 15) + Strety Scorecard (DB 16)
4. Build hub dashboards and filtered views for each persona

### Phase 4: Automations + Onboarding (Weeks 4-5)

**Goal:** Complete the automation monitoring suite and onboarding experience.

1. Sync all automation databases (DB 17-22)
2. Build Automations Hub "Operations Summary" dashboard
3. Create Onboarding Hub with checklist database and role-based paths
4. Create onboarding templates for each department
5. Build "Find Your Way Around" navigation guide

### Phase 5: Polish + Launch (Week 5-6)

**Goal:** Refine, test with real users, and officially launch.

1. Run pilot with 3-4 users across different departments
2. Gather feedback on navigation, data freshness, missing content
3. Refine hub page layouts and dashboard designs
4. Set up Slack integration for key notifications
5. Create sync health monitoring dashboard
6. Conduct team-wide launch and training session
7. Set up quarterly governance review cadence

---

## SUCCESS METRICS

Track these to know if the workspace is working:

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Weekly Active Users | 80%+ of team (22+ of 28) | Notion analytics |
| Time to Find Info | < 3 clicks, < 30 seconds | User testing |
| Knowledge Base Coverage | 90%+ articles verified | Wiki verification status |
| Data Freshness | All databases within 2x cadence | Sync health monitoring |
| Onboarding Completion | 100% checklist completion within 30 days | Onboarding checklist rollup |
| Support Lookup Time | < 10 seconds to pull customer context | Observational timing |
| Adoption Satisfaction | 4+ out of 5 rating | Quarterly survey |

---

## WHAT THIS ARCHITECTURE INTENTIONALLY EXCLUDES

Staying true to the Vision Brief's design principle: *"If there is no lookup moment, no check-in cadence, no exception alert — it stays in the warehouse."*

- **Raw P&L line items** — Too granular. Executive gets Company Pulse.
- **Revenue retention at customer × business_line grain** — 104K rows. Stays in warehouse.
- **Anomaly detector** — Agent-driven alerts, not standing database.
- **Cohort retention curves** — Analytical, not operational.
- **Raw call transcripts** — Too large. Support gets call metadata.
- **Email workflow views** — Internal accounting ops.
- **Customer concentration / HHI** — Strategic analysis, agent-queryable.
- **Full HubSpot company list** — 23,287 records, 81% unmapped prospects. Only synced customers reach Notion.
- **Microsoft Teams message archive** — 4,958 messages stay in Teams. Notion gets operational data, not chat history.

---

## APPENDIX A: COMPLETE DATABASE INVENTORY

| # | Database | Hub | Source | Sync Cadence | Est. Rows |
|---|----------|-----|--------|--------------|-----------|
| — | Team Directory | 🏠 Home | Manual + Teams seed | Manual | 28 |
| — | Company Announcements | 🏠 Home | Manual | Manual | ~50/yr |
| — | Company Calendar | 🏠 Home | Manual | Manual | ~100/yr |
| 1 | Customer Directory | 🎧 Support | mv_customer_intel | Daily 6am | ~500 |
| 2 | Ticket Board | 🎧 Support | v_client_tickets | Every 2hr | ~200 open |
| 3 | Call Log (7-day) | 🎧 Support | mv_call_spine | Every 4hr | ~4,500 |
| 4 | Device Directory | 🎧 Support | dim_device | Daily | ~6,099 |
| 5 | Deal Pipeline | 💰 Sales | v_client_deals | Daily | ~338 open |
| 6 | Market Intelligence | 💰 Sales | mv_state_market_summary | Weekly | ~56 |
| 7 | Prospect Priority | 💰 Sales | v_prospect_priority | Weekly | ~200 |
| 8 | Regulatory Inbox | 💰 Sales | v_regulatory_inbox | Weekly | ~20 |
| 9 | GL / Contract Code Ref | 📊 Finance | gl_account + contract_code | On-change | ~200 |
| 10 | Customer Identity Crosswalk | 📊 Finance | customer_identity_master | Daily | ~500 |
| 11 | AR Aging Board | 📊 Finance | mv_ar_aging_latest | Daily | ~300 |
| 12 | Unit Economics | 📊 Finance | mv_unit_economics_monthly | Daily | ~1,500 |
| 13 | Company Pulse | 👔 Executive | mv_company_pulse | Daily | ~38 |
| 14 | Customer Health Board | 👔 Executive | v_customer_health | Daily | ~100 |
| 15 | Revenue Waterfall | 👔 Executive | mv_revenue_waterfall | Weekly | ~38 |
| 16 | Strety Scorecard | 👔 Executive | v_strety | Weekly | ~52 |
| 17 | Automation Registry | ⚙️ Automations | v_registry_live | Every 6hr | ~596 |
| 18 | Chain Health Monitor | ⚙️ Automations | v_chain_health | Every 6hr | ~20 |
| 19 | Incident Queue | ⚙️ Automations | v_incident_dashboard | Every 2hr | ~50 open |
| 20 | Draft Performance | ⚙️ Automations | v_draft_performance | Daily | ~30 |
| 21 | Review Queue | ⚙️ Automations | v_review_queue | Every 4hr | ~20 |
| 22 | Operations Summary | ⚙️ Automations | v_operations_summary | Every 6hr | 1 |
| — | Onboarding Checklist | 👋 Onboarding | Manual (template) | Manual | ~50/hire |

**Total synced databases: 22** (from Supabase)
**Total manual databases: 4** (Team Directory, Announcements, Calendar, Onboarding)
**Total databases: 26**

---

## APPENDIX B: TEAM MEMBERS BY DEPARTMENT (from Microsoft Teams + Outlook data)

| Department | Members |
|-----------|---------|
| **Support** | Greg Khanoyan, Mayuri Buckius, Rowealth Maniago, Randy Morehouse |
| **Engineering** | Brian Brick, Pramod Vaity, Steven Kim, Edward Chen, Brennan Lin, Zachary Liang, Sunho Lee |
| **Sales** | Daniel Almodovar, Connor Schauer, Corey Stock |
| **Finance** | Kathy Zimmerman, Shelley Barstow |
| **Executive/Leadership** | Brigid Mulcahy, Jack Elliott, Daniel Hatfield |
| **Operations/Implementation** | Andy Vu, Phil Taylor, Philip Gudijanto, Adam Lane, Jordan Davis, Jacob Osorio, Carlos Navarro, Ross Bagley |

*Note: Department assignments inferred from Teams channel membership, email patterns, and chat group membership. Some members may span multiple departments. Verify before seeding Team Directory.*

---

## APPENDIX C: KEY NOTION CONFIGURATION DECISIONS

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Notion Plan | Business or Enterprise | Required for: Private Teamspaces, Wiki verification, Notion AI Q&A, Dashboard views |
| Default font | System default | Don't customize — keeps pages loading fast |
| Page width | Full width for hub pages | Data-heavy hub pages need horizontal space |
| Database default view | Table for most, Board for Ticket Board/AR Aging/Incident Queue | Tables for lookup, Boards for workflow |
| AI Q&A | Enabled workspace-wide | Primary search/discovery mechanism |
| Guest access | Disabled initially | No external stakeholders need Notion access at launch |
| Public pages | None | All content is internal-only |
| Import method (KB) | Structured page hierarchy | Not a database — articles are pages with rich content that doesn't fit database rows |

---

*This Architecture Blueprint is the companion to the Vision Brief. The Vision Brief defines WHAT data syncs and HOW (the Supabase → Notion pipeline). This Blueprint defines WHERE everything lives, WHO sees what, and HOW people navigate the complete workspace. Together, they form the complete specification for building B4ALL's Notion workspace.*

*Ready for `/stevewozniak` to produce implementation-level technical specs for each phase.*
