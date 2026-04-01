-- =============================================================================
-- Phase 2.4: finance.v_shipping_cogs_reclass
-- =============================================================================
-- Purpose: Surface shipping COGS that need reclassification to account 53030
--          per Controller close tasks 3.15 and 3.25.
--
-- Data Sources:
--   - raw_quickbooks.pnl_monthly (gl_code = '43070')
--       Shipping revenue billed to customers (account 43070 - Shipping Revenue).
--       This is the invoice-side signal for how much shipping passed through.
--
--   - raw_quickbooks.report_cogs_transactions (account_name = '53030 - Shipping')
--       All transactions already posted to 53030 - Shipping COGS.
--       Pre-Aug 2024: driven by monthly JE reclass from 65020-Postage.
--       Aug 2024+:    driven by direct expense/bill postings (UPS/FedEx).
--
--   - raw_quickbooks.journal_entry_lines + journal_entries
--       The reclass JEs (description = 'To breakout COGS' / 'To breakout Solutions COGS')
--       that move shipping costs from 65020-Postage into 53030.
--
-- Reclass logic:
--   shipping_cogs_needed  = shipping_revenue (43070) — a pass-through proxy
--                           indicating what the Controller expects in 53030.
--   shipping_cogs_posted  = sum of all amounts in report_cogs_transactions
--                           for account 53030 - Shipping.
--   reclass_amount        = shipping_cogs_needed - shipping_cogs_posted
--                           Positive = shortfall (more needs to move to 53030).
--                           Negative = overcost (more in 53030 than revenue).
--
-- Notes:
--   - Months with data only in 53030 (no 43070 revenue) represent direct-expense
--     posting of carrier bills — no reclass needed, reclass_amount will be negative.
--   - The view is intentionally not filtered to current/open periods so the
--     Controller can review history and confirm the reclass pattern.
-- =============================================================================

CREATE OR REPLACE VIEW finance.v_shipping_cogs_reclass AS

WITH shipping_revenue AS (
    -- 43070 - Shipping Revenue: what customers were billed for shipping
    SELECT
        period_start                            AS report_month,
        COALESCE(SUM(amount), 0)               AS shipping_revenue
    FROM raw_quickbooks.pnl_monthly
    WHERE gl_code = '43070'
    GROUP BY period_start
),

shipping_cogs_posted AS (
    -- 53030 - Shipping COGS: everything already in the target account
    -- Includes JE reclass amounts, direct expenses, bills, credits, and deposits
    SELECT
        DATE_TRUNC('month', transaction_date)::date     AS report_month,
        COALESCE(SUM(amount), 0)                        AS shipping_cogs_posted
    FROM raw_quickbooks.report_cogs_transactions
    WHERE account_name = '53030 - Shipping'
    GROUP BY DATE_TRUNC('month', transaction_date)::date
),

je_reclass AS (
    -- JE reclass entries specifically targeting 53030 (historical close entries)
    -- These are the Controller's "To breakout COGS / Solutions COGS" journal entries
    SELECT
        DATE_TRUNC('month', je.txn_date)::date          AS report_month,
        SUM(
            CASE jel.posting_type
                WHEN 'Debit'  THEN  jel.amount
                WHEN 'Credit' THEN -jel.amount
                ELSE 0
            END
        )                                               AS je_reclass_amount
    FROM raw_quickbooks.journal_entry_lines jel
    JOIN raw_quickbooks.journal_entries je
        ON je.id = jel.journal_entry_id
    WHERE jel.account_name ILIKE '%53030%'
      AND jel.description ILIKE '%breakout%'
    GROUP BY DATE_TRUNC('month', je.txn_date)::date
)

SELECT
    COALESCE(r.report_month, c.report_month)            AS report_month,

    -- What customers paid for shipping (43070 revenue, pass-through signal)
    COALESCE(r.shipping_revenue, 0)                     AS shipping_revenue,

    -- What is already posted to 53030 (COGS, all transaction types)
    COALESCE(c.shipping_cogs_posted, 0)                 AS shipping_cogs_posted,

    -- The JE-specific reclass portion already applied to 53030
    COALESCE(j.je_reclass_amount, 0)                    AS je_reclass_applied,

    -- Needed COGS proxy: shipping revenue is a pass-through indicator.
    -- The Controller's expectation is that 53030 matches actual carrier costs,
    -- which historically equalled or tracked closely to invoiced shipping.
    COALESCE(r.shipping_revenue, 0)                     AS shipping_cogs_needed,

    -- Reclass gap: positive = shortfall still needing to move to 53030
    --              negative = overcost (53030 > revenue, direct expenses exceeded billing)
    ROUND(
        COALESCE(r.shipping_revenue, 0)
        - COALESCE(c.shipping_cogs_posted, 0),
        2
    )                                                   AS reclass_amount,

    -- Indicates whether a JE reclass has been applied this month
    CASE
        WHEN COALESCE(j.je_reclass_amount, 0) > 0 THEN TRUE
        ELSE FALSE
    END                                                 AS je_reclass_done,

    -- Coverage ratio: how much of revenue is covered by posted COGS
    CASE
        WHEN COALESCE(r.shipping_revenue, 0) = 0 THEN NULL
        ELSE ROUND(
            COALESCE(c.shipping_cogs_posted, 0)
            / COALESCE(r.shipping_revenue, 0),
            4
        )
    END                                                 AS cogs_coverage_ratio

FROM shipping_revenue r
FULL OUTER JOIN shipping_cogs_posted c
    ON r.report_month = c.report_month
LEFT JOIN je_reclass j
    ON COALESCE(r.report_month, c.report_month) = j.report_month

ORDER BY COALESCE(r.report_month, c.report_month);
