# Phase 3.5: finance.v_variance_analysis

**Created:** 2026-04-01  
**Status:** DEPLOYED  
**Supports:** Close checklist task 3.34

---

## Summary

`finance.v_variance_analysis` is a read-only view built on top of `finance.v_pnl_reconciliation`. It provides month-over-month (MoM) and year-over-year (YoY) variance analysis for all 37 P&L GL codes across Income and COGS sections.

---

## Data Coverage

| Metric | Value |
|---|---|
| Total rows | 798 |
| Distinct GL codes | 37 |
| Earliest period | 2024-01-01 |
| Latest period | 2026-02-01 |
| Sections covered | Income, COGS |

**Note:** Pre-2024 periods exist in `v_pnl_reconciliation` but have `qb_total = 0` (hub_total only, no QB mirror). The view filters to `qb_total IS NOT NULL AND qb_total <> 0`, so effective coverage begins January 2024. YoY comparisons are therefore available from January 2025 onward.

---

## Budget Tables

No budget, plan, or forecast tables were found in the `finance` or `analytics` schemas. Budget columns (`budget_amount`, `budget_variance`, `budget_pct`) have been omitted. Add them if a budget table is introduced later.

---

## View Columns

| Column | Description |
|---|---|
| `gl_code` | GL account code |
| `gl_name` | GL account name |
| `pl_section` | P&L section (Income or COGS) |
| `report_month` | Month being analyzed (first of month) |
| `current_month_actual` | QB actual for this month |
| `prior_month_actual` | QB actual for prior month (LAG 1) |
| `mom_change` | Absolute MoM change (current - prior) |
| `mom_pct_change` | MoM % change, rounded to 2dp |
| `ytd_actual` | Cumulative YTD through this month (same calendar year) |
| `prior_ytd_actual` | Cumulative YTD through same month in prior year |
| `prior_year_month_actual` | Same GL, same month, one year ago |
| `yoy_change` | Absolute YoY change vs prior year same month |
| `yoy_pct_change` | YoY % change, rounded to 2dp |
| `avg_6mo` | Rolling 6-month average (current + 5 prior months) |
| `variance_flag` | NORMAL / WATCH / ALERT — see logic below |

---

## Variance Flag Logic

| Flag | Condition |
|---|---|
| `ALERT` | MoM change > 30% **or** current month deviates > 50% from 6-month rolling average |
| `WATCH` | MoM change > 15% (and not ALERT) |
| `NORMAL` | All other cases |

**Flag distribution across all 798 rows:**

| Flag | Count |
|---|---|
| ALERT | 295 |
| WATCH | 125 |
| NORMAL | 378 |

ALERT rate is relatively high (~37%) partly because the 6-month average deviation check catches seasonal swings. This is expected given the Q4 seasonality visible in core revenue lines.

---

## Sample Output (Oct 2025 – Feb 2026, selected GL codes)

| gl_code | gl_name | report_month | current_actual | prior_actual | mom_pct | yoy_pct | avg_6mo | flag |
|---|---|---|---|---|---|---|---|---|
| 41010 | Contract Processing Fee | 2025-10 | 181,484.78 | 216,253.53 | -16.08% | +4.25% | 191,778.28 | WATCH |
| 41010 | Contract Processing Fee | 2025-11 | 129,239.70 | 181,484.78 | -28.79% | +30.51% | 182,099.30 | WATCH |
| 41010 | Contract Processing Fee | 2025-12 | 132,479.38 | 129,239.70 | +2.51% | +62.14% | 179,028.60 | NORMAL |
| 41010 | Contract Processing Fee | 2026-01 | 173,434.56 | 132,479.38 | +30.91% | +5.66% | 176,389.88 | ALERT |
| 41010 | Contract Processing Fee | 2026-02 | 164,184.62 | 173,434.56 | -5.33% | -7.78% | 166,179.43 | NORMAL |
| 41020 | Government Fees | 2025-11 | 252,771.40 | 366,532.70 | -31.04% | +2.14% | 363,309.18 | ALERT |
| 41020 | Government Fees | 2026-01 | 302,984.00 | 250,209.00 | +21.09% | -1.07% | 333,681.68 | WATCH |

---

## SQL File

`/Users/jackelliott/commandcenter/projects/finance-wizard/sql/phase3/3_5_variance_analysis.sql`

---

## Usage Examples

```sql
-- Most recent month for all Income lines with flags
SELECT * FROM finance.v_variance_analysis
WHERE pl_section = 'Income'
  AND report_month = (SELECT MAX(report_month) FROM finance.v_variance_analysis)
ORDER BY gl_code;

-- All ALERT/WATCH items in 2026
SELECT gl_code, gl_name, report_month, mom_pct_change, variance_flag
FROM finance.v_variance_analysis
WHERE variance_flag IN ('ALERT', 'WATCH')
  AND report_month >= '2026-01-01'
ORDER BY variance_flag, ABS(mom_pct_change) DESC;

-- YoY comparison for a specific GL
SELECT report_month, current_month_actual, prior_year_month_actual, yoy_pct_change
FROM finance.v_variance_analysis
WHERE gl_code = '41010'
  AND report_month >= '2025-01-01'
ORDER BY report_month;
```
