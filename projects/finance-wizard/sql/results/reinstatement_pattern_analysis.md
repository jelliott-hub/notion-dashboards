# Reinstatement (44020) Pattern Analysis

**Date:** 2026-04-01
**Source:** Diana's `Reinstatement_Invoices.csv` (208 rows, 188 distinct invoices)
**Method:** Matched CSV invoice numbers against `raw_quickbooks.invoices` + `invoice_lines` to find classification signals

---

## Key Finding: SalesType is Text-Driven, Not Metadata-Driven

There is **no QB metadata field** (class, custom field, department, sales type) that distinguishes reinstatement invoices. The spreadsheet's `SalesType = "Maintenance - QB - reinstatement"` is determined by text content in the invoice.

### Fields Checked (None Are the Driver)
| Field | Result |
|-------|--------|
| `class_ref_name` | Not present in QB data (no ClassRef in `_raw` JSON) |
| `custom_field_1` (P.O. Number) | Generic, not classification-relevant |
| `custom_field_2` (Sales Rep) | Mostly NULL |
| `custom_field_3` (LSID) | Generic, not classification-relevant |
| `sales_term_name` | Mix of "Due on receipt" and "Net 30" — same as regular |
| `item_name` on lines | Same items as regular maintenance (Maint-9X5-SW only, Maint-9X5-Remote) |
| `DepartmentRef` | Not present |

### Where Reinstatement Signal Lives
The classification signal is spread across **three text fields**, in priority order:

1. **`private_note`** — Contains `"Maint Reinst..."` or `"Maint Reinstatement..."` prefix (113 invoices total, 85 maintenance)
2. **`invoice_lines.description`** — First ~150 characters contain action words like "MAINTENANCE REINSTATEMENT", "REINSTATE COVERAGE", "REINSTATEMENT INVOICE", "ONE-TIME REINSTATEMENT FEE"
3. **`invoice_lines.item_name`** — Explicit `Maint:Maint - Reinstatement` item (only 5 invoices)

### Boilerplate Problem
5,801 regular maintenance invoices contain "reinstat" somewhere in their line descriptions — but it's **boilerplate text** like:
- `"Disruption of coverage will result in Reinstatement Fees"`
- `"Reinstatement fee applies 10 days after expiration"`

A naive `description ILIKE '%reinstat%'` produces massive false positives.

---

## Proposed Heuristic (v2)

An invoice is classified as reinstatement (44020) if ANY of these conditions are true:

```sql
-- Condition A: private_note signals reinstatement
private_note ILIKE '%reinst%' AND private_note NOT ILIKE '%reinstall%'

-- Condition B: item_name is the explicit reinstatement item
item_name ILIKE '%reinstat%'

-- Condition C: description STARTS with reinstatement action text (first 150 chars)
-- Excludes boilerplate patterns
LEFT(description, 150) ILIKE '%reinstat%'
  AND LEFT(description, 150) NOT ILIKE '%reinstatement fee applies%'
  AND LEFT(description, 150) NOT ILIKE '%will result in reinstatement%'
  AND LEFT(description, 150) NOT ILIKE '%disruption%reinstatement%'

-- Condition D: standalone reinstatement fee line item
description ILIKE 'reinstatement fee%'
  OR description ILIKE 'one-time reinstatement%'
  OR description ILIKE '%one-time fee to reinstat%'
```

### Confusion Matrix (v2 heuristic)

| | Predicted Yes | Predicted No | Total |
|---|---|---|---|
| **True Reinstatement** | 174 | 17 | 188 |
| **Not Reinstatement** | 71 | 9,864 | 9,935 |

- **Recall:** 174/188 = 92.6%
- **Precision:** 174/245 = 71.0%
- **False Positives:** 71 (need investigation — may be legitimate reinstatements Diana's CSV doesn't capture)
- **False Negatives:** 17 (need investigation — zero-text invoices)

### Known Edge Cases (17 False Negatives)

These invoices have ZERO reinstatement text anywhere in QB data. They can only be caught by:
- Direct lookup table (doc_number-based override)
- External knowledge (e.g., tc_maintenance_schedule gap analysis)

Three confirmed zero-text invoices:
- `MWSPSO0001` — private_note says `"maint 03/01/19 - 02/29/20 - Yr 2 of 5"`, no reinstatement signal
- `MKINGR0046` — KINGR account (should be EXCLUDED anyway), no reinstatement signal
- `CMGPOFF0004` — Credit memo, no text fields populated

---

## Next Steps

1. **Investigate the 71 false positives** — Are they actually reinstatements Diana missed? Or is the heuristic too broad?
2. **Investigate the 17 false negatives** — Are they all truly zero-text? Can private_note patterns catch more?
3. **Validate against P&L** — Run the expanded heuristic through `rebuild_deferred_maintenance()` and check if 44020 monthly totals move toward the $4,232 target
4. **Consider hybrid approach** — Use the heuristic for ~93% coverage + a small lookup table for confirmed zero-text exceptions

---

## Raw Data: Item Names on Reinstatement Invoices

| item_name | Lines | Invoices |
|-----------|-------|----------|
| Maint:Maint-9X5-SW only | 110 | 101 |
| Maint:Maint-9X5-Remote | 86 | 81 |
| Finance Charge 3.2% | 57 | 56 |
| (NULL) | 32 | 17 |
| Maint:Maint-24X7-Onsite | 15 | 1 |
| Svcs-Phone | 8 | 8 |
| HW-LT-Std-Home | 7 | 7 |
| Maint:Maint - Reinstatement | 5 | 5 |
| Maint:Maint-Warr 9X5 | 5 | 5 |
| Other (misc HW, services, discounts) | ~50 | ~40 |

## Private Note Pattern

113 invoices across all QB have `reinst` in `private_note`. Pattern: `"Maint Reinst[atement|ate] [dates]"`.
This is a reliable signal with virtually zero false positives (only 1 false match: `SO114842` = "Reinstall" not "Reinstate").
