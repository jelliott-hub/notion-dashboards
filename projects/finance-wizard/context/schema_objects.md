# Finance Schema Object Inventory
**Last verified**: 2026-03-31
**Project**: B4All-Hub (dozjdswqnzqwvieqvwpe)

## Counts: 34 views, 5 functions, 2 staging tables

## Functions

| Function | Purpose | Key Dependencies |
|---|---|---|
| `derive_dn000811(year, month)` | CMS AR/COGS true-up (7 JE lines). Sources OI delta, gov fee adj, SRS/Sterling adj | `raw_thinclient.sk_outstanding_invoices`, `finance.v_sk_fee_classification`, `raw_quickbooks.bill_lines`, `raw_quickbooks.journal_entry_lines`, `lookup.je_tier_classification` |
| `derive_dn000812(year, month)` | SAM AP true-up (2 JE lines). Cumulative SRS-Sterling gap from 2025-01-01 minus prior postings | `finance.v_sk_fee_classification`, `raw_quickbooks.bill_lines`, `raw_quickbooks.journal_entry_lines` |
| `rebuild_deferred_maintenance()` | 8-step pipeline: QB staging, coverage parsing (7 regex passes), gl_track assignment (uses `lookup.reinstatement_clients`), auto-pay staging, schedule sync, logging | `raw_quickbooks.invoice_lines`, `raw_quickbooks.invoices`, `raw_thinclient.tc_maintenance_schedule`, `lookup.reinstatement_clients`, `lookup.qb_customer_crosswalk` |
| `refresh_fact_revenue()` | Loads `v_fact_revenue_source` into `analytics.fact_revenue`. Truncate-and-reload. | `finance.v_fact_revenue_source` |
| `safe_parse_date(text)` | Utility: parses date text safely, returns NULL on failure | None |

## Staging Tables

| Table | Rows | Rebuilt By |
|---|---|---|
| `stg_maint_qb_invoices` | ~4,593 | `rebuild_deferred_maintenance()` — TRUNCATED each run |
| `stg_maint_auto_invoices` | ~22,246 | `rebuild_deferred_maintenance()` — TRUNCATED each run |

## Key Views (grouped by domain)

### Revenue ETL
- `v_fp_contract_txn` — SaaS Platform revenue (~576K rows)
- `v_relay_txn` — Relay per-scan billing
- `v_solutions_revenue_txn` — Solutions from QB invoices + JE breakouts + credit memos (~14K rows). **Fixed 2026-03-31: dedup group vs direct**
- `v_support_revenue_txn` — Deferred revenue engine output (~136K rows)
- `v_cancellation_txn` — Cancellation fees (41210/41220)
- `v_je_catchall_txn` — Uncaptured QB JE lines
- `v_fact_revenue_source` — Master UNION ALL, sole input for `refresh_fact_revenue()`

### Deferred Revenue
- `v_deferred_maint_balance` — Running deferred liability (23000)
- `v_deferred_maint_close_je` — Monthly close JE
- `v_deferred_maint_deferral` — Monthly new deferrals (DR)
- `v_deferred_maint_recognition` — Monthly recognition (CR)

### Fee Classification
- `v_sk_fee_classification` — Master fee classifier (~451K rows). Key columns: report_month, source_region, agency, description, total_dollars, classified_as, revenue, gov_fees, sam_cost
- `v_gov_fee_actual` — Actual gov fee payments from QB bills
- `v_sam_payout_actual` — Actual SAM credit payouts

### Reconciliation
- `v_ach_reconciliation` — ACH detail with 1:1 matching. **Fixed 2026-03-31: ROW_NUMBER replaces LATERAL JOIN**
- `v_ach_reconciliation_monthly` — Monthly ACH summary
- `v_paypal_reconciliation` — PayPal detail
- `v_paypal_reconciliation_monthly` — PayPal monthly with fee-aware analysis. **Fixed 2026-03-31: expected_fees, residual_variance**
- `v_swipesum_reconciliation` — SwipeSum CC detail
- `v_swipesum_reconciliation_monthly` — Monthly SwipeSum summary
- `v_payment_processor_monthly_summary` — Combined processor summary. **Updated 2026-03-31: uses residual_variance for PayPal**

### Proof/Validation
- `v_pnl_reconciliation` — Hub vs QB P&L (primary validation surface)
- `v_fp_revenue_proof` — SaaS Platform + Relay proof
- `v_fp_cogs_proof` — SaaS Platform COGS proof
- `v_solutions_revenue_proof` — Solutions revenue proof
- `v_solutions_cogs_proof` — Solutions COGS proof
- `v_solutions_cogs_txn` — Solutions COGS from QB
- `v_support_revenue_proof` — Support/Maintenance revenue proof
- `v_support_cogs_proof` — Support COGS proof
- `v_support_cogs_txn` — Support COGS from QB JEs

### Other
- `v_ar_aging_snapshot` — AR aging bucket builder
- `v_cms_trueup_rows` — CMS AR/AP true-up JE generator
- `v_oi_monthly` — Monthly OI totals from ThinClient
- `v_qb_estimates` — QB estimates
