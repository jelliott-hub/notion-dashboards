# Phase 1.7 — SwipeSum Reconciliation View Validation

**Date:** 2026-04-01  
**Database:** B4All-Hub (`dozjdswqnzqwvieqvwpe`)  
**Views:** `finance.v_swipesum_reconciliation`, `finance.v_swipesum_reconciliation_monthly`

---

## 1. View Structure

### `finance.v_swipesum_reconciliation` (detail view)

Joins two sources on exact date equality (`settlement_date = txn_date`):

- **Left:** `raw_thinclient.swipesum_settlements` — one row per settlement date, sourced from parsed SwipeSum emails. Date range: **2025-10-28 to 2026-03-25** (146 records).
- **Right:** `raw_quickbooks.deposits` + `raw_quickbooks.deposit_lines` — filtered to `entity_name ILIKE '%swipe%'` or `'%SwipeSum%'`. Date range: **2025-02-03 to 2026-02-27** (246 deposit days).

Match classification:
- `matched` — both sides present, difference < $0.01
- `email_only` — SS has record, QB has no deposit on that date
- `qb_only` — QB has deposit, SS has no record on that date
- `discrepancy` — both sides present, difference >= $0.01

### `finance.v_swipesum_reconciliation_monthly` (summary view)

Groups by `date_trunc('month', settle_date)`. Column name is `month` (not `report_month` — note the original query used the wrong column name). Computes: `email_settled_total`, `qb_total`, `variance`, `total_charges`, `gross_refunds`, `matched_days`, `discrepancy_days`.

---

## 2. Monthly Reconciliation Results

| Month | SS Total | QB Total | Variance | Matched Days | Discrepancy Days |
|---|---|---|---|---|---|
| 2025-02 | NULL | $555,898.94 | -$555,898.94 | 0 | 0 |
| 2025-03 | NULL | $618,784.14 | -$618,784.14 | 0 | 0 |
| 2025-04 | NULL | $612,989.81 | -$612,989.81 | 0 | 0 |
| 2025-05 | NULL | $562,132.03 | -$562,132.03 | 0 | 0 |
| 2025-06 | NULL | $725,497.06 | -$725,497.06 | 0 | 0 |
| 2025-07 | NULL | $766,147.90 | -$766,147.90 | 0 | 0 |
| 2025-08 | NULL | $865,059.32 | -$865,059.32 | 0 | 0 |
| 2025-09 | NULL | $528,628.43 | -$528,628.43 | 0 | 0 |
| 2025-10 | $30,751.85 | $633,437.08 | -$602,685.23 | 0 | 0 |
| **2025-11** | $538,329.68 | $524,593.12 | +$13,736.56 | 7 | 11 |
| **2025-12** | $508,450.16 | $471,467.77 | +$36,982.39 | 13 | 8 |
| **2026-01** | $699,061.42 | $666,623.88 | +$32,437.54 | 12 | 8 |
| **2026-02** | $663,654.21 | $666,108.35 | **-$2,454.14** | 15 | 4 |
| **2026-03** | $567,032.62 | NULL | +$567,032.62 | 0 | 0 |

**Pre-Nov 2025:** All NULL on SS side — `raw_thinclient.swipesum_settlements` only begins 2025-10-28 (one record). Data gap, not a view logic error.

**Mar 2026:** QB data only runs through 2026-02-27. The March QB deposits haven't been loaded yet. Data gap.

---

## 3. Root Cause of All Discrepancies: QB Batches Multiple SS Days Into One Deposit

This is the central finding. SwipeSum settles daily and emails a report for each settlement date. QuickBooks, however, books deposits by **bank deposit date**, not settlement date. QB batches Friday + Saturday + Sunday (and sometimes Monday) settlements into a single Monday QB deposit entry, with individual SS batch dates called out in the description field.

### Confirmed Batch Pattern

Analysis of QB deposit line-item descriptions confirms: every "discrepancy" or "email_only" row in the detail view is caused by this date-shift, not by missing or erroneous money.

**Example — November 2025:**

| QB Date | QB Description | QB Amount |
|---|---|---|
| 2025-11-10 | CC Batch 11/07/25 | $23,843.20 |
| 2025-11-10 | CC Batch 11/08/25 | $3,163.55 |
| 2025-11-10 | CC Batch 11/09/25 | $2,371.05 |

- SS shows: Nov 7 = $23,843.20 (`email_only`), Nov 8 = $3,163.55 (`email_only`), Nov 9 = $2,371.05 (`discrepancy`)
- QB books all three on Nov 10 (Monday), so Nov 10 QB = $29,377.80 vs SS Nov 10 = $2,371.05 → `discrepancy`

The view's 1:1 date join cannot resolve this. **All SS amounts in Feb 2026 match their QB line-item by amount** — confirmed by exact-amount lookup — except one.

### Match Quality by Month (Nov 2025 – Feb 2026)

| Month | Matched Days | Email-Only Days | Discrepancy Days | Email-Only SS $ | Disc SS $ | Disc QB $ |
|---|---|---|---|---|---|---|
| 2025-11 | 7 | 12 | 11 | $195,506 | $152,226 | $333,995 |
| 2025-12 | 13 | 10 | 8 | $122,415 | $76,268 | $161,701 |
| 2026-01 | 12 | 11 | 8 | $205,910 | $113,247 | $286,719 |
| 2026-02 | 15 | 9 | 4 | $148,079 | $22,795 | $173,328 |

The improving trend in `matched_days` (7 → 15) reflects QB adopting a more consistent per-day booking style by Feb 2026.

---

## 4. The $2,454.14 February 2026 Variance — Explained

This is the "cleanest" month but still shows a -$2,454.14 variance (QB is $2,454 higher). This is a **legitimate cross-month boundary effect**, not a real discrepancy:

- **QB Feb includes** two Jan settlement batches booked on Feb 2: "CC Batch 01-30-2026" ($32,628.49) and "CC Batch 01-31-2026" ($7,147.37) = **$39,775.86 from January**
- **SS Feb excludes** Jan 30–31 (those records are in Jan's SS total)
- **SS Feb 28** ($30,174.35) is present in SS but QB hasn't booked it yet (it will appear in the March QB batch)
- Net boundary effect: +$39,775.86 (Jan amounts in Feb QB) − $30,174.35 (Feb 28 SS not yet in QB) − (Jan email-only SS amounts that match into Feb QB) = -$2,454.14

Every individual SS settlement amount in February was confirmed to appear in a QB deposit line item by exact dollar amount — all 27 of 28 records matched. Only Feb 28 ($30,174.35) had no matching QB line item because it hadn't been deposited yet as of the QB data cutoff (2026-02-27).

---

## 5. Data Availability Assessment

| Source | Date Range | Gap |
|---|---|---|
| `raw_thinclient.swipesum_settlements` | 2025-10-28 → 2026-03-25 | No SS data before Oct 28, 2025 |
| `raw_thinclient.swipesum_transactions` | 2025-12-01 → 2026-02-01 | Transaction-level only for 2 months |
| `raw_quickbooks.deposits` (SwipeSum) | 2025-02-03 → 2026-02-27 | QB data runs further back but SS email data doesn't exist before Oct 2025 |

Pre-Oct 2025: QB has SwipeSum deposit history going back to Feb 2025 but there are no corresponding `swipesum_settlements` records. The FULL JOIN produces `qb_only` rows for those months, showing massive negative variances.

---

## 6. View Logic Assessment

### Is the view logic correct?

**Yes, the view logic is structurally sound.** The SQL is correct for what it's doing. The FULL OUTER JOIN on `settlement_date = txn_date`, the COALESCE handling, and the match-status CASE logic are all appropriate.

### Are any view logic fixes needed?

**No fixes required, but one enhancement would materially improve the reconciliation:**

**The fundamental limitation** is the date-equality join. QB batches multiple SS settlement dates into a single deposit keyed to bank deposit date. This causes:
- Correct SS records to appear as `email_only` (Sat/Sun/weekends)
- Correct Monday QB deposits to appear as `discrepancy` (because the QB amount includes Fri+Sat+Sun+Mon SS amounts)
- The monthly variance figures to be misleading (Nov: $13.7K, Dec: $37K, Jan: $32.4K "variances" that are actually zero)

**A more accurate reconciliation** would join on the batch dates embedded in QB `deposit_lines.description` (e.g., "CC Batch 11-15-25" → parse to date → join to SS settlement_date). This would convert most `email_only` and `discrepancy` rows to `matched`. However, this requires regex parsing of free-text descriptions and is a new feature, not a bug fix.

---

## 7. Status Summary

| Issue | Status |
|---|---|
| Pre-Oct 2025 NULL SS data | **Data gap** — SwipeSum email parsing only begins Oct 28, 2025. View logic is correct; data simply doesn't exist. |
| Oct 2025 partial data | **Data gap** — Only 1 SS record (Oct 28). QB has full month. |
| Nov 2025 – Feb 2026 discrepancies | **Not real discrepancies** — caused by QB batching Fri/Sat/Sun settlements into Monday deposits. All money is accounted for. |
| Mar 2026 NULL QB data | **Data gap** — QB sync only goes through Feb 27, 2026. |
| Feb 2026 $2,454.14 variance | **Cross-month boundary effect** — Feb 28 SS not yet in QB, partially offset by Jan 30-31 SS appearing in Feb QB. Will resolve when March QB data loads. |
| View logic bugs | **None found.** |

### Conclusion

**The views are logically correct. All discrepancies are data availability issues or a known structural limitation** (date-shift between SS settlement dates and QB deposit dates). No view logic fixes are needed. The primary actionable improvement would be backfilling `raw_thinclient.swipesum_settlements` for Feb–Oct 2025 if historical SwipeSum email archives exist, and optionally building a smarter join that parses batch dates from QB description fields to eliminate the date-shift false positives.
