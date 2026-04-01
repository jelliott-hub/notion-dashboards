# Phase 2.5: finance.v_catchall_monitor — Results

**Date:** 2026-04-01
**Database:** Supabase `dozjdswqnzqwvieqvwpe` (B4All-Hub)
**SQL file:** `sql/phase2/2_5_catchall_monitor.sql`

---

## What Was Built

`finance.v_catchall_monitor` — a monitoring view that aggregates `finance.v_je_catchall_txn` by month and surfaces:

| Column | Description |
|---|---|
| `report_month` | Month bucket (first of month) |
| `uncaptured_line_count` | Number of JE lines not matched by any dedicated ETL view |
| `uncaptured_total` | Absolute value of net uncaptured amount |
| `uncaptured_debit_total` | Sum of positive (debit) lines |
| `uncaptured_credit_total` | Sum of absolute value of negative (credit) lines |
| `distinct_accounts` | Array of GL accounts appearing in the catchall |
| `status` | `OK` (<$1K) / `WARN` ($1K–$4,999) / `ALERT` (≥$5K) |
| `mom_change` | Month-over-month delta in `uncaptured_total` (positive = growing, negative = shrinking) |

---

## Current Catchall State (as of run date)

| report_month | lines | uncaptured_total | debit | credit | accounts | status | mom_change |
|---|---|---|---|---|---|---|---|
| 2025-12-01 | 6 | $227,461.31 | $0.00 | $227,461.31 | [43021, 51026] | **ALERT** | NULL (first month) |

Only one month of catchall data exists. All 6 lines are credits (negative amounts). `mom_change` is NULL because there is no prior month to compare against.

---

## Line-Level Breakdown (Dec 2025)

| gl_account | line_type | txn_date | amount |
|---|---|---|---|
| 43021 | revenue | 2025-12-03 | -$9,044.00 |
| 43021 | revenue | 2025-12-12 | -$275.00 |
| 43021 | revenue | 2025-12-17 | -$487.00 |
| 51026 | cogs | 2025-12-31 | -$66,143.31 |
| 51026 | cogs | 2025-12-31 | -$75,936.00 |
| 51026 | cogs | 2025-12-31 | -$75,576.00 |

**43021 subtotal:** -$9,806.00 (3 lines — non-standard Solutions adjustment account)
**51026 subtotal:** -$217,655.31 (3 lines — COGS write-off, year-end batch entries)

---

## Status Tier Logic

```
OK   : |uncaptured_total| < $1,000     — normal noise, no action needed
WARN : |uncaptured_total| $1,000–$4,999 — monitor, may need investigation
ALERT: |uncaptured_total| >= $5,000    — investigate; ETL likely missing a category
```

December 2025 is **ALERT** at $227K. This was a known one-time event (year-end COGS write-offs via 51026 and a Solutions adjustment via 43021). If these accounts recur in future months, a dedicated ETL view should be created.

---

## Recommendations

1. **51026 (COGS write-off):** $217K in three year-end batch entries. If this account appears in Jan 2026+, create `finance.v_je_cogs_writeoff` to capture it explicitly.
2. **43021 (Solutions adjustment):** $9.8K across three transactions. Confirmed one-time. Monitor via this view — if it reappears, categorize it.
3. **Threshold to watch:** Any future month with `status = 'ALERT'` that is NOT a known one-time event requires a new ETL view to reduce catchall scope.
4. **mom_change is your early-warning signal:** A positive `mom_change` > $5K month-over-month means the catchall is actively growing and the ETL is falling behind.
