# B4All Ultimate Notion Enterprise Architecture & Design Document

*This document serves as the exact, "down-to-the-click" blueprint for the B4All Notion workspace. It maps the 19 Supabase operational datasets and the existing GitHub `knowledge-base` repository into a strictly functional, Master Data Management (MDM) architecture.*

---

## 🏗️ Architectural Philosophy
Following enterprise best practices, we use an **MDM (Master Data Management)** approach adapted to a functional PARA structure.
1. **The Core Data Engine (The Back Room):** All raw operational databases live in an Admin-only workspace.
2. **Functional Teamspaces (The Front Room):** There are 10 distinct departmental Teamspaces (e.g., Finance, Hardware) that exactly mirror the `knowledge-base` directory structure. Users interact with data via **Linked Views** layered into these Teamspaces.
3. **Relational Wikis:** Markdown documents are imported as database entries so they can automatically backlink to the operational data they govern.

---

## 🗄️ THE BACK ROOM: Core Infrastructure (Admin Only)
*All databases listed here are the canonical single-source-of-truth. They are never accessed directly by standard users.*

### Database 1: Master Parent Companies & Franchises
* **Properties:** 
  * `Account Name` (Title)
  * `Corporate Headquarters` (Text)
  * `National Enterprise Agreement?` (Checkbox)
  * `Total Affiliated Providers` (Rollup: Count of LSIDs)
* **Relations:** Site Locations (1:N), Contract Fee Master (1:N).

### Database 2: Site Locations (LSID & BLSID Registry)
* **Properties:**
  * `System ID` (Title): e.g., CA-12345 or BL-98765
  * `SAM Provider Status` (Select): Active, Prospect, Waitlisted, Suspended
  * `Location Type` (Select): Corporate Hub, Franchise, Independent Pharmacy, Government Office
* **Relations:** Parent Company (N:1), Assigned Hardware (1:N), FPC Operators (1:N).

### Database 3: Hardware Inventory (MIS Master)
* **Properties:**
  * `Serial Number` (Title)
  * `Manufacturer / Model` (Select): Guardian 200, HID Patrol, Kojak, RealScan G10.
  * `Deployment Status` (Status): Active, In Transit, Spare Pool, Pending Refurb.
* **Relations:** Assigned LSID (N:1), RMA Queue (1:N).

### Database 4: RMA & Preventative Maintenance Queue
* **Properties:** 
  * `RMA Ticket #` (Title)
  * `Reported Symptom (SCS)` (Multi-Select): Poor NFIQ Score, Blue Light Out, Foggy Prism.
  * `Return Tracking #` (Text)
* **Relations:** Hardware Serial (N:1).

### Database 5: ORI & Agency Sandbox
* **Properties:**
  * `ORI Number` (Title)
  * `Agency Name` (Text)
  * `Allowed TOTs` (Multi-select): FAP, DO, RAR, CUS, ARR.
* **Relations:** Regulatory Change Monitor (1:N).

### Database 6: Regulatory Change Monitor
* **Properties:**
  * `Statute Title` (Title)
  * `Impact` (Select): Code Update, Form Update, Fee Change.
  * `Go-Live Deadline` (Date)
* **Relations:** ORI Affected (N:1).

### Database 7: Contract Code & CBID Fee Master
* **Properties:**
  * `Contract Code` (Title, 4-letter format)
  * `Fee Chain Rules` (Select): Applicant Pays, Origining Agency Pays, B4ALL Split.
  * `Expiration Date` (Date)
  * `SLA Tier` (Select): Base, Priority, Mission Critical.
* **Relations:** Master Parent Company (N:1).

### Database 8: LS4G Fleet Telemetry & Windows Services
* **Properties:**
  * `Host LSID` (Title)
  * `LS4G Version` (Select): v4.1, v4.2, v4.4
  * `Service Status` (Status): Fault, Stopped, Healthy.
* **Relations:** LSID Registry (1:1).

### Database 9: Gateway Uptime Monitor (DOJ/FBI)
* **Properties:**
  * `Connection Endpoint` (Title)
  * `Current Status` (Status): Operational, Intermittent, Hard Down.

### Database 10: RTM Exception & Resubmission Queue
* **Properties:**
  * `ATI / TCN` (Title)
  * `Rejection Reason` (Select): Poor NFIQ, Invalid Annotation (AMP/BAND).
* **Relations:** Submitting LSID (N:1).

### Database 11: Daily Reconciliation Playbook
* **Properties:**
  * `Date/Batch Identifier` (Title)
  * `Payment Processor` (Select): SwipeSum, PayPal, Relay.
  * `Variance Amount` (Number - Currency)

### Database 12: Unmatched Payment Queue (QuickBooks)
* **Properties:**
  * `Stray Payment Name/ID` (Title)
  * `Amount` (Number - Currency)

### Database 13: Gov Bid & RFP War Room
* **Properties:**
  * `Solicitation ID` (Title)
  * `Probability to Win` (Select): Long-Shot, Competitive, Recompete.

### Database 14: Competitive Density Heatmap
* **Properties:**
  * `County/Region` (Title)
  * `Competitor Footprint` (Multi-Number): Counts of Identogo, Fieldprint.

### Database 15: Unified Support Intake
* **Properties:**
  * `Interaction ID` (Title)
  * `Triage Severity` (Select): Fatal Outage, Single Location Blocked.

### Database 16: Automation Incident Queue (Triage)
* **Properties:**
  * `Trigger Process` (Title)
  * `State` (Status): Firing, Snoozed, Triaging, Resolved.

### Database 17: At-Risk & Signal Matrices
* **Properties:**
  * `Client Entity` (Title)
  * `Signal Level` (Status): Code Red, Watchlist.

### Database 18: Fingerprint Certified Operator Roster (FPC Matrix)
* **Properties:**
  * `Operator FPC Number` (Title)
  * `Status` (Status): Active, Revoked, Expired.
* **Relations:** Assigned LSID (N:1).

### Database 19: SAM Provider Go-Live Checklist
* **Properties:**
  * `Checklist ID` (Title)
  * `Phase` (Status): ITO Signed, Hardware Provisioned, FPC Assigned, Live.
* **Relations:** LSID Registry (1:1).

---

## 🏛️ THE FRONT ROOM: Functional Teamspaces & Dashboards
*These are the exact visual specifications for the 10 Departmental Teamspaces.*

### 1. Company HQ & Getting Started
*   **Wiki Database:** Maps `getting-started/`. Contains Onboarding Docs & `identifier-glossary.md`.
*   **Dashboard Specs:**
    *   *Chart Type:* Gallery View of Core Values & Benefits links.
    *   *Linked Database:* `LSID Registry` (Count Rollup shown to executives: Total Active Providers).

### 2. Products
*   **Wiki Database:** Maps `products/`. Contains Livescan feature roadmaps & portal rules.
*   **Dashboard Specs:**
    *   *Chart Type:* Timeline View of upcoming feature releases.
    *   *Linked Database:* `LS4G Fleet Telemetry` (Pie Chart: Breakdown of v4.1 vs v4.2 vs v4.4 footprint).

### 3. Technical Operations
*   **Wiki Database:** Maps `technical/`. Contains Thin-Client configs, ActiveReports instructions.
*   **Dashboard Specs:**
    *   *Chart Type:* Board View grouped by `Service Status`.
    *   *Linked Database 1:* `LS4G Fleet Telemetry` (Filtered by `Status = Fault`).
    *   *Linked Database 2:* `Gateway Uptime Monitor` (Gallery View: Green/Red status cards for IL-ISP, CA-DOJ, FBI).
    *   *Linked Database 3:* `Automation Incident Queue` (Table View of active bot errors).

### 4. Hardware
*   **Wiki Database:** Maps `hardware/`. Contains RMA processing SOPs, Guardian/Patrol maintenance.
*   **Dashboard Specs:**
    *   *Chart Type:* Kanban Board grouped by `Deployment Status`.
    *   *Linked Database 1:* `Hardware Inventory (MIS Master)` (Filtered: Active issues only).
    *   *Linked Database 2:* `RMA Queue` (Table View: Pending shipping labels).

### 5. Compliance
*   **Wiki Database:** Maps `compliance/`. Contains State DOJ regulations.
*   **Dashboard Specs:**
    *   *Chart Type:* Calendar View.
    *   *Linked Database 1:* `Regulatory Change Monitor` (Plotted by `Go-Live Deadline`).
    *   *Linked Database 2:* `ORI Sandbox` (Table View of Suspended ORIs).

### 6. Implementation
*   **Wiki Database:** Maps `implementation/`. Contains New Operator Business checklists.
*   **Dashboard Specs:**
    *   *Chart Type:* Pipeline / Funnel View.
    *   *Linked Database:* `SAM Provider Go-Live Checklist` (Grouped by `Phase`).

### 7. Resolution Center
*   **Wiki Database:** Maps `resolution-center/`. Contains SCS ticket frameworks.
*   **Dashboard Specs:**
    *   *Chart Type:* Master Triage Inbox (List View).
    *   *Linked Database 1:* `Unified Support Intake` (Sorted by `Triage Severity` descending).
    *   *Linked Database 2:* `RTM Exception Queue` (Board View grouped by `Rejection Reason`).

### 8. Sales
*   **Wiki Database:** Maps `sales/`. Contains RFPs and Pricing plays.
*   **Dashboard Specs:**
    *   *Chart Type:* Heatmap / Table overlay.
    *   *Linked Database 1:* `Gov Bid War Room` (Kanban Board by `Status`).
    *   *Linked Database 2:* `Competitive Density Heatmap` (Table view).

### 9. Finance
*   **Wiki Database:** (Exclusive to Finance SOPs).
*   **Dashboard Specs:**
    *   *Chart Type:* Reconciliation Ledgers.
    *   *Linked Database 1:* `Unmatched Payment Queue` (Table View).
    *   *Linked Database 2:* `Daily Reconciliation Playbook` (List View filtered by Discrepancies).
    *   *Linked Database 3:* `Contract Code & CBID Fee Master` (Reference view for billing).

---

## 🔗 The Relational Click-Path (Example)
The power of this specific MDM format is the automated backlinking between the Knowledge Base wikis and the raw Supabase data flow.

**Scenario: A CA-DOJ Rate Hike**
1. An analyst opens the **Compliance Teamspace**.
2. They pull up the wiki page: `compliance/california-state-police-tot-updates.md`.
3. Because this is a Notion Database Entry, it is relationally linked to the **ORI Sandbox** entry for `CA-DOJ`.
4. Anyone looking at the `CA-DOJ` entry in the **Resolution Center** immediately sees the linked mandate doc.
5. In the **Finance Teamspace**, the CBID matrix updates, showing exactly which `Contract Codes` are affected by the CA-DOJ rate hike.

*End of Design Document.*
