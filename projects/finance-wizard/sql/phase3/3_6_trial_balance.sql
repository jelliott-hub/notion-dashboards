-- Phase 3.6: Create finance.v_trial_balance
-- Purpose: Derived trial balance from Hub data. Aggregates all revenue (41xxx-44xxx) and
--          COGS (51xxx-54xxx) accounts with debit/credit balances by period.
--          Supports close checklist task 3.33.
--
-- Data sources:
--   PRIMARY:  finance.v_pnl_reconciliation   — Hub vs QB totals by gl_code and period
--   SECONDARY: raw_quickbooks.journal_entry_lines + journal_entries — QB debit/credit breakdown
--
-- Accounting convention (QB/GAAP P&L):
--   Revenue accounts (41xxx-44xxx): normal credit balance → credit_total >= debit_total
--   COGS accounts    (51xxx-54xxx): normal debit  balance → debit_total  >= credit_total
--   net_balance = credit_total - debit_total (positive = normal credit balance = net income contribution)
--
-- Notes:
--   - hub_total and qb_total in v_pnl_reconciliation already carry correct sign
--     (credits are positive for Revenue, positive for COGS matching QB convention)
--   - debit/credit columns sourced from QB JE lines for periods with QB data (2025-01+);
--     for pre-2025 periods only hub/qb net amounts are available (debit/credit NULL)
--   - Summary rows are added per pl_section and a Grand Total row using GROUPING SETS
-- =============================================================================

CREATE OR REPLACE VIEW finance.v_trial_balance AS

-- ---------------------------------------------------------------------------
-- CTE 1: QB journal entry lines — extract account number, debit/credit totals
-- by calendar month for Revenue and COGS accounts only.
-- Only covers 2025-01-01+ (when QB JE data is reliable).
-- ---------------------------------------------------------------------------
WITH qb_je AS (
    SELECT
        DATE_TRUNC('month', je.txn_date)::date                         AS report_month,
        -- Extract leaf account number (5-digit) from hierarchical account_name
        CASE
            WHEN SPLIT_PART(jel.account_name, ':', -1) LIKE '% - %'
                THEN TRIM(SPLIT_PART(SPLIT_PART(jel.account_name, ':', -1), ' - ', 1))
            ELSE TRIM(SPLIT_PART(jel.account_name, ':', -1))
        END                                                             AS gl_code,
        SUM(CASE WHEN jel.posting_type = 'Debit'  THEN jel.amount ELSE 0 END)  AS debit_total,
        SUM(CASE WHEN jel.posting_type = 'Credit' THEN jel.amount ELSE 0 END)  AS credit_total
    FROM raw_quickbooks.journal_entry_lines  jel
    JOIN raw_quickbooks.journal_entries      je  ON je.id = jel.journal_entry_id
    WHERE je.txn_date >= '2025-01-01'
    GROUP BY 1, 2
),

-- Filter to valid 5-digit Revenue/COGS account numbers
qb_je_filtered AS (
    SELECT
        report_month,
        gl_code,
        ROUND(debit_total::numeric,  2) AS debit_total,
        ROUND(credit_total::numeric, 2) AS credit_total
    FROM qb_je
    WHERE gl_code ~ '^[4-5][0-9]{4}$'
),

-- ---------------------------------------------------------------------------
-- CTE 2: Hub totals from v_pnl_reconciliation — one row per (period, gl_code)
-- ---------------------------------------------------------------------------
hub AS (
    SELECT
        period_start                                AS report_month,
        gl_code,
        gl_name,
        pl_section,
        source_view,
        ROUND(hub_total::numeric, 2)                AS hub_derived_amount,
        ROUND(qb_total::numeric,  2)                AS qb_actual_amount,
        ROUND((hub_total - qb_total)::numeric, 2)   AS variance,
        status                                      AS recon_status
    FROM finance.v_pnl_reconciliation
),

-- ---------------------------------------------------------------------------
-- CTE 3: Combine Hub and QB JE data — detail rows
-- ---------------------------------------------------------------------------
detail AS (
    SELECT
        h.report_month,
        h.gl_code,
        h.gl_name,
        h.pl_section,
        h.source_view,

        -- Debit/credit from QB JE lines (NULL when no JE data, i.e. pre-2025)
        COALESCE(q.debit_total,  0)                 AS debit_total,
        COALESCE(q.credit_total, 0)                 AS credit_total,

        -- net_balance: credit minus debit (positive = net income contribution)
        -- For Revenue: normally positive (credits > debits)
        -- For COGS:    normally negative (debits > credits)
        ROUND((COALESCE(q.credit_total, 0) - COALESCE(q.debit_total, 0))::numeric, 2)
                                                    AS net_balance,

        h.hub_derived_amount,
        h.qb_actual_amount,
        h.variance,
        h.recon_status,

        -- Row sort key: detail row = 0 (used to sort detail before summary rows)
        0                                           AS row_type,

        -- Ordering within pl_section
        h.gl_code                                   AS sort_key
    FROM hub h
    LEFT JOIN qb_je_filtered q
        ON  q.report_month = h.report_month
        AND q.gl_code      = h.gl_code
),

-- ---------------------------------------------------------------------------
-- CTE 4: Section subtotals and grand total via GROUPING SETS
-- ---------------------------------------------------------------------------
subtotals AS (
    SELECT
        report_month,
        CASE
            WHEN GROUPING(pl_section) = 0 AND pl_section IS NOT NULL
                THEN '>>> ' || pl_section || ' TOTAL'
            ELSE '>>> GRAND TOTAL'
        END                                             AS gl_code,
        CASE
            WHEN GROUPING(pl_section) = 0 AND pl_section IS NOT NULL
                THEN 'Total ' || pl_section
            ELSE 'Total Revenue & COGS'
        END                                             AS gl_name,
        COALESCE(pl_section, 'GRAND')                   AS pl_section,
        NULL::text                                      AS source_view,
        ROUND(SUM(debit_total)::numeric,        2)      AS debit_total,
        ROUND(SUM(credit_total)::numeric,       2)      AS credit_total,
        ROUND(SUM(net_balance)::numeric,        2)      AS net_balance,
        ROUND(SUM(hub_derived_amount)::numeric, 2)      AS hub_derived_amount,
        ROUND(SUM(qb_actual_amount)::numeric,   2)      AS qb_actual_amount,
        ROUND(SUM(variance)::numeric,           2)      AS variance,
        NULL::text                                      AS recon_status,
        -- row_type: 1 = section subtotal, 2 = grand total
        CASE WHEN GROUPING(pl_section) = 0 THEN 1 ELSE 2 END AS row_type,
        CASE WHEN GROUPING(pl_section) = 0 THEN pl_section ELSE 'ZZZ' END AS sort_key
    FROM detail
    GROUP BY GROUPING SETS (
        (report_month, pl_section),   -- section subtotals (Income, COGS)
        (report_month)                -- grand total
    )
),

-- UNION into single result set so sort_key is available for ORDER BY
combined AS (
    SELECT report_month, gl_code, gl_name, pl_section, source_view,
           debit_total, credit_total, net_balance,
           hub_derived_amount, qb_actual_amount, variance, recon_status,
           row_type, sort_key
    FROM detail

    UNION ALL

    SELECT report_month, gl_code, gl_name, pl_section, source_view,
           debit_total, credit_total, net_balance,
           hub_derived_amount, qb_actual_amount, variance, recon_status,
           row_type, sort_key
    FROM subtotals
)

-- ---------------------------------------------------------------------------
-- FINAL: Output all columns except internal sort_key
-- ---------------------------------------------------------------------------
SELECT
    report_month,
    gl_code,
    gl_name,
    pl_section,
    source_view,
    debit_total,
    credit_total,
    net_balance,
    hub_derived_amount,
    qb_actual_amount,
    variance,
    recon_status,
    row_type
FROM combined
ORDER BY
    report_month,
    -- Income before COGS, GRAND last
    CASE pl_section
        WHEN 'Income' THEN 1
        WHEN 'COGS'   THEN 2
        ELSE               3
    END,
    row_type,      -- detail (0) before subtotal (1) before grand total (2)
    sort_key;


-- =============================================================================
-- VALIDATION: Run for Jan 2026 and Feb 2026
-- =============================================================================

-- 1. Full trial balance for Jan 2026
SELECT
    report_month,
    gl_code,
    gl_name,
    pl_section,
    debit_total,
    credit_total,
    net_balance,
    hub_derived_amount,
    qb_actual_amount,
    variance,
    recon_status,
    row_type
FROM finance.v_trial_balance
WHERE report_month = '2026-01-01'
ORDER BY
    CASE pl_section WHEN 'Income' THEN 1 WHEN 'COGS' THEN 2 ELSE 3 END,
    row_type,
    gl_code;


-- 2. Full trial balance for Feb 2026
SELECT
    report_month,
    gl_code,
    gl_name,
    pl_section,
    debit_total,
    credit_total,
    net_balance,
    hub_derived_amount,
    qb_actual_amount,
    variance,
    recon_status,
    row_type
FROM finance.v_trial_balance
WHERE report_month = '2026-02-01'
ORDER BY
    CASE pl_section WHEN 'Income' THEN 1 WHEN 'COGS' THEN 2 ELSE 3 END,
    row_type,
    gl_code;


-- 3. Summary check: section totals for both months
SELECT
    report_month,
    gl_code,
    gl_name,
    debit_total,
    credit_total,
    net_balance,
    hub_derived_amount,
    qb_actual_amount,
    variance
FROM finance.v_trial_balance
WHERE report_month IN ('2026-01-01', '2026-02-01')
  AND row_type IN (1, 2)
ORDER BY report_month,
    CASE pl_section WHEN 'Income' THEN 1 WHEN 'COGS' THEN 2 ELSE 3 END,
    row_type;


-- 4. Variance check: accounts where hub_derived_amount != qb_actual_amount
SELECT
    report_month,
    gl_code,
    gl_name,
    pl_section,
    hub_derived_amount,
    qb_actual_amount,
    variance,
    recon_status
FROM finance.v_trial_balance
WHERE report_month IN ('2026-01-01', '2026-02-01')
  AND row_type = 0
  AND ABS(variance) > 0
ORDER BY report_month, ABS(variance) DESC;
