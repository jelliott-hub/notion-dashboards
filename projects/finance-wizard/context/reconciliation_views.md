# Reconciliation Views — ACH, PayPal, SwipeSum

## ACH (Fixed 2026-03-31)

### v_ach_reconciliation
**Problem**: LATERAL JOIN with LIMIT 1 allowed same QB deposit to match multiple settlements. Jan variance: -$67K.
**Fix**: ROW_NUMBER ranked matching. Candidates generated via CROSS JOIN within ±1 day, scored by amount proximity then date proximity. Partitioned by BOTH settlement and deposit sides to enforce 1:1.

**Source tables**:
- `raw_thinclient.achworks_bank_totals` — settlement amounts
- `raw_thinclient.achworks_transactions` — debit/credit detail (source='email_csv')
- `raw_quickbooks.deposits` + `deposit_lines` — QB deposits (entity_name ILIKE '%ACH Works%', account_name ILIKE '%Fingerprinting%')
- `raw_quickbooks.purchases` — QB expenses (vendor_name ILIKE '%ACH Works%')
- `raw_thinclient.achworks_returns` — return transactions

**Post-fix**: Jan variance: $0. Feb: $533 on 1 discrepancy day.

### v_ach_reconciliation_monthly
Not changed — reads same column interface from v_ach_reconciliation.

## PayPal (Fixed 2026-03-31)

### v_paypal_reconciliation_monthly
**Problem**: Compared email gross to QB net deposits (showed phantom 33.8% fee). Daily vs batch timing mismatch.
**Fix**: 
- Applies expected PayPal fee: 3.49% + $0.49/txn
- Computes `expected_net = email_gross - expected_fees`
- `residual_variance = expected_net - qb_deposits` (flags only what's beyond expected fees)
- Added `cumulative_email_gross` and `cumulative_qb_deposits` for rolling reconciliation
- Status thresholds: PASS (<$50), TIMING (<$500), INVESTIGATE (>$500)

**Dependent view**: `v_payment_processor_monthly_summary` — updated to use `residual_variance` instead of `gross_net_gap` for PayPal's contribution to total_variance_all_processors.

**Known issue**: Nov 2025-Jan 2026 show large residuals ($25K-$53K) suggesting QB deposit data is incomplete for those months (pre-migration data quality, not logic issue).

### v_paypal_reconciliation (detail view)
Not changed in this session — still uses date-level matching.

## SwipeSum
Not changed — `v_swipesum_reconciliation` and `v_swipesum_reconciliation_monthly` were not part of the 7-issue report.
