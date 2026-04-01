# Phase 3.3: finance.v_close_dashboard — Findings

## Status: DEPLOYED

**View:** `finance.v_close_dashboard`
**SQL:** `sql/phase3/3_3_close_dashboard.sql`
**Executed:** 2026-04-01

---

## Pre-flight Checks

| Object | Exists? | Notes |
|---|---|---|
| `finance.close_checklist` | NO | Not yet created (Phase 3.2 pending); `checklist_pct_complete` returns NULL |
| `finance.v_close_readiness` | YES | Used as primary rollup source |
| `finance.v_pnl_reconciliation` | YES | Account-level P&L recon |
| `finance.v_clearing_account_balance` | YES | BS clearing account open balances |
| `finance.v_catchall_monitor` | YES | Uncaptured transaction monitor |
| `finance.v_ar_oi_reconciliation` | YES | AR open-invoice reconciliation |

---

## View Design

The view unions months across all five source views so no month is dropped even if a source has a gap. For each month it surfaces:

| Column | Source | Notes |
|---|---|---|
| `total_revenue` | `v_pnl_reconciliation` (Income section) | Prefers QB total; falls back to Hub |
| `total_cogs` | `v_pnl_reconciliation` (COGS section) | Same fallback logic |
| `gross_margin` / `gross_margin_pct` | Derived | NULL pct when revenue = 0 |
| `pnl_accounts_passing/failing/total` | `v_pnl_reconciliation` | WARN rows counted as failing |
| `cash_recon_status` | `v_close_readiness` | ACH + PayPal + SwipeSum rollup |
| `clearing_open_count` / `clearing_open_abs_total` / `clearing_status` | `v_clearing_account_balance` | BS_CLEARING account type only |
| `ar_recon_status` / `ar_recon_status_raw` / `qb_ar_total` / `tc_oi_ar` / `ar_delta` | `v_ar_oi_reconciliation` | Raw status pass-through for drill-down |
| `catchall_status` / `catchall_uncaptured_lines` / `catchall_uncaptured_total` | `v_catchall_monitor` | |
| `deferred_rev_balance` / `deferred_status` | `v_close_readiness` | |
| `checklist_pct_complete` | `finance.close_checklist` | NULL (table not yet deployed) |
| `blocking_items` | `v_close_readiness` | Array of human-readable failure strings |
| `overall_health` | Derived | GREEN / YELLOW / RED |

### Overall Health Logic

| Signal | GREEN | YELLOW | RED |
|---|---|---|---|
| Cash | PASS | NO_DATA | FAIL |
| AR | PASS | — | FAIL or NO_DATA |
| Catchall | PASS | — | FAIL or NO_DATA |
| Deferred | PASS | WARN | FAIL |
| Clearing | PASS | WARN or NO_DATA | — |
| PnL accounts | 0 failing | — | >0 failing |

**GREEN** requires all mandatory signals PASS and clearing resolved.
**YELLOW** fires on any warning, missing data on optional signals, or clearing open.
**RED** fires on any hard FAIL or mandatory signal with NO_DATA.

---

## Validation Results (Oct 2025 – Mar 2026)

| Month | Revenue | COGS | Gross Margin % | PnL Pass/Fail/Total | Cash | Clearing Open | AR | Catchall | Health |
|---|---|---|---|---|---|---|---|---|---|
| 2026-03 | $261K | $8K | 97.0% | 0/9/9 | FAIL | $0 | NO_DATA | NO_DATA | RED |
| 2026-02 | $1.92M | $769K | 60.0% | 24/7/31 | FAIL | $391.6K (1 acct) | PASS | NO_DATA | RED |
| 2026-01 | $1.54M | $739K | 52.0% | 27/4/31 | FAIL | $391.1K (1 acct) | PASS | NO_DATA | RED |
| 2025-12 | $1.38M | $595K | 57.0% | 26/7/33 | FAIL | $988.2K (2 accts) | PASS | FAIL | RED |
| 2025-11 | $1.27M | $771K | 39.4% | 22/9/31 | FAIL | $962.1K (2 accts) | PASS | NO_DATA | RED |
| 2025-10 | $1.58M | $893K | 43.6% | 27/4/31 | FAIL | $870.9K (2 accts) | PASS | NO_DATA | RED |

### Key Observations

1. **All months are RED.** No month has achieved a clean close. The primary blockers are:
   - PayPal INVESTIGATE status on cash reconciliation (persistent across all months)
   - SwipeSum variance exceeding threshold (all months)
   - ACH variance in Dec 2025 and Feb 2026
   - PnL FAIL accounts present in every month

2. **Clearing account exposure** is significant: $391K–$988K of open BS_CLEARING balance across recent months, all from the PayPal clearing account (10090).

3. **Catchall alert in Dec 2025:** 6 uncaptured lines totaling $227.5K across accounts 43021 and 51026.

4. **AR reconciliation** is PASS for all months with data (Oct 2025–Feb 2026), with a consistent $2.00 delta.

5. **`v_pnl_reconciliation` has no COGS rows** in the 2032 future-dated months — those are single-account Income rows. The real months (2025–2026) have 31–33 accounts spanning both Income and COGS sections correctly.

---

## Checklist Integration (TODO)

When `finance.close_checklist` is deployed (Phase 3.2), replace the `checklist_pct_complete` column in the view with:

```sql
(SELECT ROUND(
    COUNT(*) FILTER (WHERE completed_at IS NOT NULL)::numeric
    / NULLIF(COUNT(*), 0) * 100, 1
 FROM finance.close_checklist
 WHERE report_month = am.report_month)       AS checklist_pct_complete,
```

Then run `CREATE OR REPLACE VIEW finance.v_close_dashboard AS ...` to activate it with no other changes needed.
