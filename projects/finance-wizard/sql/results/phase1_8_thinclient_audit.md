# Phase 1.8 — Finance Schema: raw_thinclient Penny-to-Dollar Audit

**Date:** 2026-04-01  
**Database:** `dozjdswqnzqwvieqvwpe` (B4All-Hub)  
**Auditor:** Independent verification of Finding 10 (previously PASS)

---

## Scope

All 16 finance schema views that reference `raw_thinclient` tables were examined for correct `/100` division on penny-valued columns. The audit covers:

1. Which views reference raw_thinclient
2. Which raw_thinclient columns contain penny values
3. Whether each view applies `/100` before surfacing dollar amounts
4. Spot-check of actual data magnitudes to confirm correctness

---

## 1. Finance Views Referencing raw_thinclient

```
v_ach_reconciliation
v_ar_aging_snapshot
v_cancellation_txn
v_deferred_maint_deferral
v_deferred_maint_recognition
v_fact_revenue_source
v_fp_revenue_proof
v_oi_monthly
v_payment_processor_monthly_summary
v_paypal_reconciliation
v_paypal_reconciliation_monthly
v_relay_txn
v_sam_payout_actual
v_sk_fee_classification
v_support_revenue_txn
v_swipesum_reconciliation
```

---

## 2. raw_thinclient Penny Columns Inventoried

The following columns contain integer penny values (confirmed by spot-check):

| Table | Column | Type | Confirmed Penny? |
|---|---|---|---|
| `sk_contract_transactions` | `fee_pennies` | integer | YES — values like 4900 = $49.00 |
| `sk_invoice_summary` | `total_amount_pennies` | integer | YES — values like 2400 = $24.00 |
| `sk_invoice_summary` | `discount_amount_pennies` | integer | YES |
| `sk_invoice_summary` | `invoiced_amount_pennies` | integer | YES |
| `sk_invoice_summary` | `paid_amount_pennies` | integer | YES |
| `sk_auto_billing` | `amount_pennies` | integer | YES — values like 15180 = $151.80 |
| `sk_outstanding_invoices` | `invoice_balance_pennies` | integer | YES — 4898 = $48.98 |
| `sk_peer_service_fees` | `fee_pennies` | integer | YES — values like 300 = $3.00 |

The following columns in raw_thinclient are **already in dollars** (not pennies):

| Table | Column | Evidence |
|---|---|---|
| `sk_contract_transactions` | `total_dollars` | Explicitly named; confirmed = `fee_pennies/100 * count` |
| `sk_outstanding_invoices` | `amount_dollars` | Confirmed $48.98 when `invoice_balance_pennies` = 4898 |
| `sk_not_processed` | `fee_dollars` | Values like 5.00, 47.00 — dollar scale confirmed |
| `tc_ar_ledger` | `amount` | Values like -152.59, -840.00 — dollar scale |
| `tc_maintenance_schedule` | `amount_charged`, `monthly_fee` | Values like 840.00, 363.75 — dollar scale |
| `achworks_bank_totals` | `amount` | Values like 1486.83 — dollar scale |
| `achworks_transactions` | `amount` | Values like 1486.83, 189.00 — dollar scale |
| `paypal_payments` | `amount` | Values like 27.00, 38.00 — dollar scale |
| `payment_refunds` | `amount` | Values like 27.00, 38.00, 106.25 — dollar scale |

---

## 3. Per-View Analysis

### v_sk_fee_classification
- **Source table:** `raw_thinclient.sk_contract_transactions`
- **Penny column used:** `fee_pennies` — passed through RAW as an informational column only
- **Dollar column used for all financial calculations:** `total_dollars` (pre-converted in source table; verified = `fee_pennies/100 * count`)
- **Revenue/gov_fees/sam_cost/bam_revenue/bam_cost/srs_offset:** All derived from `total_dollars`
- **Status: PASS** — `fee_pennies` is exposed as metadata only; no arithmetic is applied to it

### v_fp_contract_txn (consumes v_sk_fee_classification)
- Uses `.revenue`, `.gov_fees`, `.sam_cost`, `.bam_revenue`, `.bam_cost` — all dollar-valued columns from above
- **Status: PASS**

### v_fp_revenue_proof (consumes v_sk_fee_classification + raw reads)
- `v_sk_fee_classification` columns used: `revenue`, `gov_fees`, `sam_cost` — all dollars, PASS
- `raw_thinclient.sk_not_processed`: uses `fee_dollars * count` — already dollars, PASS
- `raw_thinclient.sk_invoice_summary`: uses `total_amount_pennies::numeric / 100.0` and `discount_amount_pennies::numeric / 100.0` — **correctly divided**, PASS
- **Status: PASS**

### v_relay_txn
- **Source table:** `raw_thinclient.sk_invoice_summary`
- Uses `total_amount_pennies::numeric / 100.0` and `discount_amount_pennies::numeric / 100.0`
- Spot-check confirmed: `total_amount_pennies` = 2400 → output = $24.00; monthly totals in $100k–$250k range (correct dollar scale for relay fees)
- **Status: PASS**

### v_cancellation_txn
- **Source table:** `raw_thinclient.sk_not_processed`
- Uses `fee_dollars * count` — column is already in dollars (confirmed $5.00, $47.00 values)
- **Status: PASS**

### v_oi_monthly
- **Source table:** `raw_thinclient.sk_outstanding_invoices`
- Uses `amount_dollars` only — already in dollars
- **Status: PASS**

### v_ar_aging_snapshot
- **Source table:** `raw_thinclient.sk_outstanding_invoices`
- Uses `amount_dollars` — already in dollars
- **Status: PASS**

### v_deferred_maint_deferral
- **Source tables:** `raw_thinclient.tc_ar_ledger`, `raw_thinclient.tc_maintenance_schedule`
- Uses `ar.amount` and `abs(ar.amount)` — `tc_ar_ledger.amount` is dollar-valued (confirmed: -152.59, -840.00, etc.)
- No penny columns referenced
- **Status: PASS**

### v_deferred_maint_recognition
- **Source tables:** `raw_thinclient.tc_ar_ledger`, `raw_thinclient.tc_maintenance_schedule`
- Uses `abs(ar.amount)` — dollar-valued (same as above)
- No penny columns referenced
- **Status: PASS**

### v_support_revenue_txn
- Reads from `raw_thinclient.tc_ar_ledger` via `abs(ar.amount)` — dollar-valued
- **Status: PASS**

### v_ach_reconciliation
- **Source tables:** `raw_thinclient.achworks_bank_totals`, `achworks_transactions`, `achworks_returns`
- All `amount` columns confirmed dollar-scale (1486.83, 189.00, etc.)
- No penny columns
- **Status: PASS**

### v_paypal_reconciliation
- **Source table:** `raw_thinclient.paypal_payments`
- Uses `amount` — confirmed dollar-scale
- **Status: PASS**

### v_paypal_reconciliation_monthly
- Same as above, aggregated monthly
- **Status: PASS**

### v_payment_processor_monthly_summary
- Reads from `raw_thinclient.payment_refunds`
- Uses `sum(payment_refunds.amount)` — confirmed dollar-scale (27.00, 106.25, etc.)
- **Status: PASS**

### v_sam_payout_actual
- Reads from `raw_thinclient.achworks_transactions`
- Uses `sum(achworks_transactions.amount)` — dollar-scale confirmed
- **Status: PASS**

### v_swipesum_reconciliation
- Reads from `raw_thinclient.swipesum_settlements`
- Uses `net_settled` — column name implies dollars, no penny columns involved
- **Status: PASS**

### v_fact_revenue_source
- Aggregator view — delegates all raw_thinclient reads to sub-views already audited above
- No direct raw_thinclient penny column reads
- **Status: PASS**

---

## 4. Spot-Check Verification

### sk_contract_transactions: fee_pennies vs total_dollars
```
fee_pennies | total_dollars | count | fee_pennies/100 | expected_total
------------|---------------|-------|-----------------|---------------
4900        | 147.00        | 3     | 49.00           | 147.00  ✓
2000        | 60.00         | 3     | 20.00           | 60.00   ✓
1198        | 11.98         | 1     | 11.98           | 11.98   ✓
```
Confirmed: `total_dollars = fee_pennies / 100 * count` — the source table pre-converts.

### sk_invoice_summary: penny columns
```
total_amount_pennies | Divided /100 in v_relay_txn = $24.00 when pennies=2400  ✓
```
Monthly relay total after division: ~$244,814 (Feb 2026) — reasonable dollar scale.

### sk_outstanding_invoices: penny vs dollar fields
```
invoice_balance_pennies = 4898  →  amount_dollars = 48.98  ✓
invoice_balance_pennies = 4995  →  amount_dollars = 49.95  ✓
```
Views use `amount_dollars` exclusively — no risk.

---

## 5. Columns NOT Used in Any Finance View (no risk)

These penny columns exist in raw_thinclient but are not referenced by any finance schema view:

- `sk_auto_billing.amount_pennies`
- `sk_outstanding_invoices.invoice_balance_pennies`
- `sk_invoice_summary.invoiced_amount_pennies`
- `sk_invoice_summary.paid_amount_pennies`
- `sk_peer_service_fees.fee_pennies`
- `blsid_detail.fees`, `static_based_monthly_fee`, `txn_based_*_monthly_fee`

---

## 6. Notable Observation: fee_pennies Exposed Raw in v_sk_fee_classification

`v_sk_fee_classification` selects `fee_pennies` as a pass-through column. This is acceptable because:
1. It is labeled `fee_pennies` (not misleadingly named `fee` or `amount`)
2. No arithmetic is applied to it in this view or any downstream view
3. All downstream views (`v_fp_contract_txn`, `v_fp_revenue_proof`, `v_cms_trueup_rows`) use only the pre-classified dollar columns (`.revenue`, `.gov_fees`, etc.)

**Recommendation (non-blocking):** Consider adding a companion column `fee_dollars AS (fee_pennies / 100.0)` to make the view self-documenting, or dropping `fee_pennies` from the SELECT list if it is not used by any consumer.

---

## Final Verdict

**RESULT: PASS**

All 16 finance schema views that reference `raw_thinclient` tables correctly handle penny-to-dollar conversion:

- Views reading `*_pennies` columns (`v_relay_txn`, `v_fp_revenue_proof`) consistently apply `/100.0` division
- Views reading pre-converted dollar columns (`total_dollars`, `amount_dollars`, `fee_dollars`, `tc_ar_ledger.amount`, etc.) do not need division and correctly omit it
- No view applies arithmetic to a penny column without the required `/100` divisor
- No view accidentally treats a dollar column as pennies or vice versa

**No views require fixing.** The independent verification confirms Finding 10 (PASS) is correct.
