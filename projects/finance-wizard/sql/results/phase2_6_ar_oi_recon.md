# Phase 2.6 – AR / OI Reconciliation

**View created:** `finance.v_ar_oi_reconciliation`
**Date run:** 2026-04-01
**Months validated:** 2025-01 through 2026-02 (14 months)

---

## Sample Output

| report_month | qb_ar_total | qb_invoice_count | tc_oi_ar | tc_client_count | delta | pct_delta | recon_status |
|---|---|---|---|---|---|---|---|
| 2025-01-01 | 547,134.29 | 1,176 | 547,204.34 | 1,176 | 70.05 | 0.0128% | PASS |
| 2025-02-01 | 684,950.14 | 1,180 | 684,997.19 | 1,180 | 47.05 | 0.0069% | PASS |
| 2025-03-01 | 572,941.50 | 1,165 | 572,988.55 | 1,165 | 47.05 | 0.0082% | PASS |
| 2025-04-01 | 593,105.63 | 1,190 | 593,152.68 | 1,190 | 47.05 | 0.0079% | PASS |
| 2025-05-01 | 674,040.90 | 1,211 | 674,297.99 | 1,211 | 257.09 | 0.0381% | PASS |
| 2025-06-01 | 574,840.37 | 1,214 | 575,097.46 | 1,214 | 257.09 | 0.0447% | PASS |
| 2025-07-01 | 581,788.92 | 1,200 | 581,835.97 | 1,200 | 47.05 | 0.0081% | PASS |
| 2025-08-01 | 651,412.83 | 1,250 | 651,592.65 | 1,250 | 179.82 | 0.0276% | PASS |
| 2025-09-01 | 643,061.96 | 1,226 | 643,241.78 | 1,226 | 179.82 | 0.0280% | PASS |
| 2025-10-01 | 588,665.90 | 1,198 | 588,712.95 | 1,198 | 47.05 | 0.0080% | PASS |
| 2025-11-01 | 413,697.03 | 1,231 | 413,744.10 | 1,231 | 47.07 | 0.0114% | PASS |
| 2025-12-01 | 425,752.89 | 1,277 | 425,752.89 | 1,277 | 0.00 | 0.0000% | PASS |
| 2026-01-01 | 602,688.31 | 1,416 | 602,690.31 | 1,416 | 2.00 | 0.0003% | PASS |
| 2026-02-01 | 664,530.26 | 1,392 | 664,532.26 | 1,392 | 2.00 | 0.0003% | PASS |

---

## Status Summary

| Status | Count | Threshold |
|---|---|---|
| PASS | 14 | ABS(delta) < $1,000 |
| WARN | 0 | $1,000 <= ABS(delta) < $5,000 |
| INVESTIGATE | 0 | ABS(delta) >= $5,000 |

**All 14 months reconcile cleanly.** No WARN or INVESTIGATE flags raised.

---

## Key Findings

### Delta Pattern Analysis

The `tc_oi_ar` figure is consistently higher than `qb_ar_total` across all months. The delta is always positive (TC sees slightly more AR than QB). Three distinct delta tiers were observed:

| Delta Amount | Months |
|---|---|
| ~$0.00 | Dec-2025 |
| ~$2.00 | Jan-2026, Feb-2026 |
| ~$47.05 | Feb, Mar, Apr, Jul, Oct, Nov 2025 |
| ~$179.82 | Aug, Sep 2025 |
| ~$257.09 | May, Jun 2025 |
| ~$70.05 | Jan 2025 |

The consistency of these delta amounts (recurring fixed values rather than random drift) suggests this is a **structural difference** between the two systems, not data corruption. Likely candidates:

- Small recurring charges or adjustments posted in TC that are not yet in QBO (AP-style accruals)
- Platform/service fees captured in the TC OI report that flow through `oi_ap` but land in `oi_ar` depending on billing setup

All deltas are well under the $1,000 PASS threshold (largest is $257.09, or 0.04%). No Controller action required.

---

## View Design Notes

- **Join basis:** `FULL OUTER JOIN` on `report_month` ensures months present in only one system surface as `MISSING_QB` or `MISSING_TC`.
- **Comparison column:** `oi_ar` (not `oi_total`) is used as the TC comparator since it represents the AR-specific line in the OI report. `oi_total = oi_ar + oi_ap`.
- **`pct_delta`:** Expressed as a percentage of `qb_ar_total`. Returns NULL when QB total is zero to prevent divide-by-zero.
- **Thresholds:** PASS < $1K | WARN $1K–$5K | INVESTIGATE > $5K (all absolute value).

---

## Files

- SQL: `sql/phase2/2_6_ar_oi_recon.sql`
- View: `finance.v_ar_oi_reconciliation` (B4All-Hub `dozjdswqnzqwvieqvwpe`)
