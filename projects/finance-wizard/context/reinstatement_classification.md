# Reinstatement Classification (44020)

## Current State
- **Target**: QB shows $4,232/month recognized for account 44020
- **Current recognition**: ~$1,859/month (gap: ~$2,373/month)
- **Method**: text heuristic in `rebuild_deferred_maintenance()` Step 4

## Classification Logic (in order)
1. KINGR → EXCLUDED
2. PRDOH/PRDOJ → 44040
3. `lookup.reinstatement_clients` table join → 44020 (NEW, deployed 2026-03-31)
4. `item_name ILIKE '%reinstat%' OR LEFT(description, 200) ILIKE '%reinstat%'` → 44020
5. Everything else → 44010

## What the Text Heuristic Catches
- 178 invoice lines tagged as 44020
- Items: `Maint:Maint - Reinstatement` (5 lines), `Maint:Maint-9X5-Remote` (71), `Maint:Maint-9X5-SW only` (98), other (4)
- These are invoices where someone typed "reinstate" in the description or used the explicit reinstatement item

## What It Misses
Invoices for clients Diana classified as reinstatements based on external knowledge. Example: 5 hardcoded overrides (EMLASCF0006, MALLUN0006, MJRITA0003, MSAPSE0005, MU03590001).

3 of 5 have ZERO distinguishing features on the invoice — generic "Maintenance Plan" descriptions, standard item_names, no reinstatement text.

## Why Programmatic Detection Failed
Tested multiple approaches:
1. **Schedule gap > coverage period**: 429 false positives (44010 lines incorrectly tagged). Catches 97/178 true positives.
2. **Gap > MAX(coverage, 365 days)**: Still 277 false positives.
3. **First invoice per client after lapse**: Barely catches anything because MAX(expiry) includes post-reinstatement schedules.
4. **Between-schedule-entry gaps**: Only catches 1-3 new lines per month.

Root cause of failure: reinstatement is **per-LSID**, not per-client. A client can have 3 LSIDs, one reinstated and two continuously active. The invoice/schedule data doesn't distinguish LSID-level coverage.

## How to Close the Gap
Import Diana's reinstatement client list into `lookup.reinstatement_clients`:
```sql
INSERT INTO lookup.reinstatement_clients (client_id, client_name, source, effective_date, notes)
VALUES ('XXXXX', 'Client Name', 'diana_list', '2025-01-01', 'From Diana reinstatement file');
```
Then run:
```sql
SELECT finance.rebuild_deferred_maintenance();
```

## Table Schema
```sql
lookup.reinstatement_clients (
    client_id TEXT PRIMARY KEY,
    client_name TEXT,
    source TEXT DEFAULT 'diana_list',
    effective_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
)
```

Currently contains: 5 override clients + 142 text-match clients (circular, low value).
