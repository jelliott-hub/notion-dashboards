-- Phase 2.5: finance.v_catchall_monitor
-- Monthly trend monitor for finance.v_je_catchall_txn
-- Purpose: Surface months where uncaptured JE lines are growing or exceed thresholds,
--          indicating the ETL is missing items that need new dedicated views.
--
-- Status tiers:
--   OK    : |uncaptured_total| < $1,000
--   WARN  : |uncaptured_total| $1,000–$4,999.99
--   ALERT : |uncaptured_total| >= $5,000
--
-- mom_change: month-over-month delta in absolute uncaptured amount
--             positive = more uncaptured this month vs prior month (getting worse)
--             negative = less uncaptured (getting better)

CREATE OR REPLACE VIEW finance.v_catchall_monitor AS
WITH monthly AS (
    SELECT
        report_month,
        COUNT(*)                                                   AS uncaptured_line_count,
        ABS(SUM(amount))                                          AS uncaptured_total,
        COALESCE(SUM(CASE WHEN amount > 0 THEN amount  ELSE 0 END), 0) AS uncaptured_debit_total,
        COALESCE(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 0) AS uncaptured_credit_total,
        array_agg(DISTINCT gl_account ORDER BY gl_account)        AS distinct_accounts
    FROM finance.v_je_catchall_txn
    GROUP BY report_month
),
with_status AS (
    SELECT
        report_month,
        uncaptured_line_count,
        uncaptured_total,
        uncaptured_debit_total,
        uncaptured_credit_total,
        distinct_accounts,
        CASE
            WHEN uncaptured_total >= 5000 THEN 'ALERT'
            WHEN uncaptured_total >= 1000 THEN 'WARN'
            ELSE 'OK'
        END AS status,
        -- Month-over-month change: positive = more uncaptured (worse), negative = less (better)
        uncaptured_total
            - LAG(uncaptured_total) OVER (ORDER BY report_month) AS mom_change
    FROM monthly
)
SELECT
    report_month,
    uncaptured_line_count,
    ROUND(uncaptured_total,        2) AS uncaptured_total,
    ROUND(uncaptured_debit_total,  2) AS uncaptured_debit_total,
    ROUND(uncaptured_credit_total, 2) AS uncaptured_credit_total,
    distinct_accounts,
    status,
    ROUND(mom_change, 2)              AS mom_change
FROM with_status
ORDER BY report_month;
