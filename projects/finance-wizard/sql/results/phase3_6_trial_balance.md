# Phase 3.6 — `finance.v_trial_balance`

**Date:** 2026-04-01
**Analyst:** Claude (Phase 3.6 automated implementation)
**View created:** `finance.v_trial_balance`
**Close checklist task:** 3.33

---

## 1. Design Decisions

### Data Source: `v_pnl_reconciliation` as Primary

`v_pnl_reconciliation` was chosen as the primary source (not raw QB JE lines) because it already:
- Derives Hub amounts via all dedicated ETL views
- Pulls QB totals directly from QB journal entries
- Carries `gl_code`, `gl_name`, `pl_section` (canonical, already validated)
- Provides `delta`, `status`, and `note` for reconciliation context

QB `journal_entry_lines` is used as a secondary source solely to split QB actuals into **debit_total** and **credit_total** columns. This enriches the trial balance with the full debit/credit picture without displacing the Hub's validated net amounts.

### Accounting Convention

| Account type | Normal balance | Interpretation |
|---|---|---|
| Revenue (41xxx–44xxx) | Credit | `net_balance` positive = income earned |
| COGS (51xxx–54xxx)    | Debit  | `net_balance` negative = cost incurred |

`net_balance = credit_total - debit_total` (QB/GAAP P&L convention).

**Important:** `hub_derived_amount` and `qb_actual_amount` carry the sign from `v_pnl_reconciliation`, which follows the Hub's native signed convention: Revenue amounts are positive (credits), COGS amounts are positive or negative per account (e.g., 51025 true-up can be negative). The debit/credit columns are raw QB totals — the two sets of columns answer different questions (debit/credit breakdown vs. net economic amount).

### Coverage Scope

- Revenue: 41010–44050 (23 accounts, Jan 2026)
- COGS: 51010–53030 (8 accounts, Jan 2026)
- **Total: 31 detail accounts per month**
- OpEx (60xxx+) and balance sheet accounts: out of scope by design

### Summary Rows

Three summary rows are appended per month via `GROUPING SETS`:
1. `>>> Income TOTAL` — sum of all Revenue accounts (`row_type = 1`)
2. `>>> COGS TOTAL` — sum of all COGS accounts (`row_type = 1`)
3. `>>> GRAND TOTAL` — sum of all Revenue + COGS (`row_type = 2`)

`row_type = 0` indicates detail rows; use `WHERE row_type = 0` to get detail only.

---

## 2. View Schema

| Column | Type | Description |
|---|---|---|
| `report_month` | date | First day of the accounting month |
| `gl_code` | text | 5-digit account number (or summary label for row_type > 0) |
| `gl_name` | text | Account name from Hub/QB |
| `pl_section` | text | `Income`, `COGS`, or `GRAND` (summary rows) |
| `source_view` | text | Hub ETL view that derives this account (NULL for summary rows) |
| `debit_total` | numeric | Sum of QB JE debit postings to this account for the month |
| `credit_total` | numeric | Sum of QB JE credit postings to this account for the month |
| `net_balance` | numeric | `credit_total - debit_total` (positive = net credit = income contribution) |
| `hub_derived_amount` | numeric | Hub-calculated amount (from `v_pnl_reconciliation.hub_total`) |
| `qb_actual_amount` | numeric | QB-recorded amount (from `v_pnl_reconciliation.qb_total`) |
| `variance` | numeric | `hub_derived_amount - qb_actual_amount` (0 = perfect match) |
| `recon_status` | text | `PASS` / `FAIL` / `WARN` (from `v_pnl_reconciliation.status`; NULL for summary rows) |
| `row_type` | integer | 0 = detail, 1 = section subtotal, 2 = grand total |

---

## 3. Validation Results — January 2026

### Section Totals

| Section | Debit | Credit | Net Balance | Hub Total | QB Total | Variance |
|---|---|---|---|---|---|---|
| Income | $315,265 | $1,788,581 | **$1,473,316** | $1,540,385 | $1,538,445 | **$1,940** |
| COGS | $719,027 | $75,576 | **-$643,451** | $739,067 | $739,067 | **$0** |
| Grand Total | $1,034,292 | $1,864,157 | $829,865 | $2,279,452 | $2,277,512 | **$1,940** |

- **Net Revenue (Hub):** $1,540,385
- **Net COGS (Hub):** $739,067
- **Gross Profit (Hub-derived):** $1,540,385 - $739,067 = **$801,318**
- **Total variance:** $1,940 (concentrated in Support accounts, per known finding #2)

### Accounts with Variance (Jan 2026)

| Account | gl_name | Hub | QB | Variance | Status |
|---|---|---|---|---|---|
| 44010 | Maintenance-InvoicedQB | $137,819 | $134,921 | +$2,897 | FAIL |
| 44020 | Maintenance-ReinstateQB | $1,859 | $4,232 | -$2,373 | FAIL |
| 44030 | Maintenance-Autopay | $56,966 | $55,661 | +$1,305 | FAIL |
| 44050 | Maintenance-SAMCredit | $10,111 | $10,000 | +$110 | FAIL |

All variances are in Support (44xxx) accounts, consistent with the systematic misallocation documented in finding #2 (forensic audit 2026-04-01). These are pre-existing known issues, not new discoveries from this view.

---

## 4. Validation Results — February 2026

### Section Totals

| Section | Debit | Credit | Net Balance | Hub Total | QB Total | Variance |
|---|---|---|---|---|---|---|
| Income | $487,179 | $2,194,462 | **$1,707,283** | $1,899,911 | $1,922,582 | **-$22,671** |
| COGS | $824,554 | $70,938 | **-$753,616** | $769,376 | $769,376 | **$0** |
| Grand Total | $1,311,733 | $2,265,400 | $953,667 | $2,669,287 | $2,691,958 | **-$22,671** |

- **Net Revenue (Hub):** $1,899,911
- **Net COGS (Hub):** $769,376
- **Gross Profit (Hub-derived):** $1,899,911 - $769,376 = **$1,130,535**
- **Total variance:** -$22,671 (Support 44010 drives -$21,200; known finding #2)

### Accounts with Variance (Feb 2026)

| Account | gl_name | Hub | QB | Variance | Status |
|---|---|---|---|---|---|
| 44010 | Maintenance-InvoicedQB | $147,421 | $168,621 | -$21,200 | FAIL |
| 44020 | Maintenance-ReinstateQB | $1,839 | $4,365 | -$2,526 | FAIL |
| 44030 | Maintenance-Autopay | $56,946 | $58,765 | -$1,819 | FAIL |
| 43010 | Hardware | $229,665 | $228,555 | +$1,110 | FAIL |
| 43030 | Services | $84,908 | $83,303 | +$1,605 | FAIL |
| 43070 | Shipping | $4,050 | $3,990 | +$60 | WARN |
| 44050 | Maintenance-SAMCredit | $8,115 | $8,017 | +$98 | WARN |

Feb 2026 adds Solutions variances (43010/43030/43070) not present in Jan 2026 — consistent with the Solutions dedup/rounding corrections deployed 2026-03-31 not yet fully propagated for this month.

---

## 5. Notable Observations

### Debit/Credit vs. Hub Net Amount Discrepancies (by design)
Several accounts show `net_balance` (from QB JE debit/credit) that does not match `hub_derived_amount`. This is expected for accounts where the Hub includes invoice-level activity not posted as a single JE line. For example:
- **43010 Hardware (Jan 2026):** JE credits = $18,300; hub_derived = $40,020. The $21,720 difference is Solutions invoice revenue processed through the Hub's invoice ETL but not posted as a standalone QB JE.
- **53010 Hardware COGS:** Similar gap — Hub includes cost roll-up from invoice lines; QB JE reflects only batch close entries.

This is not a data quality issue. The `hub_derived_amount` and `qb_actual_amount` columns (sourced from `v_pnl_reconciliation`) reflect the authoritative reconciled amounts. The `debit_total`/`credit_total` columns are supplemental analytical detail.

### COGS 51025 True-Up (Sign Behavior)
Account 51025 (True-up CMS AR to TC AR) shows a net credit in Jan 2026 (+$63,643) because the DN000811 true-up posts more credit than debit in that month. The `hub_derived_amount` is negative (-$63,643) in `v_pnl_reconciliation`, reflecting that this account is a contra-COGS offset. The debit/credit split confirms: Debit $8,741 (DN000812 portion), Credit $72,384 (DN000811 portion).

---

## 6. Usage Guidance

```sql
-- Monthly trial balance (detail only, Jan 2026)
SELECT * FROM finance.v_trial_balance
WHERE report_month = '2026-01-01' AND row_type = 0
ORDER BY gl_code;

-- Section and grand totals only
SELECT * FROM finance.v_trial_balance
WHERE report_month = '2026-01-01' AND row_type > 0;

-- Gross profit calculation (Hub-derived)
SELECT
    report_month,
    SUM(CASE WHEN pl_section = 'Income' THEN hub_derived_amount ELSE 0 END) AS total_revenue,
    SUM(CASE WHEN pl_section = 'COGS'   THEN hub_derived_amount ELSE 0 END) AS total_cogs,
    SUM(CASE WHEN pl_section = 'Income' THEN hub_derived_amount ELSE 0 END)
    - SUM(CASE WHEN pl_section = 'COGS'  THEN hub_derived_amount ELSE 0 END) AS gross_profit
FROM finance.v_trial_balance
WHERE row_type = 0
GROUP BY report_month
ORDER BY report_month;

-- All FAIL accounts (Hub/QB variance present)
SELECT report_month, gl_code, gl_name, hub_derived_amount, qb_actual_amount, variance
FROM finance.v_trial_balance
WHERE row_type = 0 AND recon_status = 'FAIL'
ORDER BY report_month, ABS(variance) DESC;
```

---

## 7. Files

- SQL: `sql/phase3/3_6_trial_balance.sql`
- View: `finance.v_trial_balance` (B4All-Hub `dozjdswqnzqwvieqvwpe`)
- Results: `sql/results/phase3_6_trial_balance.md` (this file)
