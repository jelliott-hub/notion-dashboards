-- =============================================================================
-- Phase 3.3: finance.v_close_dashboard
-- Real-time view of month-end close progress.
--
-- Dependencies (must exist before creating this view):
--   finance.v_pnl_reconciliation     -- Hub vs QB P&L account-level recon
--   finance.v_close_readiness        -- Aggregated close status per month
--   finance.v_ar_oi_reconciliation   -- AR open-invoice reconciliation
--   finance.v_catchall_monitor       -- Uncaptured / catch-all account monitor
--   finance.v_clearing_account_balance -- Clearing account open balances
--
-- NOTE: finance.close_checklist does not exist as of view creation.
--       checklist_pct_complete is set to NULL with a placeholder CASE expression
--       that will activate automatically once the table is created and this view
--       is refreshed. See TODO below.
-- =============================================================================

CREATE OR REPLACE VIEW finance.v_close_dashboard AS

WITH

-- ── P&L account-level aggregation ──────────────────────────────────────────
pnl_agg AS (
    SELECT
        period_start                                                AS report_month,

        -- Revenue: Income section, prefer QB (authoritative) fallback Hub
        SUM(CASE WHEN pl_section = 'Income'
                 THEN COALESCE(NULLIF(qb_total, 0), hub_total)
                 ELSE 0 END)                                        AS total_revenue,

        -- COGS: COGS section
        SUM(CASE WHEN pl_section = 'COGS'
                 THEN COALESCE(NULLIF(qb_total, 0), hub_total)
                 ELSE 0 END)                                        AS total_cogs,

        -- Account-level pass/fail counts
        COUNT(*)                                                    AS pnl_accounts_total,
        COUNT(*) FILTER (WHERE status = 'PASS')                     AS pnl_accounts_passing,
        COUNT(*) FILTER (WHERE status IN ('FAIL', 'WARN'))          AS pnl_accounts_failing
    FROM finance.v_pnl_reconciliation
    GROUP BY period_start
),

-- ── Close readiness rollup (cash, AR, catchall, deferred, overall) ─────────
readiness AS (
    SELECT
        report_month,
        cash_recon_status,
        ar_recon_status,
        catchall_status,
        deferred_rev_balance,
        deferred_status,
        overall_status,
        blocking_items
    FROM finance.v_close_readiness
),

-- ── AR open-invoice reconciliation ─────────────────────────────────────────
ar AS (
    SELECT
        report_month,
        recon_status   AS ar_recon_status_raw,
        qb_ar_total,
        tc_oi_ar,
        delta          AS ar_delta
    FROM finance.v_ar_oi_reconciliation
),

-- ── Catch-all / uncaptured transaction monitor ─────────────────────────────
catchall AS (
    SELECT
        report_month,
        uncaptured_line_count,
        uncaptured_total,
        status         AS catchall_status_raw
    FROM finance.v_catchall_monitor
),

-- ── Clearing account open balances (BS_CLEARING rows only) ─────────────────
clearing AS (
    SELECT
        report_month,
        COUNT(*) FILTER (WHERE account_type = 'BS_CLEARING'
                           AND ending_balance <> 0)                 AS clearing_open_count,
        SUM(CASE WHEN account_type = 'BS_CLEARING'
                 THEN ABS(ending_balance) ELSE 0 END)               AS clearing_open_abs_total,
        CASE
            WHEN COUNT(*) FILTER (WHERE account_type = 'BS_CLEARING'
                                    AND ending_balance <> 0) = 0    THEN 'PASS'
            WHEN SUM(CASE WHEN account_type = 'BS_CLEARING'
                         THEN ABS(ending_balance) ELSE 0 END) > 0   THEN 'WARN'
            ELSE 'PASS'
        END                                                         AS clearing_status
    FROM finance.v_clearing_account_balance
    GROUP BY report_month
),

-- ── Universe of known months (union across all sources) ────────────────────
all_months AS (
    SELECT report_month FROM pnl_agg
    UNION
    SELECT report_month FROM readiness
    UNION
    SELECT report_month FROM ar
    UNION
    SELECT report_month FROM catchall
    UNION
    SELECT report_month FROM clearing
)

-- ── Final assembly ──────────────────────────────────────────────────────────
SELECT
    am.report_month,

    -- ── P&L metrics ────────────────────────────────────────────────────────
    COALESCE(p.total_revenue, 0)                                    AS total_revenue,
    COALESCE(p.total_cogs,    0)                                    AS total_cogs,
    COALESCE(p.total_revenue, 0) - COALESCE(p.total_cogs, 0)       AS gross_margin,
    CASE
        WHEN COALESCE(p.total_revenue, 0) = 0 THEN NULL
        ELSE ROUND(
            (COALESCE(p.total_revenue, 0) - COALESCE(p.total_cogs, 0))
            / p.total_revenue * 100,
            1
        )
    END                                                             AS gross_margin_pct,

    -- ── P&L recon counts ───────────────────────────────────────────────────
    COALESCE(p.pnl_accounts_passing,  0)                            AS pnl_accounts_passing,
    COALESCE(p.pnl_accounts_failing,  0)                            AS pnl_accounts_failing,
    COALESCE(p.pnl_accounts_total,    0)                            AS pnl_accounts_total,

    -- ── Cash reconciliation status (from v_close_readiness rollup) ─────────
    COALESCE(r.cash_recon_status, 'NO_DATA')                        AS cash_recon_status,

    -- ── Clearing account (balance-sheet clearing rows) ─────────────────────
    COALESCE(cl.clearing_open_count, 0)                             AS clearing_open_count,
    COALESCE(cl.clearing_open_abs_total, 0)                         AS clearing_open_abs_total,
    COALESCE(cl.clearing_status, 'NO_DATA')                         AS clearing_status,

    -- ── AR open-invoice reconciliation ─────────────────────────────────────
    COALESCE(r.ar_recon_status, 'NO_DATA')                          AS ar_recon_status,
    ar.ar_recon_status_raw,
    ar.qb_ar_total,
    ar.tc_oi_ar,
    ar.ar_delta,

    -- ── Catch-all monitor ──────────────────────────────────────────────────
    COALESCE(r.catchall_status, 'NO_DATA')                          AS catchall_status,
    ca.catchall_status_raw,
    COALESCE(ca.uncaptured_line_count, 0)                           AS catchall_uncaptured_lines,
    COALESCE(ca.uncaptured_total,      0)                           AS catchall_uncaptured_total,

    -- ── Deferred revenue ───────────────────────────────────────────────────
    COALESCE(r.deferred_rev_balance, 0)                             AS deferred_rev_balance,
    COALESCE(r.deferred_status, 'NO_DATA')                          AS deferred_status,

    -- ── Checklist completion ────────────────────────────────────────────────
    -- TODO: Activate once finance.close_checklist is deployed (Phase 3.2).
    -- Replace the NULL below with:
    --   (SELECT ROUND(
    --       COUNT(*) FILTER (WHERE completed_at IS NOT NULL)::numeric
    --       / NULLIF(COUNT(*), 0) * 100, 1
    --    FROM finance.close_checklist
    --    WHERE report_month = am.report_month)
    NULL::numeric                                                   AS checklist_pct_complete,

    -- ── Blocking items array (from v_close_readiness) ──────────────────────
    r.blocking_items,

    -- ── Overall health signal ───────────────────────────────────────────────
    -- GREEN  = all proofs pass, no failures, no NO_DATA on mandatory signals
    -- YELLOW = warnings present or optional signals missing
    -- RED    = any hard failure or mandatory signal has NO_DATA
    CASE
        WHEN 'FAIL' = ANY(ARRAY[
            COALESCE(r.cash_recon_status,  'NO_DATA'),
            COALESCE(r.ar_recon_status,    'NO_DATA'),
            COALESCE(r.catchall_status,    'NO_DATA'),
            COALESCE(r.deferred_status,    'NO_DATA')
        ])
        OR  COALESCE(p.pnl_accounts_failing, 0) > 0
            THEN 'RED'

        WHEN 'NO_DATA' = ANY(ARRAY[
            COALESCE(r.cash_recon_status,  'NO_DATA'),
            COALESCE(r.ar_recon_status,    'NO_DATA'),
            COALESCE(r.catchall_status,    'NO_DATA')
        ])
        OR  COALESCE(cl.clearing_status, 'NO_DATA') IN ('WARN', 'NO_DATA')
        OR  COALESCE(r.deferred_status,  'NO_DATA') = 'WARN'
            THEN 'YELLOW'

        ELSE 'GREEN'
    END                                                             AS overall_health

FROM all_months       am
LEFT JOIN pnl_agg     p   ON p.report_month  = am.report_month
LEFT JOIN readiness   r   ON r.report_month  = am.report_month
LEFT JOIN ar          ar  ON ar.report_month = am.report_month
LEFT JOIN catchall    ca  ON ca.report_month = am.report_month
LEFT JOIN clearing    cl  ON cl.report_month = am.report_month

ORDER BY am.report_month DESC;

-- Grant read access to standard roles
GRANT SELECT ON finance.v_close_dashboard TO anon, authenticated, service_role;
