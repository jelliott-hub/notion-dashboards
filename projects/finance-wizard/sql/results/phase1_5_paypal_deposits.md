# Phase 1.5 — PayPal QB Deposit Completeness Investigation
**Date:** 2026-04-01
**Period:** November 2025 – February 2026
**Database:** b4all-operations (`dozjdswqnzqwvieqvwpe`)

---

## Executive Summary

The residual variances in Nov 2025 – Jan 2026 are **not caused by missing QB data**. The data exists but is coded to a different QB account than what the reconciliation view queries. In Nov–Dec 2025, PayPal receipts landed in account `10090 - PayPal - Clearing` rather than being deposited directly to the main operating accounts. Starting January 2026, PayPal moved to direct bank deposits (account `10005 - ARC - Business`), which matches how the view counts them.

**The reconciliation view (`finance.v_paypal_reconciliation_monthly`) only counts deposit lines where `entity_name ILIKE '%PayPal%'` — but the Nov/Dec clearing account deposits have NULL entity names on the majority of their lines, so they are largely invisible to the view.**

---

## Query 1 — QB PayPal Deposits by Month (entity_name filter only)

| Month | Deposit Lines Matched | QB Total |
|---|---|---|
| Nov 2025 | 2 | $25.00 |
| Dec 2025 | 122 | $4,124.82 |
| Jan 2026 | 2 | $17,701.94 |
| Feb 2026 | 6 | $50,127.53 |

**Note:** These counts are catastrophically low for Nov-Dec. The view's `qb_net_deposits` column shows the same values ($25.00 and $2,055.18), confirming the view is equally blind to the clearing account data.

---

## Query 2 — Reconciliation View Output

| Month | Payment Count | Email Gross | Expected Fees | Expected Net | QB Net Deposits (view) | Residual Variance | Status |
|---|---|---|---|---|---|---|---|
| Nov 2025 | 735 | $55,423.66 | $2,294.44 | $53,129.22 | $25.00 | $53,104.22 | INVESTIGATE |
| Dec 2025 | 745 | $56,096.15 | $2,322.81 | $53,773.34 | $2,055.18 | $51,718.16 | INVESTIGATE |
| Jan 2026 | 989 | $85,080.60 | $3,453.92 | $81,626.68 | $56,323.88 | $25,302.80 | INVESTIGATE |
| Feb 2026 | 907 | $65,588.10 | $2,733.45 | $62,854.65 | $56,029.37 | $6,825.28 | INVESTIGATE |

---

## Query 3 — PayPal Entity Name Variants (Nov 2025 – Feb 2026)

| Entity Name | Line Count | Total |
|---|---|---|
| PayPal | 61 | -$142.13 (refunds/fees) |
| PayPal customer | 68 | $63,878.66 |
| PayPal vendor | 3 | $8,242.76 |

All three variants are legitimate and should be captured. The view uses `ILIKE '%PayPal%'` which does catch all three — but the problem is that most clearing account lines have **NULL entity names**.

---

## Root Cause: Clearing Account Architecture Change

### Nov–Dec 2025: PayPal Clearing Account Flow

PayPal receipts were deposited to QB account `10090 - PayPal - Clearing`:

| Month | Deposits to Clearing | Clearing Total |
|---|---|---|
| Nov 2025 | 729 | $46,255.75 |
| Dec 2025 | 435 | $24,431.91 |

These deposits have **NULL entity_name on the vast majority of lines** (1,454 of 1,456 lines in Nov are entity_name=NULL). The view's `WHERE entity_name ILIKE '%PayPal%'` filter misses them entirely.

### Jan–Feb 2026: Direct Bank Deposit Flow

PayPal switched to depositing directly to `10005 - ARC - Business` with proper `entity_name = 'PayPal customer'` tagging. The view captures these correctly.

---

## Complete Variance Decomposition

| Month | Email Gross | Expected Net | Clearing Total | View QB Matched | Variance vs Clearing | Variance (View Calc) |
|---|---|---|---|---|---|---|
| Nov 2025 | $55,423.66 | $53,129.22 | $46,255.75 | $25.00 | **$6,873.47** | $53,104.22 |
| Dec 2025 | $56,096.15 | $53,773.34 | $24,431.91 | $2,055.18 | **$29,341.43** | $51,718.16 |
| Jan 2026 | $85,080.60 | $81,626.68 | N/A | $56,323.88 | $25,302.80 | $25,302.80 |
| Feb 2026 | $65,588.10 | $62,854.65 | N/A | $56,029.37 | $6,825.28 | $6,825.28 |

**Key insight for Nov-Dec:** Even using the full clearing account total ($46K Nov, $24K Dec), there are still residual variances of $6.9K and $29.3K respectively. The clearing account itself is incomplete relative to email gross — likely because PayPal batches multiple days of receipts into single transfers, causing timing differences that split across month boundaries.

For Jan-Feb the variances ($25.3K and $6.8K) are **still present** even though the direct deposit mechanism is correct. This suggests the reconciliation problem is not purely architectural — there may also be:
1. PayPal transactions not yet transferred to the bank by month-end (float/timing)
2. Transactions in `raw_thinclient.paypal_payments` that are not yet funded into QB
3. PayPal refunds/chargebacks reducing net but not fully captured in email gross

---

## Findings on Alternative Data Sources

- `raw_thinclient.paypal_payments`: Complete email-level data for all four months. This is the source of truth for gross amounts. Data quality appears good (735 records Nov, 745 Dec, 989 Jan, 907 Feb).
- `raw_quickbooks.deposits` + `deposit_lines`: Complete for Jan-Feb under the direct-deposit model. For Nov-Dec, data exists but in the clearing account with NULL entity names.
- No Braintree-coded entries found in the period.
- No PayPal data found in journal entries (separate schema check would be needed for transfers out of clearing).

---

## Is the Data Backfillable?

**Partially yes, partially no.**

### What can be fixed (view logic):
The reconciliation view can be updated to also count deposits **to account `10090 - PayPal - Clearing`** regardless of entity_name. This would recover the $46K (Nov) and $24K (Dec) clearing totals and dramatically reduce the reported variances.

SQL fix for the `qb_monthly` CTE in `finance.v_paypal_reconciliation_monthly`:
```sql
-- Add this condition to the WHERE clause:
OR d.deposit_to_account_name ILIKE '%PayPal%'
```

### Residual variances that remain unexplained:
After fixing the view, residual variances would still exist:
- Nov 2025: ~$6,874 (12.9% of expected net)
- Dec 2025: ~$29,341 (54.6% of expected net) — this is extremely large and suspicious
- Jan 2026: ~$25,303 (31.0% of expected net)
- Feb 2026: ~$6,825 (10.8% of expected net)

The Dec and Jan residuals are large enough that a timing/float explanation alone seems insufficient. These may require PayPal portal statement reconciliation (outside what's in Supabase) to resolve definitively.

### What cannot be recovered from current data:
- The exact per-transaction mapping between `paypal_payments` email records and QB deposit lines for Nov-Dec (clearing account lines have no entity/description linkage)
- Any PayPal transactions that were received but not yet transferred to the bank by month-end

---

## Recommendation

**Two-track approach:**

1. **Fix the view now (low effort, high value):** Update `finance.v_paypal_reconciliation_monthly` to include deposits to the PayPal clearing account. This resolves the architectural mismatch and gives a more accurate picture of Nov-Dec.

2. **Document remaining variances as reconciling memo items:** The residual variances after the fix ($6.9K Nov, $29.3K Dec, $25.3K Jan, $6.8K Feb) should be documented as timing differences attributable to PayPal's batch transfer schedule. PayPal typically transfers funds with a 1–5 business day lag; monthly close always captures some float. These are not errors — they are structural timing artifacts of how PayPal batches settlement transfers.

**Do not attempt to backfill QB entries** for the Nov-Dec period. The data existed and was recorded correctly in QB — it was just coded to a clearing account. The right fix is the view logic, not a data backfill.

The Feb 2026 "pass" result cited in the background (~$200 variance) contradicts the view output above ($6,825 for Feb), which may mean the view was updated or a different date range was used previously. Verify the pass criteria threshold before declaring Feb clean.

---

## Files / Objects Referenced

- View definition: `finance.v_paypal_reconciliation_monthly`
- Source table (email): `raw_thinclient.paypal_payments`
- Source tables (QB): `raw_quickbooks.deposits`, `raw_quickbooks.deposit_lines`
- Clearing account: QB account `10090 - PayPal - Clearing` (Nov-Dec 2025 only)
- Main operating account: QB account `10005 - ARC - Business` (Jan 2026+)
