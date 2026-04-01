# Phase 2.4: `finance.v_shipping_cogs_reclass` — Findings

**Date:** 2026-04-01  
**View:** `finance.v_shipping_cogs_reclass`  
**SQL File:** `sql/phase2/2_4_shipping_cogs.sql`

---

## Summary

The view surfaces shipping COGS reclass status for the Controller's close tasks 3.15 and 3.25. Account 53030 (Shipping COGS) is the target; the view compares shipping revenue billed to customers (account 43070) against what has been posted to 53030, with the delta shown as `reclass_amount`.

---

## Data Sources

| Source | Field Used | Purpose |
|---|---|---|
| `raw_quickbooks.pnl_monthly` | `gl_code = '43070'` | Shipping revenue billed to customers |
| `raw_quickbooks.report_cogs_transactions` | `account_name = '53030 - Shipping'` | COGS already posted to target account |
| `raw_quickbooks.journal_entry_lines` + `journal_entries` | `description ILIKE '%breakout%'` | Historical JE reclass entries for 53030 |

---

## Key Findings

### Shipping Item Names in Invoice Lines

The following item names represent shipping in `raw_quickbooks.invoice_lines`:

| item_name | count | total_amount |
|---|---|---|
| Ship - L | 3,530 | $270,919.93 |
| Ship - XL | 65 | $41,401.14 |
| Ship - M | 315 | $12,845.00 |
| Ship - Cab | 8 | $5,100.00 |
| Ship - S | 128 | $2,620.00 |
| ACC - LS4G Shipping Enclosure | 1 | $8,800.00 |

All match on `il.item_name ILIKE 'Ship -%'` plus the LS4G enclosure item.

### Account 53030 Coverage (2024-01 to 2026-02)

| Month | Shipping Rev (43070) | COGS Posted (53030) | Reclass Gap |
|---|---|---|---|
| 2024-01 | $4,238.00 | $10,076.95 | -$5,838.95 |
| 2024-02 | $2,266.00 | $3,060.81 | -$794.81 |
| 2024-03 | $1,980.00 | $1,554.26 | **+$425.74** |
| 2024-04 | $2,054.00 | $2,369.19 | -$315.19 |
| 2024-05 | $3,450.00 | $2,426.01 | **+$1,023.99** |
| 2024-06 | $2,788.00 | $3,140.58 | -$352.58 |
| 2024-07 | $3,852.00 | $1,978.18 | **+$1,873.82** |
| 2024-08 | $12,682.00 | $11,230.62 | **+$1,451.38** |
| 2024-09 | $3,254.01 | $2,674.94 | **+$579.07** |
| 2024-10 | $2,274.30 | $2,102.53 | **+$171.77** |
| 2024-11 | $5,922.00 | $9,416.76 | -$3,494.76 |
| 2024-12 | $1,300.00 | $1,699.49 | -$399.49 |
| 2025-01 | $2,965.00 | $2,898.45 | **+$66.55** |
| 2025-02 | $1,774.34 | $1,377.82 | **+$396.52** |
| 2025-03 | $1,710.00 | $2,542.41 | -$832.41 |
| 2025-04 | $3,031.47 | $3,708.24 | -$676.77 |
| 2025-05 | $1,682.00 | $2,559.13 | -$877.13 |
| 2025-06 | $4,380.00 | $3,372.39 | **+$1,007.61** |
| 2025-07 | $1,068.00 | $7,746.51 | -$6,678.51 |
| 2025-08 | $1,200.00 | $13,653.21 | -$12,453.21 |
| 2025-09 | $1,330.00 | -$15,873.26 | **+$17,203.26** |
| 2025-10 | $1,360.00 | $2,019.95 | -$659.95 |
| 2025-11 | $2,268.00 | $2,521.42 | -$253.42 |
| 2025-12 | $2,690.00 | $2,725.59 | -$35.59 |
| 2026-01 | $2,679.40 | $3,394.46 | -$715.06 |
| 2026-02 | $3,990.00 | $2,797.04 | **+$1,192.96** |

### Reclass Method Changed in Aug 2024

**Pre-Aug 2024:** Shipping carrier costs were initially posted to `65020 - Postage` (an office expense account). The Controller ran a monthly JE at close to move the balance to `53030 - Shipping` (description: "To breakout COGS"). These JEs are visible in `raw_quickbooks.journal_entry_lines`.

**Aug 2024 onward:** Carrier invoices (UPS/FedEx) are now posted directly to `53030` via Expense and Bill transactions. No JE reclass needed for the carrier-cost portion; however, JE reclass for the invoice-side breakdown may still apply in some months.

### Notable Anomaly: Sep 2025

The `53030` balance for Sep 2025 is **-$15,873.26** due to a `Vendor Credit` entry of -$18,283.39. This is a large credit (likely a carrier billing dispute or rebate) and causes the `reclass_amount` to spike to +$17,203.26. The Controller should confirm this credit is correct before treating it as an open reclass need.

### JE Reclass History

Monthly JE reclass ("To breakout COGS") ran from **Jan 2023 through Sep 2024** — 21 months total. The last JE reclass to 53030 with a positive debit amount was **Jul 2024 ($1,978.18)**. The Aug 2024 JE also included an accrual reversal pair ($7,900 debit Aug / $7,900 credit Sep) for carrier costs in the last two weeks of the month.

---

## View Design

```sql
finance.v_shipping_cogs_reclass
```

| Column | Source | Description |
|---|---|---|
| `report_month` | derived | First day of the calendar month |
| `shipping_revenue` | `pnl_monthly` gl_code 43070 | What customers were billed for shipping |
| `shipping_cogs_posted` | `report_cogs_transactions` 53030 | All amounts already in 53030 (any txn type) |
| `je_reclass_applied` | `journal_entry_lines` | JE-specific debit net to 53030 (breakout entries) |
| `shipping_cogs_needed` | = shipping_revenue | Pass-through proxy for expected COGS level |
| `reclass_amount` | needed - posted | Positive = shortfall; negative = over-posted |
| `je_reclass_done` | boolean | TRUE if a breakout JE was posted this month |
| `cogs_coverage_ratio` | posted / revenue | How much of revenue is covered by COGS |

---

## Usage Notes

- **Positive `reclass_amount`:** The month has shipping revenue that hasn't been matched by 53030 postings. The Controller should create a JE to debit 53030 / credit the source account (historically 65020-Postage, or the clearing account used).
- **Negative `reclass_amount`:** More is in 53030 than was billed — common when direct carrier expenses exceed invoiced shipping (B4ALL absorbs some freight cost), or when credits/reversals are present.
- **`je_reclass_done = FALSE` with positive gap:** Months that clearly need a close entry.
- **Sep 2025 outlier:** Large vendor credit (-$18,283.39) inflates the reclass_amount. Verify before acting.
- Historical data goes back to 2015 in invoice lines, but `report_cogs_transactions` only has 53030 data from Jan 2024 onward.
