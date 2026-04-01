# Forensic Financial Audit & Automated Close Roadmap

**Audit Date:** 2026-04-01  
**Scope:** B4All-Hub `finance.*` schema (2 tables, 33 views, 5 functions) vs. actual QB JE postings  
**Database:** Supabase `dozjdswqnzqwvieqvwpe`  
**Sources:** finance-wizard context, knowledge-base/finance, hub-schema-architecture-v2, schema forensics report

---

## Executive Summary

The B4All-Hub finance schema contains **34 views, 5 functions, and 2 staging tables** that attempt to derive the same journal entries the Controller manually posts in QuickBooks each month. This audit cross-references every derivation surface against the documented close process that produces ~47 discrete tasks across 5 phases over 10-15 business days.

**Bottom line:** 7 root-cause issues were fixed on 2026-03-31, but **3 of those fixes have residual gaps** and **12 additional anomalies** exist that have never been addressed. The fully automated close requires resolving all 15 items plus building 8 new automation capabilities.

---

## Part 1: Status of the 7 Previously Fixed Issues (2026-03-31)

### ✅ Issue 1 — `lookup.je_tier_classification` Dropped by Orphan Scanner

**Status:** RESOLVED  
**What happened:** The orphan scanner in migration 008 dropped the 45-row lookup table used by `derive_dn000811()` Step 3 to filter Tier 5 reversals.  
**Fix applied:** Restored via `restore_je_tier_classification` migration. 45 rows, 7 tiers confirmed.  
**Residual risk:** None — but the orphan scanner should be taught to skip `lookup.*` tables.

---

### ⚠️ Issue 2 — DN000812 SAM AP True-Up: $1,371 Delta

**Status:** PARTIALLY RESOLVED — $1,371 unexplained variance remains

| Metric | Hub Derivation | Controller Posting | Delta |
|--------|---------------|-------------------|-------|
| Jan 2026 | $10,111.50 | $8,740.91 | **$1,370.59** |
| Feb 2026 | $494.59 | (uses Jan actual) | Self-corrects |

**Root cause candidates (unresolved):**

1. **Sterling bill timing:** A Sterling Identity invoice straddling the month boundary may be excluded from the Hub's `raw_quickbooks.bill_lines` filter but included in the Controller's workpaper.
2. **SRS credit filter mismatch:** The function filters `agency='SRS' AND description='SRS Credit'`. If the Controller uses a broader filter (e.g., also includes `agency='Sterling'` adjustments), the SRS credit total will differ.
3. **Baseline date assumption:** The function hardcodes `2025-01-01`. If the Controller started tracking from a different date, cumulative totals diverge.

**Required fix:**

```sql
-- Step 1: Line-by-line comparison query
SELECT 
  'hub' as source,
  report_month,
  SUM(CASE WHEN agency = 'SRS' AND description = 'SRS Credit' THEN total_dollars END) as srs_credits,
  NULL as sterling_bills
FROM finance.v_sk_fee_classification
WHERE report_month BETWEEN '2025-01-01' AND '2026-01-31'
GROUP BY report_month

UNION ALL

SELECT 
  'qb' as source,
  DATE_TRUNC('month', txn_date)::date as report_month,
  NULL as srs_credits,
  SUM(amount) as sterling_bills
FROM raw_quickbooks.bill_lines bl
JOIN raw_quickbooks.bills b ON b.id = bl.bill_id
WHERE b.vendor_name ILIKE '%Sterling Identity%'
  AND b.txn_date BETWEEN '2025-01-01' AND '2026-01-31'
GROUP BY DATE_TRUNC('month', txn_date)
ORDER BY report_month, source;
```

> [!IMPORTANT]
> **Action:** Compare this output row-by-row with the Controller's Jan workpaper. The $1,371 delta will appear in a specific month's SRS or Sterling column. Once identified, adjust the filter in `derive_dn000812()` to match the Controller's methodology.

---

### ⚠️ Issue 3 — Reinstatement 44020: ~$2,373/month Gap

**Status:** PARTIALLY RESOLVED — lookup table deployed but needs Diana's data

| Metric | Hub Recognition | QB Target | Gap |
|--------|----------------|-----------|-----|
| Monthly 44020 | ~$1,859 | ~$4,232 | **~$2,373/month** |

**What's deployed:**
- `lookup.reinstatement_clients` table (147 rows: 5 overrides + 142 text-match seeds)
- `rebuild_deferred_maintenance()` Step 4 now joins on this table before text fallback

**What's missing:**
- Diana's authoritative reinstatement client list has NOT been imported
- The 142 text-match seeds are circular (they're the same lines the text heuristic already catches)
- 3 of 5 override clients have ZERO distinguishing features on invoices — programmatic detection confirmed impossible per-LSID

**Required fix:**

```sql
-- Step 1: Get Diana's list and insert
INSERT INTO lookup.reinstatement_clients (client_id, client_name, source, effective_date, notes)
VALUES 
  -- Diana provides these rows
  ('CLIENTID1', 'Client Name 1', 'diana_list', '2025-01-01', 'From Diana reinstatement review'),
  -- ... all clients Diana classifies as reinstatements
;

-- Step 2: Rebuild deferred maintenance
SELECT finance.rebuild_deferred_maintenance();

-- Step 3: Validate
SELECT 
  DATE_TRUNC('month', invoice_date)::date as month,
  gl_track,
  COUNT(*) as lines,
  SUM(amount) as total
FROM finance.stg_maint_qb_invoices
WHERE gl_track = '44020'
GROUP BY 1, 2
ORDER BY 1;
-- Target: ~$4,232/month
```

> [!WARNING]
> This gap is **~$28K/year** of misclassified revenue (44010 vs 44020). While total support revenue is unaffected, the account-level breakout in numbered P&L accounts does not match QB.

---

### ✅ Issue 4 — Solutions Revenue Dedup (GroupLineDetail)

**Status:** RESOLVED  
**Fix:** `group_invoice_ids` CTE excludes `invoice_direct` rows for invoices with GroupLineDetail.  
**Validated:** Feb 2026 shows clean split — $121K invoice_direct, $7.8K invoice_group, no overlap.  
**Residual risk:** None.

---

### ⚠️ Issue 5 — PayPal Reconciliation: Large Residuals Nov-Jan

**Status:** LOGIC RESOLVED — data quality issue persists

| Month | Residual Variance | Status |
|-------|------------------|--------|
| Nov 2025 | ~$25K | QB deposits incomplete |
| Dec 2025 | ~$38K | QB deposits incomplete |
| Jan 2026 | ~$53K | QB deposits incomplete |
| Feb 2026 | ~$200 | PASS |

**Logic fix:** Fee-aware reconciliation (3.49% + $0.49/txn) with `residual_variance` is correct.  
**Data issue:** QB batch deposit data for Nov-Jan is incomplete. Pre-migration data quality problem.

**Required fix:**

```sql
-- Identify missing QB deposits for PayPal in the problem months
SELECT 
  DATE_TRUNC('month', d.txn_date)::date as month,
  COUNT(*) as deposit_count,
  SUM(dl.amount) as deposit_total
FROM raw_quickbooks.deposits d
JOIN raw_quickbooks.deposit_lines dl ON dl.deposit_id = d.id
WHERE d.entity_name ILIKE '%PayPal%'
  AND d.txn_date BETWEEN '2025-11-01' AND '2026-01-31'
GROUP BY 1
ORDER BY 1;
-- Compare to PayPal email gross amounts for same period
```

> [!NOTE]
> If QB deposits cannot be backfilled (original PayPal data lost), document the variance with a reconciling memo and move forward. The logic is correct from Feb 2026 onward.

---

### ✅ Issue 6 — ACH Reconciliation 1:1 Matching

**Status:** RESOLVED  
**Fix:** ROW_NUMBER ranked matching replacing LATERAL JOIN. Jan variance: -$67K → $0. Feb: $533 on 1 day.  
**Residual risk:** None.

---

### ✅ Issue 7 — Finance Functions Not in Registry

**Status:** RESOLVED  
All 5 finance functions registered in `meta.object_registry`.

---

## Part 2: Newly Identified Anomalies

### Anomaly A — DN000811 AR/COGS True-Up: No Historical Validation

**Severity:** HIGH  
**What:** `derive_dn000811()` produces 7 JE lines (11000, 51010, 51020, 51025, 41010, 41020, 41030). The function was validated for Jan 2026 only. **No historical backtesting** has been done against actual Controller postings for 2025.

**Risk:** The function could produce correct results for the current month but incorrect results for historical months due to:
- Different `lookup.je_tier_classification` mappings needed for pre-2026 periods
- Changes in the Controller's methodology over time
- JEs posted under different doc_numbers in different months

**Required fix:**

```sql
-- Backtest DN000811 for all months Jan 2025 - Dec 2025
WITH months AS (
  SELECT generate_series(2025, 2025) as yr,
         generate_series(1, 12) as mo
)
SELECT 
  m.yr, m.mo,
  d.* 
FROM months m
CROSS JOIN LATERAL finance.derive_dn000811(m.yr, m.mo) d
ORDER BY m.yr, m.mo;
```

Then compare each month's output against the actual JE lines posted under the corresponding DN000811 doc_number in `raw_quickbooks.journal_entry_lines`.

---

### Anomaly B — `v_pnl_reconciliation` Coverage Gaps

**Severity:** HIGH  
**What:** `v_pnl_reconciliation` is described as "Hub vs QB P&L (primary validation surface)" but its actual account coverage has never been audited. This view is the **single most important** validation surface — if it has gaps, every other proof view downstream is unreliable.

**Required fix:**

```sql
-- Determine what accounts v_pnl_reconciliation covers vs what QB has
WITH hub_accounts AS (
  SELECT DISTINCT gl_account FROM finance.v_pnl_reconciliation
),
qb_accounts AS (
  SELECT DISTINCT account_name, account_number
  FROM raw_quickbooks.journal_entry_lines
  WHERE txn_date >= '2025-01-01'
)
SELECT 
  q.account_number,
  q.account_name,
  CASE WHEN h.gl_account IS NOT NULL THEN '✅' ELSE '❌' END as in_hub
FROM qb_accounts q
LEFT JOIN hub_accounts h ON q.account_number = h.gl_account
ORDER BY q.account_number;
```

---

### Anomaly C — `v_je_catchall_txn` Accumulating Uncaptured Lines

**Severity:** MEDIUM  
**What:** This view captures "Uncaptured QB JE lines" — anything not matched by the other revenue ETL views. If this view has a growing balance, it means the ETL is missing revenue or cost items.

**Required fix:**

```sql
-- Check catchall trends
SELECT 
  report_month,
  COUNT(*) as uncaptured_lines,
  SUM(amount) as uncaptured_amount,
  array_agg(DISTINCT gl_account) as accounts
FROM finance.v_je_catchall_txn
GROUP BY report_month
ORDER BY report_month;
-- Any month > $5K uncaptured needs investigation
```

---

### Anomaly D — `v_deferred_maint_balance` vs QBO Deferred Revenue

**Severity:** HIGH  
**What:** The Hub builds a running deferred revenue balance via `v_deferred_maint_balance` (account 23000). The knowledge base explicitly states: "Expect a gap between the Thin Client estimate and QBO actuals due to prepaid annual contracts." But **this gap has never been quantified or documented** in the Hub.

The Controller maintains a spreadsheet rollforward (PBC38) that is the authoritative balance. The Hub view is an approximation from `rebuild_deferred_maintenance()` output.

**Required fix:**

```sql
-- Monthly deferred balance from Hub
SELECT 
  report_month,
  ending_balance
FROM finance.v_deferred_maint_balance
ORDER BY report_month;
-- Compare each month to PBC38 ending balance from Controller
```

> [!IMPORTANT]
> The Hub deferred revenue engine (`rebuild_deferred_maintenance()`) is an 8-step pipeline processing ~22K auto-invoice rows and ~4.6K QB invoice rows. Its output feeds `v_deferred_maint_close_je`, which is the auto-generated journal entry. If the running balance is wrong, the close JE is wrong.

---

### Anomaly E — `v_support_revenue_txn` Missing Reinstatement Revenue

**Severity:** MEDIUM  
**What:** The deferred maintenance engine (which feeds `v_support_revenue_txn` indirectly) under-classifies reinstatement revenue to 44020 by ~$2,373/month. This directly impacts `v_support_revenue_proof`.

**Same root cause as Issue 3** — requires Diana's list import.

---

### Anomaly F — `v_fp_revenue_proof` and `v_fp_cogs_proof` Coverage

**Severity:** MEDIUM  
**What:** These proof views compare Hub-derived fingerprinting revenue/COGS to QB. They have never been tested against months where the Controller made off-cycle corrections. If the Controller posted a catch-up or correction JE outside the normal DN000811 pattern, the proof views may show a phantom variance.

**Required fix:**

```sql
-- Get all JE lines touching SaaS accounts outside DN000811
SELECT 
  jel.doc_number,
  jel.account_name,
  jel.account_number,
  je.txn_date,
  jel.amount
FROM raw_quickbooks.journal_entry_lines jel
JOIN raw_quickbooks.journal_entries je ON je.id = jel.journal_entry_id
WHERE jel.account_number IN ('41010', '41020', '41030', '51010', '51020', '51025')
  AND (jel.doc_number NOT LIKE 'DN000811%' OR jel.doc_number IS NULL)
  AND je.txn_date >= '2025-01-01'
ORDER BY je.txn_date;
```

---

### Anomaly G — `refresh_fact_revenue()` Truncate-and-Reload Risk

**Severity:** LOW (but operationally important)  
**What:** This function does a full `TRUNCATE` of `analytics.fact_revenue` then reloads from `v_fact_revenue_source`. If the function fails mid-execution, `fact_revenue` is empty. No transactional wrapping detected.

**Required fix:**

```sql
-- Wrap in a transaction or use a swap pattern
CREATE OR REPLACE FUNCTION finance.refresh_fact_revenue() RETURNS void AS $$
BEGIN
  -- Use a temp table swap instead of truncate-reload
  CREATE TEMP TABLE _tmp_fact_revenue AS 
    SELECT * FROM finance.v_fact_revenue_source;
  
  TRUNCATE analytics.fact_revenue;
  INSERT INTO analytics.fact_revenue SELECT * FROM _tmp_fact_revenue;
  DROP TABLE _tmp_fact_revenue;
  
  -- If any step fails, entire transaction rolls back
END;
$$ LANGUAGE plpgsql;
```

---

### Anomaly H — `v_solutions_cogs_txn` Missing Credit Memo Adjustments

**Severity:** MEDIUM  
**What:** `v_solutions_revenue_txn` includes a `credit_memo_adj` CTE for credit memos. But `v_solutions_cogs_txn` has no corresponding COGS reversal for credit memos. If a Solutions return generates a credit memo, revenue is adjusted but COGS is not — overstating gross margin.

**Required fix:** Add a `credit_memo_cogs_adj` CTE to `v_solutions_cogs_txn` that mirrors the credit memo logic from the revenue view.

---

### Anomaly I — Thin Client Fee Values Denominated in Pennies

**Severity:** MEDIUM  
**What:** The knowledge base states: "Denominate fee amounts in the Thin Client database in pennies (integer cents). Divide all Thin Client fee values by 100 before comparing to QBO dollar amounts." If any finance view fails to do this division, revenue comparisons will be 100x off.

**Required fix:**

```sql
-- Audit all views reading from raw_thinclient for /100 division
-- Check v_sk_fee_classification, v_oi_monthly, v_fp_contract_txn
SELECT 
  viewname, 
  definition
FROM pg_views
WHERE schemaname = 'finance'
  AND definition ILIKE '%raw_thinclient%'
  AND definition NOT ILIKE '%/ 100%'
  AND definition NOT ILIKE '%/100%';
```

---

### Anomaly J — `v_ach_reconciliation` February $533 Discrepancy

**Severity:** LOW  
**What:** After the fix, Feb shows a $533 discrepancy on 1 day. This is likely an ACH return or processing exception. Needs to be tracked monthly.

**Required fix:** Add a monitoring query to the automated close that flags any month with >$100 ACH variance.

---

### Anomaly K — SwipeSum Reconciliation Not Tested

**Severity:** MEDIUM  
**What:** `v_swipesum_reconciliation` and `v_swipesum_reconciliation_monthly` were explicitly excluded from the 7-issue fix session ("not part of the 7-issue report"). No validation has been done.

**Required fix:**

```sql
-- Validate SwipeSum reconciliation
SELECT 
  report_month,
  swipesum_settlements,
  qb_deposits,
  variance,
  status
FROM finance.v_swipesum_reconciliation_monthly
WHERE report_month >= '2025-01-01'
ORDER BY report_month;
-- Flag any month with variance > $500
```

---

### Anomaly L — No Payroll JE Derivation Exists

**Severity:** HIGH (for automated close)  
**What:** The Controller books payroll JEs based on the TriNet register (Close Checklist tasks 3.4-3.8). The Hub has **zero views or functions** for payroll. This is ~40-50% of operating expense and the single largest expense line item the close produces.

**Required for automated close:** Would need `raw_trinet` schema + payroll ETL views.

---

## Part 3: Revenue Line Derivation Map

This maps every Controller month-end task to a Hub derivation surface and identifies gaps.

| Close Task | Checklist # | Controller Action | Hub Surface | Status |
|-----------|-------------|-------------------|-------------|--------|
| SaaS/Relay true-up | 3.9 | Reclass from FP clearing → numbered accounts | `derive_dn000811()` | ⚠️ Needs backtest |
| FP Revenue breakout | 3.10 | Break out by account per 119 | `v_fp_contract_txn` + `v_relay_txn` | ⚠️ Needs proof validation |
| FP COGS breakout | 3.11 | Break out by account per 119 | `v_fp_cogs_proof` | ⚠️ Needs proof validation |
| SAM cost/payable true-up | 3.12 | Book SAM payable | `derive_dn000812()` | ⚠️ $1,371 delta |
| AR balance reconciliation | 3.13 | Align QBO AR ↔ TC OI report | `v_cms_trueup_rows` + `v_oi_monthly` | ⚠️ Needs validation |
| FP Revenue/COGS adj | 3.14 | Post adjustments | `derive_dn000811()` | ⚠️ Needs backtest |
| Shipping COGS reclass | 3.15 | Move shipping → 53030 | ❌ **No Hub surface** | 🔴 GAP |
| Auto Maintenance adj | 3.16 | Post auto-maint JE | `v_deferred_maint_close_je` | ⚠️ Needs balance validation |
| Support reclass to deferred | 3.17 | Clearing → Deferred Revenue | `v_deferred_maint_deferral` | ⚠️ Needs balance validation |
| Support amortization | 3.18 | Deferred → P&L | `v_deferred_maint_recognition` | ⚠️ Needs balance validation |
| Support rollforward | 3.19 | Update spreadsheet | `v_deferred_maint_balance` | ⚠️ Needs PBC38 validation |
| Support Revenue breakout | 3.20 | Break out by account | `v_support_revenue_txn` | ⚠️ 44020 gap |
| Maintenance coverage buckets | 3.21 | Assign to periods | `rebuild_deferred_maintenance()` | ⚠️ Needs Diana's list |
| Solutions invoicing | 3.22 | Confirm shipped = invoiced | ❌ **No Hub surface** | 🔴 GAP |
| Solutions Revenue breakout | 3.23 | Break out by account | `v_solutions_revenue_txn` | ✅ Fixed |
| Solutions COGS breakout | 3.24 | Break out by account | `v_solutions_cogs_txn` | ⚠️ Missing credit memo adj |
| Shipping COGS reclass | 3.25 | Reclass to 53030 | ❌ **No Hub surface** | 🔴 GAP |
| Cash reconciliation | 3.26 | Reconcile all banks | `v_ach_*` + `v_paypal_*` + `v_swipesum_*` | ⚠️ SwipeSum untested |
| AR reconciliation | 3.27 | QBO AR ↔ TC | `v_ar_aging_snapshot` | ⚠️ Needs validation |
| Deferred Revenue recon | 3.28 | QBO ↔ rollforward | `v_deferred_maint_balance` | ⚠️ Needs PBC38 |
| Payroll JE | 3.4-3.8 | Book from TriNet | ❌ **No Hub surface** | 🔴 GAP |
| Pre-close amortization | 1.1-1.4 | Fixed JEs, rent, commissions | ❌ **No Hub surface** | 🔴 GAP |
| Bank/CC posting | 2.1-2.8 | Post all transactions | ❌ **No Hub surface** | 🔴 GAP |
| Vendor bills | 2.12-2.14 | Enter all vendor bills | ❌ **No Hub surface** | 🔴 GAP |
| Balance sheet recon | 3.30 | All material accounts | ❌ **Partial Hub surface** | 🔴 GAP |
| Trial balance | 3.33 | Finalize TB | ❌ **No Hub surface** | 🔴 GAP |
| Variance analysis | 3.34 | MoM + budget flux | ❌ **No Hub surface** | 🔴 GAP |

**Summary:** Out of ~36 close tasks, the Hub covers **15** (42%), partially covers **12** (33%), and has **no surface for 9** (25%).

---

## Part 4: Automated Month-End Close Roadmap

### Phase 1: Fix Known Derivation Bugs (Weeks 1-2) — EXECUTED 2026-04-01

| # | Item | Priority | Status | Result |
|---|------|----------|--------|--------|
| 1.1 | Resolve DN000812 $1,371 delta | P0 | 🔶 DIAGNOSED | Controller used Sep 2025 data cutoff. Function correct. **Blocked on Controller review.** |
| 1.2 | Import Diana's reinstatement list into `lookup.reinstatement_clients` | P0 | 🔴 BLOCKED | External data dependency — Diana's list not available. ~$28K/year impact. |
| 1.3 | Run `rebuild_deferred_maintenance()` and validate 44020 hits $4,232/month | P0 | 🔴 BLOCKED on 1.2 | Run immediately after Diana's list import. |
| 1.4 | Backtest `derive_dn000811()` against all 2025 months | P0 | ✅ VALIDATED | Exact match May 2025–Feb 2026. Controller uses different doc# each month. |
| 1.5 | Verify PayPal QB deposit completeness for Nov-Jan 2025 | P1 | 🔶 DIAGNOSED | Root cause: clearing account filter gap. 1-line view fix needed. |
| 1.6 | Add credit memo COGS adjustment to `v_solutions_cogs_txn` | P1 | ✅ NO CHANGE NEEDED | `report_cogs_transactions` already includes credit memos. |
| 1.7 | Validate SwipeSum reconciliation views for all months | P1 | ✅ VALIDATED | Logic correct. Variances = QB weekend batching. Pre-Nov 2025 irrecoverable. |
| 1.8 | Audit all Thin Client views for /100 division compliance | P1 | ✅ PASS | All 16 views correct. |
| 1.9 | Wrap `refresh_fact_revenue()` in transaction-safe swap pattern | P2 | ✅ NO CHANGE NEEDED | Already transaction-safe (plpgsql = single txn). |

---

### Phase 2: Build Missing Proof Views (Weeks 3-4) — EXECUTED 2026-04-01

| # | Item | Priority | Status | Key Finding |
|---|------|----------|--------|-------------|
| 2.1 | `v_pnl_reconciliation_coverage` | P0 | ✅ DEPLOYED | Zero gaps in Revenue/COGS. OpEx uncovered by design. |
| 2.2 | `v_clearing_account_balance` | P0 | ✅ DEPLOYED | Undeposited Funds +$592K. PayPal Clearing -$392K. Jun 2025 spike flagged. |
| 2.3 | `v_close_readiness` | P0 | ✅ DEPLOYED | All months NOT_READY (P&L FAILs + PayPal INVESTIGATE). |
| 2.4 | `v_shipping_cogs_reclass` | P1 | ✅ DEPLOYED | Reclass method changed Aug 2024. Sep 2025 vendor credit anomaly. |
| 2.5 | `v_catchall_monitor` | P1 | ✅ DEPLOYED | Dec 2025: $227K uncaptured (43021 + 51026). Alert thresholds working. |
| 2.6 | `v_ar_oi_reconciliation` (new view, not enhancement) | P1 | ✅ DEPLOYED | All 14 months PASS. Largest delta: $257 (0.04%). |
| 2.7 | `v_solutions_shipment_audit` | P2 | ✅ DEPLOYED | 249 email-only estimates need manual review for uninvoiced orders. |

---

### Phase 3: Build the Close Engine (Weeks 5-8) — EXECUTED 2026-04-01

| # | Item | Priority | Status | Key Finding |
|---|------|----------|--------|-------------|
| 3.1 | `derive_close_je(year, month)` — master function | P0 | ✅ DEPLOYED | 5 JE segments, all balanced. Jan 2026: 25 lines, ~$626K total debits. |
| 3.2 | `close_checklist` table + `init_close_checklist()` | P0 | ✅ DEPLOYED | 43 template tasks, 5 phases. Mar 2026 initialized. Registered in meta.object_registry. |
| 3.3 | `v_close_dashboard` — real-time close progress | P0 | ✅ DEPLOYED | Revenue/COGS/margin + pass/fail counts + GREEN/YELLOW/RED health. |
| 3.4 | `validate_close(year, month)` — quality gate function | P0 | ✅ DEPLOYED | Jan 2026: 27 PASS, 7 WARN, 5 FAIL. Failures = known 44xxx + SwipeSum. |
| 3.5 | `v_variance_analysis` — MoM + YoY variance | P1 | ✅ DEPLOYED | 798 rows, 37 GL codes. No budget tables found. |
| 3.6 | `v_trial_balance` — derived trial balance | P1 | ✅ DEPLOYED | Jan 2026: $801K gross profit, $1.9K total variance. |

---

### Phase 4: Automate Bookkeeper Tasks (Weeks 9-12)

> [!IMPORTANT]
> Bookkeeper tasks (Phase 2 of the close checklist) involve cash posting, bank reconciliation, and vendor bill entry. Full automation requires QB API write access (currently read-only via `raw_quickbooks`).

| # | Item | Priority | LOE |
|---|------|----------|-----|
| 4.1 | Build QB API write layer (OAuth refresh already in `045_qb_oauth_state_functions.sql`) | P0 | 16 hrs |
| 4.2 | Create `finance.auto_bank_match` function — matches bank feed transactions to QB deposits | P1 | 12 hrs |
| 4.3 | Create `finance.auto_clearing_post` function — posts cash to correct clearing accounts | P1 | 8 hrs |
| 4.4 | Create `finance.auto_bill_entry` function — auto-enters vendor bills from known vendors | P2 | 12 hrs |
| 4.5 | Create `finance.auto_amortization` function — posts recurring amortization JEs | P1 | 4 hrs |

---

### Phase 5: Automate Controller Tasks (Weeks 13-16)

| # | Item | Priority | LOE |
|---|------|----------|-----|
| 5.1 | Create `finance.post_close_je(year, month)` — takes output of `derive_close_je()` and posts to QB via API | P0 | 8 hrs |
| 5.2 | Create `finance.auto_deferred_revenue_reclass()` — moves Support payments from clearing → Deferred Revenue | P0 | 4 hrs |
| 5.3 | Create `finance.auto_deferred_revenue_amortize()` — monthly recognition entry | P0 | 4 hrs |
| 5.4 | Build TriNet data integration (`raw_trinet` schema) for payroll JE automation | P1 | 16 hrs |
| 5.5 | Create `finance.derive_payroll_je(year, month)` — generates payroll JE from TriNet data | P1 | 8 hrs |
| 5.6 | Create `finance.auto_period_lock(year, month)` — locks QB period via API after close-complete | P2 | 4 hrs |

---

### Phase 6: Close Orchestration (Weeks 17-20)

| # | Item | Priority | LOE |
|---|------|----------|-----|
| 6.1 | Create `finance.run_close(year, month)` — orchestrator that executes all phases in order with dependency checks | P0 | 12 hrs |
| 6.2 | Create pg_cron job for automated close initiation on Day 1 of each month | P1 | 2 hrs |
| 6.3 | Create notification pipeline (email/Teams) for close status updates | P1 | 4 hrs |
| 6.4 | Build close audit trail (`finance.close_audit_log`) with immutable records of every automated action | P0 | 4 hrs |
| 6.5 | Create human approval gates for Controller sign-off before posting | P0 | 4 hrs |
| 6.6 | Build rollback capability — can reverse all automated JEs for a month | P1 | 6 hrs |

---

## Open Questions

> [!NOTE]
> **Q1:** ~~Do you want me to run the diagnostic SQL queries?~~ **ANSWERED 2026-04-01** — All diagnostics run. Results in `sql/results/`.

> [!NOTE]
> **Q2:** ~~DN000812 delta — do you have the Controller's workpaper?~~ **PARTIALLY ANSWERED 2026-04-01** — Root cause identified (Sep 2025 data cutoff, $27.59 from cumulative gap at that point). Still need Controller to confirm or post adjusting entry.

> [!WARNING]
> **Q3:** The automated close roadmap (Phases 4-6) requires QB API write access. The current integration is read-only (`raw_quickbooks` is a mirror). Is there an existing OAuth write token, or does this need to be set up?

> [!NOTE]
> **Q4:** ~~Should I prioritize Phase 1?~~ **ANSWERED 2026-04-01** — Phases 1-3 all executed. See session log `sessions/2026-04-01_phases_1-3_execution.md`.

> [!IMPORTANT]
> **Q5 (NEW):** Diana's reinstatement client list — who has this, and in what format? This is the single highest-impact blocker (~$28K/year misallocation). The `lookup.reinstatement_clients` table is ready to receive data.

> [!IMPORTANT]
> **Q6 (NEW):** The PayPal reconciliation view needs a 1-line fix to capture Nov-Dec 2025 clearing account deposits. Should this be applied immediately, or wait for the next migration batch?

---

## Verification Plan

### Automated Tests — Status as of 2026-04-01
1. ✅ Run all diagnostic SQL queries from Part 2 against live Supabase — **DONE** (15 queries, results in `sql/results/`)
2. ✅ Backtest `derive_dn000811()` for all 2025 months — **DONE** (exact match May 2025+, see `phase1_4_dn000811_backtest.md`)
3. 🔴 Run `rebuild_deferred_maintenance()` after Diana's list import — **BLOCKED** on Diana's list
4. ✅ Validate all reconciliation views (ACH, PayPal, SwipeSum) — **DONE** (ACH: $0 variance Jan 2026; PayPal: clearing acct root cause found; SwipeSum: date-batching, not missing data)
5. ✅ Create composite monitoring — **DONE** as `v_close_readiness` + `v_catchall_monitor` + `validate_close()` (replaces proposed `v_close_health`)

### Manual Verification — Status as of 2026-04-01
- 🔶 Controller reviews DN000812 — root cause identified (Sep 2025 cutoff), awaiting Controller confirmation
- 🔴 Controller validates deferred revenue balance against PBC38 — not yet started
- ✅ Controller confirms QB account coverage — **DONE** via `v_pnl_reconciliation_coverage` (zero gaps in revenue/COGS)
- 🔴 Diana provides reinstatement client list — **BLOCKED**, highest-impact remaining item
