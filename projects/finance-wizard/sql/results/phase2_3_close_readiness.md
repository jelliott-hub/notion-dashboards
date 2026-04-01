# Phase 2.3: finance.v_close_readiness

**Deployed:** 2026-04-01  
**View:** `finance.v_close_readiness`  
**SQL:** `sql/phase2/2_3_close_readiness.sql`

---

## What Was Built

A composite month-end close readiness view that aggregates five check categories into a single `overall_status` per month, with a `blocking_items` text array listing exactly what is failing.

### View Columns

| Column | Description |
|---|---|
| `report_month` | First of month (DATE) |
| `pnl_status` | PASS / WARN / FAIL / NO_DATA |
| `pnl_fail_count` | Count of P&L accounts with status = FAIL |
| `pnl_warn_count` | Count of P&L accounts with status = WARN |
| `cash_recon_status` | Worst-case across ACH + PayPal + SwipeSum |
| `ach_status` | PASS / WARN / FAIL / NO_DATA (derived from deposit_variance) |
| `paypal_status` | PASS / WARN / FAIL (INVESTIGATE → FAIL, TIMING/NO_EMAIL_DATA → WARN) |
| `swipesum_status` | PASS / WARN / FAIL / NO_DATA (derived from variance) |
| `ach_abs_variance` | Raw ACH deposit variance (absolute value) |
| `paypal_variance` | Raw PayPal residual_variance |
| `swipesum_variance` | Raw SwipeSum variance |
| `ar_recon_status` | PASS / WARN / FAIL (INVESTIGATE → WARN) |
| `ar_recon_status_raw` | Raw value from v_ar_oi_reconciliation |
| `catchall_status` | PASS / WARN / FAIL (ALERT → FAIL) |
| `catchall_status_raw` | Raw value from v_catchall_monitor |
| `deferred_rev_balance` | Running balance from v_deferred_maint_balance |
| `deferred_status` | PASS / WARN / FAIL (negative balance → FAIL, zero → WARN) |
| `overall_status` | READY only if all checks PASS or WARN |
| `blocking_items` | Text[] of human-readable blocking reasons |

---

## Status Normalization Logic

### P&L (v_pnl_reconciliation)
- Aggregated from per-account rows (uses `period_start` as month key)
- Any account with `status = 'FAIL'` → pnl_status = FAIL (blocking)
- All accounts WARN, none FAIL → pnl_status = WARN (not blocking)

### Cash Reconciliation
- **ACH** (`v_ach_reconciliation_monthly`): no native status; derived from `deposit_variance`
  - `<= $1` → PASS, `<= $500` → WARN, `> $500` → FAIL, `NULL qb_deposits` → NO_DATA
- **PayPal** (`v_paypal_reconciliation_monthly`): native status column
  - `INVESTIGATE` → FAIL | `TIMING`, `NO_EMAIL_DATA` → WARN
- **SwipeSum** (`v_swipesum_reconciliation_monthly`): no native status; derived from `variance`
  - `<= $1` → PASS, `<= $1,000` → WARN, `> $1,000` → FAIL, `NULL qb_total` → NO_DATA
- Cash aggregate = worst case across three. NO_DATA treated as WARN (not blocking alone).

### AR Reconciliation (v_ar_oi_reconciliation)
- `PASS` → PASS | `INVESTIGATE` → WARN (soft — months with partial data)

### Catchall Monitor (v_catchall_monitor)
- `ALERT` → FAIL (blocking) | `WARN` → WARN | `OK` → PASS

### Deferred Revenue (v_deferred_maint_balance)
- Uses column `deferred_balance_23000`
- Negative balance → FAIL | Zero balance → WARN | Positive → PASS

### Overall Status
`READY` only when none of the five check statuses are FAIL or NO_DATA (for PnL, cash, AR, catchall).  
Deferred NO_DATA does not block (data may be absent for future months).

---

## Views Used and Availability

| View | Exists | Month Key Column |
|---|---|---|
| `v_pnl_reconciliation` | YES | `period_start` |
| `v_ach_reconciliation_monthly` | YES | `month` |
| `v_paypal_reconciliation_monthly` | YES | `month` |
| `v_swipesum_reconciliation_monthly` | YES | `month` |
| `v_ar_oi_reconciliation` | YES | `report_month` |
| `v_catchall_monitor` | YES | `report_month` |
| `v_deferred_maint_balance` | YES | `month` |
| `v_clearing_account_balance` | **NOT DEPLOYED** | — |
| `v_pnl_reconciliation_coverage` | **NOT DEPLOYED** | — |

`v_clearing_account_balance` and `v_pnl_reconciliation_coverage` were omitted. The clearing balance check should be added to `blocking_items` once deployed.

---

## Validation Results (recent months)

All months in 2024–2026 returned `NOT_READY`. No month has yet achieved `READY` status due to persistent issues across multiple check categories.

### Sep 2025 – Mar 2026 Detail

| Month | PnL | PnL Fails | Cash | AR | Catchall | Deferred | Status |
|---|---|---|---|---|---|---|---|
| 2026-03 | FAIL | 9 | FAIL | NO_DATA | NO_DATA | $477K | NOT_READY |
| 2026-02 | FAIL | 5 | FAIL | PASS | NO_DATA | $648K | NOT_READY |
| 2026-01 | FAIL | 4 | FAIL | PASS | NO_DATA | $745K | NOT_READY |
| 2025-12 | FAIL | 7 | FAIL | PASS | FAIL | $790K | NOT_READY |
| 2025-11 | FAIL | 8 | FAIL | PASS | NO_DATA | $874K | NOT_READY |
| 2025-10 | FAIL | 4 | FAIL | PASS | NO_DATA | $843K | NOT_READY |
| 2025-09 | FAIL | 4 | FAIL | PASS | NO_DATA | $865K | NOT_READY |

### Key Observations

1. **P&L FAILs are universal** — every month has at least 4 failing accounts. This is the primary blocker across the full date range. Root cause investigation in P&L view warranted.

2. **Cash reconciliation fails for all recent months** — primarily driven by PayPal (all months show `INVESTIGATE`). SwipeSum variances are large in some months (Oct 2025: $602K, Sep 2025: $529K).

3. **AR is generally healthy** — PASS from Aug 2024 onwards, with only 2026-03 showing NO_DATA (data not yet available for that month-end).

4. **Catchall only has one data point** — Dec 2025 shows ALERT. All other months show NO_DATA, suggesting `v_catchall_monitor` coverage is limited to a single month.

5. **Deferred revenue is healthy and positive** across all months (PASS), confirming the 23000 account balance is well-maintained.

---

## Recommended Follow-Up

- **P&L FAILs**: Identify which specific accounts are failing and whether thresholds need adjustment or source data needs reconciliation.
- **PayPal INVESTIGATE**: Persistent large residual variances (e.g., $25K in Jan 2026) suggest systematic missing deposit postings in QB.
- **SwipeSum large variances**: Oct/Sep 2025 show $500K+ gaps — likely a QB posting issue for that processor in those months.
- **Catchall coverage**: `v_catchall_monitor` only covers Dec 2025. Expanding its data window will improve close readiness signal.
- **v_clearing_account_balance**: Deploy and add as check #6 to the view.
