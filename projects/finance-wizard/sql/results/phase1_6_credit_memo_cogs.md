# Phase 1.6 — Credit Memo COGS Investigation Results

**Date:** 2026-04-01
**Conclusion: No view change needed. `v_solutions_cogs_txn` already handles credit memos correctly.**

---

## Summary

The concern was that `v_solutions_revenue_txn` has a `credit_memo_adj` CTE but `v_solutions_cogs_txn` does not, potentially overstating gross margin when Solutions returns generate credit memos. Investigation shows the COGS view is already correct.

---

## Findings

### 1. Credit memo lines do NOT post to 53xxx accounts in `credit_memo_lines`

The `raw_quickbooks.credit_memo_lines` table (the QB API object used by the revenue view's `credit_memo_adj` CTE) only references two COGS-related account names:

| Account Ref | Count |
|---|---|
| `Solutions COGS` | 4 rows (all pre-2017) |
| `SaaS Platform COGS:Fingerprinting Svcs Cost` | 1 row |

Neither maps to any specific 53xxx account (`53010 - Hardware`, `53020 - Software & Other`, `53030 - Shipping`, `53040 - Services`). These generic refs cannot be reliably mapped without additional QB account metadata.

### 2. `report_cogs_transactions` already includes credit memo rows

`Credit Memo` is one of 11 distinct `transaction_type` values in `report_quickbooks.report_cogs_transactions` for Solutions COGS accounts. QB's report export consolidates all posting types — unlike the raw API objects, it includes credit memos natively.

### 3. All credit memo COGS rows fall within the current WHERE clause

All 7 credit memo rows in `report_cogs_transactions` post exclusively to `53010 - Hardware`:

| Date | Customer | Account | Amount |
|---|---|---|---|
| 2024-01-03 | UPS Store 7418 | 53010 - Hardware | -52.73 |
| 2024-03-20 | Parkway Postal | 53010 - Hardware | -54.96 |
| 2025-02-06 | JMC Process | 53010 - Hardware | -295.05 |
| 2025-02-06 | JMC Process | 53010 - Hardware | -57.70 |
| 2025-06-23 | Allegany Police Dept. | 53010 - Hardware | -1,900.00 |
| 2025-08-04 | Print Annex | 53010 - Hardware | -116.53 |
| 2025-08-04 | Print Annex | 53010 - Hardware | -309.99 |

**Total credit memo COGS reversals: -$2,786.96**

Zero credit memo rows exist outside the 53xxx filter. The current WHERE clause captures 100% of them.

### 4. No JE-based COGS reversals for credit memos

Zero journal entry lines post to the four Solutions COGS accounts. QB does not use JEs to reverse COGS on credit memos in this system.

### 5. `v_solutions_cogs_txn` already surfaces `credit_memo` as a source_type

The view correctly outputs `source_type = 'credit_memo'` for all 7 rows (confirmed via the validation query).

---

## Why the Revenue View Needs a CTE but the COGS View Does Not

| Dimension | Revenue view | COGS view |
|---|---|---|
| Source table | `raw_quickbooks.invoice_lines` (raw API) | `raw_quickbooks.report_cogs_transactions` (QB report export) |
| Credit memo handling | Not included — must JOIN `credit_memo_lines` separately | Already included as `transaction_type = 'Credit Memo'` rows |
| Data model | Line-item API objects, no credit memo rows in invoice_lines | Pre-aggregated report that consolidates all transaction types |

The revenue view reads raw QB API invoice objects, which by definition cannot contain credit memo lines — those live in a separate `credit_memos` API object. Hence the explicit `credit_memo_adj` CTE. The COGS view reads a QB report export (`Profit & Loss by Transaction Type` or equivalent) that already merges all transaction types into a single table, including credit memos.

---

## Action Taken

No DDL executed. `v_solutions_cogs_txn` is correct as-is.

Investigation SQL saved to: `sql/phase1/1_6_solutions_cogs_credit_memo.sql`
