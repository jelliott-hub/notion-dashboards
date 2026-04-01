-- Phase 2.1: Create finance.v_pnl_reconciliation_coverage
-- Goal: Audit which QB P&L accounts the Hub covers vs what QB has in journal_entry_lines.
-- Date: 2026-04-01
--
-- STEP 1: Inspect gl_code format in v_pnl_reconciliation
-- Run this first to understand how gl_code is structured (e.g. "41010" vs "41010 - Name").
--
-- SELECT DISTINCT gl_code FROM finance.v_pnl_reconciliation ORDER BY 1 LIMIT 40;
--
-- Expected output: bare 5-digit account numbers like "41010", "41020", "51010" etc.
-- This matches the extraction logic in STEP 2 (SPLIT_PART on " - ").

-- =============================================================================
-- STEP 2: CREATE THE COVERAGE VIEW
-- =============================================================================

CREATE OR REPLACE VIEW finance.v_pnl_reconciliation_coverage AS
WITH

-- Hub covered accounts: distinct gl_codes from the P&L reconciliation view.
-- One row per gl_code; also pull the source_view for context.
hub_accounts AS (
    SELECT
        gl_code,
        MIN(source_view) AS hub_source_view   -- take any representative source_view
    FROM finance.v_pnl_reconciliation
    GROUP BY gl_code
),

-- QB accounts from journal_entry_lines since 2025-01-01.
-- account_name is hierarchical, e.g. "SaaS Platform:Fingerprinting Services:41010 - Contract Processing Fee"
-- We extract the account number as the FIRST token before " - " in the last path segment.
qb_raw AS (
    SELECT
        -- Get the last segment of the colon-delimited hierarchy (the leaf account)
        SPLIT_PART(jel.account_name, ':', -1)                          AS leaf_account_name,
        -- Extract the numeric code: everything before the first " - " in the leaf segment.
        -- If there is no " - ", fall back to the full leaf segment.
        CASE
            WHEN SPLIT_PART(jel.account_name, ':', -1) LIKE '% - %'
                THEN TRIM(SPLIT_PART(SPLIT_PART(jel.account_name, ':', -1), ' - ', 1))
            ELSE TRIM(SPLIT_PART(jel.account_name, ':', -1))
        END                                                             AS account_number,
        jel.account_name                                               AS full_account_name,
        -- Total QB activity = sum of absolute amounts (debits + credits treated as gross flow)
        ABS(jel.amount)                                                AS abs_amount,
        -- Retain posting_type for P&L vs balance sheet classification
        jel.posting_type,
        je.txn_date
    FROM raw_quickbooks.journal_entry_lines jel
    JOIN raw_quickbooks.journal_entries je ON je.id = jel.journal_entry_id
    WHERE je.txn_date >= '2025-01-01'
),

-- Aggregate to one row per (account_number, leaf_account_name) pair.
-- Determine P&L vs balance-sheet by account number prefix.
qb_accounts AS (
    SELECT
        account_number,
        -- Use the most common leaf_account_name for that number
        MODE() WITHIN GROUP (ORDER BY leaf_account_name)    AS account_name,
        -- Keep one representative full hierarchical name
        MODE() WITHIN GROUP (ORDER BY full_account_name)    AS full_account_name,
        SUM(abs_amount)                                     AS total_qb_activity,
        COUNT(*)                                            AS line_count,
        -- P&L accounts: income / expense ranges (4xxxx-6xxxx-8xxxx typical for QBO)
        -- Balance sheet: 1xxxx (assets), 2xxxx (liabilities), 3xxxx (equity)
        CASE
            WHEN account_number ~ '^[4-9][0-9]{4}$' THEN true
            ELSE false
        END                                                 AS is_pl_account
    FROM qb_raw
    -- Only include rows where we successfully extracted a 5-digit account number
    WHERE account_number ~ '^[0-9]{5}$'
    GROUP BY account_number
)

SELECT
    qa.account_number,
    qa.account_name,
    qa.full_account_name,
    qa.is_pl_account,
    -- Coverage flag: does the Hub's v_pnl_reconciliation reference this account?
    (ha.gl_code IS NOT NULL)                               AS in_hub,
    ha.hub_source_view,
    qa.total_qb_activity,
    qa.line_count,
    -- Expected coverage classification
    CASE
        WHEN qa.account_number BETWEEN '41010' AND '44050' THEN 'Revenue — should be covered'
        WHEN qa.account_number BETWEEN '51010' AND '54010' THEN 'COGS — should be covered'
        WHEN qa.account_number BETWEEN '60000' AND '68999' THEN 'OpEx — not expected'
        WHEN qa.account_number BETWEEN '80000' AND '99999' THEN 'Other/Below line — not expected'
        WHEN qa.account_number < '40000'                   THEN 'Balance sheet — not expected'
        ELSE 'Other P&L — review'
    END                                                    AS coverage_expectation
FROM qb_accounts qa
LEFT JOIN hub_accounts ha ON ha.gl_code = qa.account_number
ORDER BY qa.account_number;


-- =============================================================================
-- STEP 3: VALIDATE THE VIEW
-- =============================================================================

-- Summary by in_hub flag: count and total QB activity
SELECT
    in_hub,
    coverage_expectation,
    COUNT(*)                    AS account_count,
    SUM(total_qb_activity)      AS total_qb_activity
FROM finance.v_pnl_reconciliation_coverage
GROUP BY 1, 2
ORDER BY 2, 1;

-- Spot-check: Revenue/COGS accounts NOT in hub (gaps that should not exist)
SELECT
    account_number,
    account_name,
    in_hub,
    hub_source_view,
    total_qb_activity,
    coverage_expectation
FROM finance.v_pnl_reconciliation_coverage
WHERE coverage_expectation IN ('Revenue — should be covered', 'COGS — should be covered')
  AND in_hub = false
ORDER BY account_number;

-- Full P&L coverage matrix (P&L accounts only)
SELECT
    account_number,
    account_name,
    in_hub,
    hub_source_view,
    total_qb_activity,
    line_count,
    coverage_expectation
FROM finance.v_pnl_reconciliation_coverage
WHERE is_pl_account = true
ORDER BY account_number;
