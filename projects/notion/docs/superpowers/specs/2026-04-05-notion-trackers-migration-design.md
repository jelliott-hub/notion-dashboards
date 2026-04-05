# Notion Trackers Migration — Design Spec

**Date:** 2026-04-05
**Status:** Draft
**Scope:** Migrate all Asana project trackers + Excel tracker spreadsheets into 4 Notion databases with hub-native views and intake form templates.

---

## Context

B4ALL currently tracks operational work across two disconnected systems:

- **Asana** — ~20 RFP projects (one project per RFP), Engineering Backlog, Software Tools Management, New Pricing Rollout, Onboarding templates, and ~10 one-off operational projects
- **Excel spreadsheets** — RFP Tracker v3 (pipeline + task breakdown + intake template), Engineering Escalation Tracker, Commitment Tracker (DCFS-specific), DCFS Task List

The goal is to consolidate everything into Notion databases embedded in the existing hub architecture, with filtered views piped into each hub and structured intake forms for common workflows (e.g., Daniel closes a sale → fills a form → row appears in the tracker).

## Decision: 4 Databases, Not 1

Field overlap across tracker types is ~15% (Title, Status, Owner, Notes). Combining everything into one mega-database would create a schema that's 70% empty on any given row. Instead, we group by schema affinity:

| Database | Combines | Schema Overlap |
|----------|----------|---------------|
| **RFP Pipeline** | Asana RFP projects + Excel RFP Tracker | Same lifecycle, fields, team |
| **Engineering Tracker** | Asana Engineering Backlog + Excel Escalation Tracker | Share Product, Owner, Status; escalations add severity/root cause |
| **Operations Tracker** | Pricing Rollout + Onboarding + one-off Projects | Lightweight task tracking, ~60% field overlap |
| **Tool Tracker** | Already exists in Notion | No changes needed |

---

## Database 1: RFP Pipeline

**Hub:** Growth (Sales)
**Replaces:** ~20 individual Asana RFP projects + Excel RFP Tracker (Summary + Task Tracker + New RFP Template sheets)

### Schema

| Property | Type | Values / Notes |
|----------|------|---------------|
| `RFP Name` | Title | Agency name (e.g., "WA Parks & Recreation") |
| `RFP Number` | Text | Solicitation ID (e.g., "RFP 325-585") |
| `State` | Select | US state/territory abbreviations: AL, CA, FL, IL, MA, NC, OH, PR, TX, UT, VT, WA + others as needed |
| `Bid Decision` | Select | `BID`, `NO BID`, `TBD` |
| `RFP Stage` | Select | `Evaluate Fit`, `Plan Process`, `Draft Response`, `Submit`, `Complete` |
| `Status` | Select | `Not Started`, `In Progress`, `Waiting`, `Done` |
| `Result` | Select | `Awarded`, `Not Awarded`, `Pending`, `Passed` |
| `Lead Owner` | Person | Primary responsible (maps to Asana project owner) |
| `Team Members` | Person (multi) | Cross-functional team |
| `Submission Deadline` | Date | External due date |
| `Internal Target` | Date | B4ALL's internal cutoff (typically 2-3 days before external) |
| `Est. Contract Value` | Text | Dollar range or amount |
| `Submission Email` | Email | Agency submission address |
| `Procurement Contact` | Text | Name + email + phone |
| `Approved` | Checkbox | Final sign-off received |
| `Won/Lost Reason` | Rich Text | Post-mortem on outcome |
| `Asana Link` | URL | Legacy link to original Asana project |
| `Notes` | Rich Text | General notes |

### Page Body Template

Each RFP row's page body follows the structure from the Excel "New RFP Template" sheet:

```
## Opportunity Overview
- RFP / Agency Name: {RFP Name}
- RFP Number: {RFP Number}
- State: {State}
- Bid Decision: {Bid Decision}
- Submission Deadline: {Submission Deadline}
- Internal Target: {Internal Target}
- Est. Contract Value: {Est. Contract Value}
- Submission Email: {Submission Email}

## Team
- Lead Owner: {Lead Owner}
- Team Members: {Team Members}
- Procurement Contact: {Procurement Contact}

## Key Dates & Milestones
| Milestone | Date | Assignee | Notes |
|-----------|------|----------|-------|
| Q&A / Questions Due | | | |
| Answers Released | | | |
| Internal Draft Due | | | |
| Internal Review Complete | | | |
| Submission Deadline | | | |
| Award Expected | | | |

## Task Checklist

### Evaluate RFP Fit
- [ ] Review RFP document — identify scope, eligibility, requirements
- [ ] Go/No-Go decision — present to Brigid
- [ ] Confirm certification requirements (FBI channeler status, state registration)

### Plan RFP Process
- [ ] List all key deadlines → create Asana tasks + calendar invites
- [ ] Assign team members + send kickoff message
- [ ] Q&A submission (if applicable)

### Draft RFP Response
- [ ] Company identification (legal name, EIN, address, contacts)
- [ ] Description of services
- [ ] Qualifications & references (3+ confirmed references)
- [ ] Pricing / fee structure (Brigid approves)
- [ ] Compliance requirements (immigration, warranties, conflicts)
- [ ] Submittal letter (signed by Brigid)

### Submit RFP
- [ ] Internal review + final approval
- [ ] Submit via required method (email / portal)
- [ ] Log submission confirmation
- [ ] Update tracker

## Links & References
- Asana Project: {Asana Link}
- RFP Document Location:
- Submission Confirmation:

## Outcome
- Result: {Result}
- Won/Lost Reason: {Won/Lost Reason}
- Lessons Learned:
```

### Views

| View Name | Type | Filter | Group By | Columns Shown | Placed In |
|-----------|------|--------|----------|---------------|-----------|
| Active Pipeline | Table | Result = `Pending` | RFP Stage | RFP Name, State, Bid Decision, RFP Stage, Lead Owner, Submission Deadline, Est. Contract Value | Growth hub |
| Pipeline Board | Board | Result = `Pending` | RFP Stage | RFP Name, State, Lead Owner, Submission Deadline | Growth hub |
| By State | Table | Result = `Pending` | State | RFP Name, RFP Stage, Lead Owner, Submission Deadline | Growth hub |
| Won/Lost History | Table | Result ≠ `Pending` | Result | RFP Name, State, Result, Won/Lost Reason, Est. Contract Value | Growth hub |
| My RFPs | Table | Lead Owner = me | RFP Stage | All core fields | Growth hub |

### Intake Form: "New RFP"

Notion database template pre-filled with:
- Status → `Not Started`
- RFP Stage → `Evaluate Fit`
- Result → `Pending`
- Bid Decision → `TBD`
- Page body → full template above with empty placeholders

**Workflow:** Christy/Corey finds new RFP → opens Growth hub → clicks "New RFP" template → fills in Opportunity Overview + Team → checklist auto-scaffolds.

### Data to Migrate

| Source | Records | Method |
|--------|---------|--------|
| Excel RFP Tracker — RFP Summary sheet | 6 RFPs | Manual create via Notion API |
| Asana RFP projects (project names, notes, status, members) | ~20 projects | Script reads Asana API, creates Notion rows |
| Asana RFP tasks per project | ~150 tasks | Populate as checklist items in each RFP's page body |

---

## Database 2: Engineering Tracker

**Hub:** Engineering
**Replaces:** Asana Engineering Backlog + Excel Engineering Escalation Tracker

### Schema

| Property | Type | Values / Notes |
|----------|------|---------------|
| `Item` | Title | Bug/feature/escalation name |
| `Type` | Select | `Bug`, `Feature`, `Escalation` |
| `Product` | Select | `AS.com`, `CMS Website`, `CMS Thin Client`, `LS4G App`, `Server`, `Other` |
| `Product Section` | Select | `BRK`, `BRN` (for backlog items) |
| `Status` | Select | `New`, `Accepted`, `In Progress`, `Testing`, `Released/Closed`, `In Dev Queue`, `Pending Feedback` |
| `Priority` | Select | `P1`, `P2`, `P3`, `P4` |
| `Owner` | Person | Engineering owner |
| `Escalated By` | Text | Who raised the escalation (initials) |
| `Date Reported` | Date | When filed |
| `Product Version` | Text | e.g., "4638" |
| `Customer/Client` | Text | Client ID or name (e.g., "OCPS", "KCCMS") |
| `Impact` | Select | `Single Live Scan`, `Multi. Live Scan`, `Website`, `Thin Client`, `Support`, `Agency (FBI, CADOJ, Etc.)`, `Business (B4ALL)`, `Engineering`, `Implementation` |
| `Workaround` | Select | `Workaround Avail.`, `No Workaround - Can purchase/submit`, `No Workaround - Can't purchase/submit`, `Support Slowdown`, `Support Stoppage`, `Agency slowdown`, `Agency unavailable`, `Thin Client Unavailable`, `Prevents Go-Live`, `ENG QoL problem` |
| `Repro Steps` | Rich Text | How to reproduce |
| `Engineering Notes` | Rich Text | Investigation details |
| `Solution` | Rich Text | Fix steps taken |
| `Root Cause` | Rich Text | Post-mortem |
| `Relevant Files` | Text | File paths/log locations |
| `Point of Contact` | Text | Engineering POC (initials) |
| `Updated By` | Text | Last person to update |
| `Notes` | Rich Text | General notes |

### Views

| View Name | Type | Filter | Group By | Placed In |
|-----------|------|--------|----------|-----------|
| Open Escalations | Table | Type = `Escalation`, Status ≠ `Released/Closed` | Impact | Engineering hub |
| Escalation Board | Board | Type = `Escalation` | Status | Engineering hub |
| Backlog — All | Table | Type ∈ (`Bug`, `Feature`) | Product Section | Engineering hub |
| Backlog — By Product | Table | Type ∈ (`Bug`, `Feature`) | Product | Engineering hub |
| All Open Items | Table | Status �� `Released/Closed` | Type | Engineering hub |
| Closed / Resolved | Table | Status = `Released/Closed` | Type | Engineering hub |

### Intake Forms

**"New Escalation"** template:
- Type → `Escalation`
- Status → `New`
- Date Reported → today
- Page body prompts: Problem Description, Repro Steps, Customer/Client, Relevant Files/Logs

**"New Bug"** template:
- Type → `Bug`
- Status �� `New`

**"New Feature Request"** template:
- Type → `Feature`
- Status → `New`

### Data to Migrate

| Source | Records | Method |
|--------|---------|--------|
| Excel Engineering Escalation Tracker | ~15 escalations (rows 13-137, most are empty padding) | Script parses non-empty rows, creates via Notion API |
| Asana Engineering Backlog | 46 items | Script reads Asana tasks + custom fields, creates Notion rows |

---

## Database 3: Operations Tracker

**Hub:** Cross-functional (views in multiple hubs)
**Replaces:** Asana New Pricing Rollout + Asana Onboarding templates + Asana one-off projects (Dock Implementation, PandaDoc, AI Chatbot, GTM Initiatives, etc.)

### Schema

| Property | Type | Values / Notes |
|----------|------|---------------|
| `Task` | Title | Task/project name |
| `Type` | Select | `Pricing`, `Onboarding`, `Project`, `Initiative` |
| `Hub` | Select | `Growth`, `Engineering`, `Tools`, `Getting Started`, `Accounting`, `Customer Success`, `Implementation`, `Compliance` |
| `Status` | Select | `Not Started`, `Started`, `In Progress`, `In Review`, `Complete`, `On Hold` |
| `Owner` | Person | |
| `Due Date` | Date | |
| `Priority` | Select | `P1`, `P2`, `P3`, `P4` |
| `Category` | Select | `Logistics`, `Meetings`, `Paperwork`, `Check-ins`, `Integration`, `Rollout`, `Migration` |
| `Customer Type` | Select | `Relay`, `SaaS`, `Services / Support` (for Pricing rows) |
| `Employee` | Text | New hire name (for Onboarding rows) |
| `Project` | Text | Parent project name (for grouping tasks under a project) |
| `Notes` | Rich Text | |

### Views

| View Name | Type | Filter | Group By | Placed In |
|-----------|------|--------|----------|-----------|
| Pricing Rollout | Board | Type = `Pricing` | Status | Growth hub |
| Onboarding — Remote | Table | Type = `Onboarding`, Category in (`Logistics`, `Meetings`, `Paperwork`, `Check-ins`) | Category | Getting Started hub |
| Onboarding — By Employee | Table | Type = `Onboarding` | Employee | Getting Started hub |
| Active Projects | Table | Type ∈ (`Project`, `Initiative`), Status ≠ `Complete` | Hub | Tools hub (or a new "Operations" section) |
| All Tasks — By Hub | Table | no filter | Hub | Cross-hub dashboard page |
| My Tasks | Table | Owner = me | Status | Cross-hub dashboard page |

### Intake Forms

**"New Pricing Customer"** template:
- Type → `Pricing`
- Hub → `Growth`
- Status → `Not Started`

**"New Onboarding — Remote"** template:
- Type → `Onboarding`
- Hub → `Getting Started`
- Status → `Not Started`
- Page body → 15 pre-filled checklist items from Asana remote onboarding template

**"New Onboarding — In Person"** template:
- Type → `Onboarding`
- Hub → `Getting Started`
- Status → `Not Started`
- Page body → 15 pre-filled checklist items from Asana in-person onboarding template

**"Deal Closed"** form (Daniel's workflow):
- Type → `Project`
- Hub → `Growth`
- Status → `Not Started`
- Page body prompts: Customer Name, Deal Value, Contract Type, Implementation Notes, Handoff Checklist

**"New Project"** template:
- Type → `Project`
- Status → `Not Started`
- Page body prompts: Objective, Team, Timeline, Deliverables

### Data to Migrate

| Source | Records | Method |
|--------|---------|--------|
| Asana New Pricing Rollout | 39 customers | Script reads Asana tasks + Customer Type field |
| Asana Onboarding (remote) | 15 template tasks | Manual create as template |
| Asana Onboarding (in-person) | 15 template tasks | Manual create as template |
| Asana one-off projects | ~10 projects, ~50 tasks | Script reads Asana, creates rows |

---

## Database 4: Tool Tracker

**Hub:** Tools
**Status:** Already exists in Notion as `Tool Tracker` database (ID: `33713d36-77c3-80b9-b8ed-e1a7e626afdf`)

No schema changes needed. The Asana "Software Tools Management" project (35 tools with Primary Admin, Secondary Admin, department sections, onboarding status) should be migrated into the existing database. May need to add properties:

| Property | Type | Notes |
|----------|------|-------|
| `Primary Admin` | Person | If not already present |
| `Secondary Admin` | Person | If not already present |
| `Used For` | Rich Text | Tool purpose description |
| `Department` | Select | `B4ALL`, `Sales`, `Support`, `Accounting/Finance`, `Engineering`, `Exec` |

### Data to Migrate

| Source | Records | Method |
|--------|---------|--------|
| Asana Software Tools Management | 35 tools | Script reads Asana, upserts into existing Notion DB |

---

## Hub Placement Summary

Where each database's views get embedded:

| Hub | Views Embedded |
|-----|---------------|
| **Growth (Sales)** | RFP: Active Pipeline, Pipeline Board, By State, Won/Lost History, My RFPs · Ops: Pricing Rollout, Deal Closed items |
| **Engineering** | Eng: Open Escalations, Escalation Board, Backlog All, Backlog By Product, All Open, Closed |
| **Tools** | Tool Tracker (existing) · Ops: Active Projects |
| **Getting Started** | Ops: Onboarding Remote, Onboarding By Employee |
| **Accounting & Finance** | Ops: filtered to Hub = Accounting |
| **Customer Success** | Ops: filtered to Hub = Customer Success |
| **Implementation** | Ops: filtered to Hub = Implementation |
| **Compliance** | Ops: filtered to Hub = Compliance |

---

## Intake Form Summary

| Form Name | Creates Row In | Trigger / User |
|-----------|---------------|----------------|
| New RFP | RFP Pipeline | Christy/Corey finds new opportunity |
| New Escalation | Engineering Tracker | Support escalates to Engineering |
| New Bug | Engineering Tracker | Anyone reports a bug |
| New Feature Request | Engineering Tracker | Anyone requests a feature |
| New Pricing Customer | Operations Tracker | Pricing rollout team |
| New Onboarding — Remote | Operations Tracker | Shelley onboards remote hire |
| New Onboarding — In Person | Operations Tracker | Shelley onboards in-person hire |
| Deal Closed | Operations Tracker | Daniel closes a sale |
| New Project | Operations Tracker | Anyone kicks off a new initiative |

---

## Migration Strategy

### Phase 1: Create databases + schemas
1. Create RFP Pipeline database
2. Create Engineering Tracker database
3. Create Operations Tracker database
4. Augment existing Tool Tracker database with new properties

### Phase 2: Create views
1. Create all views per database (filtered, grouped, sorted)
2. Embed linked database views into each hub page

### Phase 3: Create intake form templates
1. Create Notion database templates for each intake form
2. Pre-fill default values and page body scaffolding

### Phase 4: Migrate data
1. Script reads Asana API → creates Notion rows for each project type
2. Script reads Excel trackers → creates Notion rows
3. Manual QA pass to verify data integrity

### Phase 5: Embed views in hubs
1. Add linked database views to each hub page under appropriate sections
2. Verify filtering and grouping in each view

---

## What This Does NOT Include

- **Asana decommission** — This spec creates the Notion databases; turning off Asana is a separate decision
- **Automated sync** — No Asana↔Notion real-time sync. This is a one-time migration + Notion becomes the system of record going forward
- **Supabase backing** — These databases live natively in Notion, not backed by Supabase views
- **Commitment Tracker / DCFS Task List** — These are DCFS-specific reference artifacts, not reusable templates. They stay as Excel files in `reference/Trackers/`

---

## Open Questions

1. **Deal Closed form fields** — Daniel's exact intake fields need confirmation. The template above is a starting point.
2. **Tool Tracker schema** — Need to verify what properties already exist before adding new ones.
3. **Asana project archival** — After migration, should Asana projects be archived, or kept read-only as historical reference?
