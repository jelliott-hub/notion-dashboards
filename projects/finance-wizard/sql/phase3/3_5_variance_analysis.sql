-- =============================================================================
-- Phase 3.5: finance.v_variance_analysis
-- Month-over-month and YoY variance analysis for all P&L line items
-- Supports close checklist task 3.34
-- No budget tables found in finance or analytics schemas; budget columns omitted
-- =============================================================================

CREATE OR REPLACE VIEW finance.v_variance_analysis AS

WITH

-- Base: pull actuals from the P&L reconciliation view.
-- Filter to periods that have non-zero data (future stub rows are all-zero).
base AS (
    SELECT
        gl_code,
        gl_name,
        pl_section,
        period_start                        AS report_month,
        COALESCE(qb_total, 0)               AS actual
    FROM finance.v_pnl_reconciliation
    WHERE qb_total IS NOT NULL
      AND qb_total <> 0
),

-- Rolling calculations: lag, lead, YTD, 6-month avg, prior-year YTD
windowed AS (
    SELECT
        gl_code,
        gl_name,
        pl_section,
        report_month,
        actual                              AS current_month_actual,

        -- Prior month actual (MoM)
        LAG(actual) OVER (
            PARTITION BY gl_code
            ORDER BY report_month
        )                                   AS prior_month_actual,

        -- YTD: sum from Jan 1 of the same year through current month
        SUM(actual) OVER (
            PARTITION BY gl_code, DATE_TRUNC('year', report_month)
            ORDER BY report_month
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        )                                   AS ytd_actual,

        -- Rolling 6-month average (current month + 5 prior)
        AVG(actual) OVER (
            PARTITION BY gl_code
            ORDER BY report_month
            ROWS BETWEEN 5 PRECEDING AND CURRENT ROW
        )                                   AS avg_6mo
    FROM base
),

-- Prior-year YTD: join back to get same GL, same month of prior year, sum YTD
prior_year_ytd AS (
    SELECT
        gl_code,
        report_month,
        SUM(actual) OVER (
            PARTITION BY gl_code, DATE_TRUNC('year', report_month)
            ORDER BY report_month
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        )                                   AS ytd_actual,
        -- Shift forward one year so we can join to current year
        (report_month + INTERVAL '1 year')::date AS shifted_month
    FROM base
),

-- YoY actual: prior year same month
prior_year_month AS (
    SELECT
        gl_code,
        (report_month + INTERVAL '1 year')::date AS shifted_month,
        actual                                    AS prior_year_actual
    FROM base
),

combined AS (
    SELECT
        w.gl_code,
        w.gl_name,
        w.pl_section,
        w.report_month,
        w.current_month_actual,
        w.prior_month_actual,

        -- MoM absolute change
        (w.current_month_actual - w.prior_month_actual)
                                            AS mom_change,

        -- MoM % change (avoid divide-by-zero)
        CASE
            WHEN w.prior_month_actual IS NULL OR w.prior_month_actual = 0 THEN NULL
            ELSE ROUND(
                ((w.current_month_actual - w.prior_month_actual)
                 / ABS(w.prior_month_actual) * 100)::numeric, 2
            )
        END                                 AS mom_pct_change,

        w.ytd_actual,

        -- Prior-year YTD (matched by gl_code + month shifted 1 year)
        py_ytd.ytd_actual                   AS prior_ytd_actual,

        -- YoY change (current month vs same month prior year)
        pym.prior_year_actual               AS prior_year_month_actual,

        CASE
            WHEN pym.prior_year_actual IS NULL THEN NULL
            ELSE (w.current_month_actual - pym.prior_year_actual)
        END                                 AS yoy_change,

        CASE
            WHEN pym.prior_year_actual IS NULL OR pym.prior_year_actual = 0 THEN NULL
            ELSE ROUND(
                ((w.current_month_actual - pym.prior_year_actual)
                 / ABS(pym.prior_year_actual) * 100)::numeric, 2
            )
        END                                 AS yoy_pct_change,

        ROUND(w.avg_6mo::numeric, 2)        AS avg_6mo,

        -- Variance flag logic
        CASE
            -- ALERT: MoM > 30%, OR current month deviates > 50% from 6mo avg
            WHEN ABS(
                    (w.current_month_actual - w.prior_month_actual)
                    / NULLIF(ABS(w.prior_month_actual), 0)
                 ) > 0.30
              OR (
                    w.avg_6mo <> 0
                    AND ABS(
                        (w.current_month_actual - w.avg_6mo)
                        / ABS(w.avg_6mo)
                    ) > 0.50
                 )
            THEN 'ALERT'

            -- WATCH: MoM > 15%
            WHEN ABS(
                    (w.current_month_actual - w.prior_month_actual)
                    / NULLIF(ABS(w.prior_month_actual), 0)
                 ) > 0.15
            THEN 'WATCH'

            ELSE 'NORMAL'
        END                                 AS variance_flag

    FROM windowed w
    LEFT JOIN prior_year_ytd py_ytd
           ON py_ytd.gl_code       = w.gl_code
          AND py_ytd.shifted_month = w.report_month
    LEFT JOIN prior_year_month pym
           ON pym.gl_code          = w.gl_code
          AND pym.shifted_month    = w.report_month
)

SELECT
    gl_code,
    gl_name,
    pl_section,
    report_month,
    ROUND(current_month_actual::numeric, 2)  AS current_month_actual,
    ROUND(prior_month_actual::numeric, 2)    AS prior_month_actual,
    ROUND(mom_change::numeric, 2)            AS mom_change,
    mom_pct_change,
    ROUND(ytd_actual::numeric, 2)            AS ytd_actual,
    ROUND(prior_ytd_actual::numeric, 2)      AS prior_ytd_actual,
    ROUND(prior_year_month_actual::numeric, 2) AS prior_year_month_actual,
    ROUND(yoy_change::numeric, 2)            AS yoy_change,
    yoy_pct_change,
    avg_6mo,
    variance_flag
FROM combined
ORDER BY pl_section, gl_code, report_month;
