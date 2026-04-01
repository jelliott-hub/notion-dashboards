-- =============================================================================
-- Phase 2.3: finance.v_close_readiness
-- Composite view checking all preconditions for month-end close.
--
-- Checks performed (per month):
--   1. P&L reconciliation   — v_pnl_reconciliation (FAIL → blocking)
--   2. Cash reconciliation  — v_ach_reconciliation_monthly,
--                             v_paypal_reconciliation_monthly,
--                             v_swipesum_reconciliation_monthly
--   3. AR reconciliation    — v_ar_oi_reconciliation
--   4. Catchall monitor     — v_catchall_monitor (ALERT → blocking)
--   5. Deferred revenue     — v_deferred_maint_balance (balance must be >= 0)
--
-- Missing views (not yet deployed):
--   • v_clearing_account_balance  — omitted; add when available
--   • v_pnl_reconciliation_coverage — omitted; informational only
--
-- overall_status = 'READY' only when ALL checks pass.
-- =============================================================================

CREATE OR REPLACE VIEW finance.v_close_readiness AS

WITH

-- ── 1. P&L RECONCILIATION ────────────────────────────────────────────────────
-- Pivot per period_start → count FAILs / WARNs
pnl_agg AS (
    SELECT
        period_start                                                  AS report_month,
        COUNT(*)                                                      AS pnl_total_accounts,
        COUNT(*) FILTER (WHERE status = 'FAIL')                       AS pnl_fail_count,
        COUNT(*) FILTER (WHERE status = 'WARN')                       AS pnl_warn_count,
        CASE
            WHEN COUNT(*) FILTER (WHERE status = 'FAIL') > 0 THEN 'FAIL'
            WHEN COUNT(*) FILTER (WHERE status = 'WARN') > 0 THEN 'WARN'
            ELSE 'PASS'
        END                                                           AS pnl_status
    FROM finance.v_pnl_reconciliation
    GROUP BY period_start
),

-- ── 2. CASH RECONCILIATION ───────────────────────────────────────────────────
-- ACH: derive status from deposit_variance threshold (allow up to $1 rounding)
ach_status AS (
    SELECT
        month                                                         AS report_month,
        deposit_variance,
        ABS(COALESCE(deposit_variance, 0))                            AS ach_abs_variance,
        CASE
            WHEN total_qb_deposits IS NULL                            THEN 'NO_DATA'
            WHEN ABS(COALESCE(deposit_variance, 0)) <= 1.00           THEN 'PASS'
            WHEN ABS(COALESCE(deposit_variance, 0)) <= 500.00         THEN 'WARN'
            ELSE 'FAIL'
        END                                                           AS ach_status
    FROM finance.v_ach_reconciliation_monthly
),

-- PayPal: has its own status column
paypal_status AS (
    SELECT
        month                                                         AS report_month,
        residual_variance                                             AS paypal_variance,
        COALESCE(status, 'NO_DATA')                                   AS paypal_status_raw,
        -- Normalize to PASS/WARN/FAIL for aggregation
        CASE
            WHEN status IN ('TIMING', 'NO_EMAIL_DATA')                THEN 'WARN'
            WHEN status = 'INVESTIGATE'                               THEN 'FAIL'
            ELSE 'PASS'
        END                                                           AS paypal_status
    FROM finance.v_paypal_reconciliation_monthly
),

-- SwipeSum: derive status from variance (no native status column)
swipesum_status AS (
    SELECT
        month                                                         AS report_month,
        variance                                                      AS swipesum_variance,
        CASE
            WHEN qb_total IS NULL                                     THEN 'NO_DATA'
            WHEN ABS(COALESCE(variance, 0)) <= 1.00                   THEN 'PASS'
            WHEN ABS(COALESCE(variance, 0)) <= 1000.00                THEN 'WARN'
            ELSE 'FAIL'
        END                                                           AS swipesum_status
    FROM finance.v_swipesum_reconciliation_monthly
),

-- Aggregate cash into a single status per month
-- We FULL OUTER JOIN across the three sources so months with partial coverage
-- still appear. The anchor month list is the union of all three.
cash_months AS (
    SELECT report_month FROM ach_status
    UNION
    SELECT report_month FROM paypal_status
    UNION
    SELECT report_month FROM swipesum_status
),
cash_agg AS (
    SELECT
        cm.report_month,
        COALESCE(a.ach_status,      'NO_DATA')                        AS ach_status,
        COALESCE(p.paypal_status,   'NO_DATA')                        AS paypal_status,
        COALESCE(s.swipesum_status, 'NO_DATA')                        AS swipesum_status,
        a.ach_abs_variance,
        p.paypal_variance,
        s.swipesum_variance,
        -- Overall cash status: worst-case across all three processors
        CASE
            WHEN 'FAIL' IN (
                COALESCE(a.ach_status,      'NO_DATA'),
                COALESCE(p.paypal_status,   'NO_DATA'),
                COALESCE(s.swipesum_status, 'NO_DATA')
            )                                                         THEN 'FAIL'
            WHEN 'WARN' IN (
                COALESCE(a.ach_status,      'NO_DATA'),
                COALESCE(p.paypal_status,   'NO_DATA'),
                COALESCE(s.swipesum_status, 'NO_DATA')
            )                                                         THEN 'WARN'
            WHEN 'NO_DATA' IN (
                COALESCE(a.ach_status,      'NO_DATA'),
                COALESCE(p.paypal_status,   'NO_DATA'),
                COALESCE(s.swipesum_status, 'NO_DATA')
            )                                                         THEN 'WARN'
            ELSE 'PASS'
        END                                                           AS cash_recon_status
    FROM cash_months cm
    LEFT JOIN ach_status      a ON a.report_month = cm.report_month
    LEFT JOIN paypal_status   p ON p.report_month = cm.report_month
    LEFT JOIN swipesum_status s ON s.report_month = cm.report_month
),

-- ── 3. AR RECONCILIATION ─────────────────────────────────────────────────────
ar_agg AS (
    SELECT
        report_month,
        recon_status                                                  AS ar_recon_status_raw,
        -- Normalize: INVESTIGATE is a soft warning, not a hard FAIL
        CASE
            WHEN recon_status = 'PASS'        THEN 'PASS'
            WHEN recon_status = 'INVESTIGATE' THEN 'WARN'
            ELSE 'FAIL'
        END                                                           AS ar_recon_status
    FROM finance.v_ar_oi_reconciliation
),

-- ── 4. CATCHALL MONITOR ──────────────────────────────────────────────────────
catchall_agg AS (
    SELECT
        report_month,
        status                                                        AS catchall_status_raw,
        -- ALERT is blocking; WARN/OK are acceptable
        CASE
            WHEN status = 'ALERT' THEN 'FAIL'
            WHEN status = 'WARN'  THEN 'WARN'
            ELSE 'PASS'
        END                                                           AS catchall_status
    FROM finance.v_catchall_monitor
),

-- ── 5. DEFERRED REVENUE ──────────────────────────────────────────────────────
deferred_agg AS (
    SELECT
        month                                                         AS report_month,
        deferred_balance_23000                                        AS deferred_rev_balance,
        -- Balance should be >= 0 (credit balance on liability account)
        CASE
            WHEN deferred_balance_23000 IS NULL   THEN 'WARN'
            WHEN deferred_balance_23000 < 0       THEN 'FAIL'
            WHEN deferred_balance_23000 = 0       THEN 'WARN'   -- fully amortized — worth noting
            ELSE 'PASS'
        END                                                           AS deferred_status
    FROM finance.v_deferred_maint_balance
),

-- ── SPINE: union of all report months across all sources ─────────────────────
all_months AS (
    SELECT report_month FROM pnl_agg
    UNION
    SELECT report_month FROM cash_agg
    UNION
    SELECT report_month FROM ar_agg
    UNION
    SELECT report_month FROM catchall_agg
    UNION
    SELECT report_month FROM deferred_agg
),

-- ── FINAL ASSEMBLY ───────────────────────────────────────────────────────────
assembled AS (
    SELECT
        am.report_month,

        -- P&L
        COALESCE(pnl.pnl_status,       'NO_DATA')                    AS pnl_status,
        COALESCE(pnl.pnl_fail_count,   0)                            AS pnl_fail_count,
        COALESCE(pnl.pnl_warn_count,   0)                            AS pnl_warn_count,

        -- Cash
        COALESCE(c.cash_recon_status,  'NO_DATA')                    AS cash_recon_status,
        COALESCE(c.ach_status,         'NO_DATA')                    AS ach_status,
        COALESCE(c.paypal_status,      'NO_DATA')                    AS paypal_status,
        COALESCE(c.swipesum_status,    'NO_DATA')                    AS swipesum_status,
        c.ach_abs_variance,
        c.paypal_variance,
        c.swipesum_variance,

        -- AR
        COALESCE(ar.ar_recon_status,   'NO_DATA')                    AS ar_recon_status,
        ar.ar_recon_status_raw,

        -- Catchall
        COALESCE(ca.catchall_status,   'NO_DATA')                    AS catchall_status,
        ca.catchall_status_raw,

        -- Deferred revenue
        d.deferred_rev_balance,
        COALESCE(d.deferred_status,    'NO_DATA')                    AS deferred_status

    FROM all_months am
    LEFT JOIN pnl_agg      pnl ON pnl.report_month = am.report_month
    LEFT JOIN cash_agg       c ON c.report_month   = am.report_month
    LEFT JOIN ar_agg        ar ON ar.report_month  = am.report_month
    LEFT JOIN catchall_agg  ca ON ca.report_month  = am.report_month
    LEFT JOIN deferred_agg   d ON d.report_month   = am.report_month
)

-- ── OUTPUT ───────────────────────────────────────────────────────────────────
SELECT
    report_month,

    -- Individual check statuses
    pnl_status,
    pnl_fail_count,
    pnl_warn_count,
    cash_recon_status,
    ach_status,
    paypal_status,
    swipesum_status,
    ach_abs_variance,
    paypal_variance,
    swipesum_variance,
    ar_recon_status,
    ar_recon_status_raw,
    catchall_status,
    catchall_status_raw,
    deferred_rev_balance,
    deferred_status,

    -- Overall readiness
    CASE
        WHEN 'FAIL' = ANY(ARRAY[
            pnl_status,
            cash_recon_status,
            ar_recon_status,
            catchall_status,
            deferred_status
        ])                                                            THEN 'NOT_READY'
        WHEN 'NO_DATA' = ANY(ARRAY[
            pnl_status,
            cash_recon_status,
            ar_recon_status,
            catchall_status
        ])                                                            THEN 'NOT_READY'
        ELSE 'READY'
    END                                                               AS overall_status,

    -- Human-readable list of what is blocking close
    ARRAY_REMOVE(
        ARRAY[
            CASE WHEN pnl_status       = 'FAIL'    THEN 'PnL: ' || pnl_fail_count || ' account(s) FAIL'         END,
            CASE WHEN pnl_status       = 'NO_DATA' THEN 'PnL: no data'                                            END,
            CASE WHEN cash_recon_status = 'FAIL'   THEN 'Cash: processor variance exceeds threshold'              END,
            CASE WHEN cash_recon_status = 'NO_DATA' THEN 'Cash: no data'                                           END,
            CASE WHEN ach_status        = 'FAIL'   THEN '  → ACH deposit variance: $' || ROUND(ach_abs_variance,2) END,
            CASE WHEN paypal_status     = 'FAIL'   THEN '  → PayPal: INVESTIGATE (' || ar_recon_status_raw || ')' END,
            CASE WHEN swipesum_status   = 'FAIL'   THEN '  → SwipeSum variance: $' || ROUND(ABS(COALESCE(swipesum_variance,0)),2) END,
            CASE WHEN ar_recon_status   = 'FAIL'   THEN 'AR: reconciliation FAIL'                                 END,
            CASE WHEN ar_recon_status   = 'NO_DATA' THEN 'AR: no data'                                             END,
            CASE WHEN catchall_status   = 'FAIL'   THEN 'Catchall: ALERT — uncaptured transactions present'       END,
            CASE WHEN catchall_status   = 'NO_DATA' THEN 'Catchall: no data'                                       END,
            CASE WHEN deferred_status   = 'FAIL'   THEN 'Deferred revenue: negative balance'                      END
        ],
        NULL
    )                                                                 AS blocking_items

FROM assembled
ORDER BY report_month DESC;
