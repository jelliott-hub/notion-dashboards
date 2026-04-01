-- Phase 2.6: AR / OI Reconciliation View
-- Compares aggregated QBO AR (v_ar_aging_snapshot) against ThinClient OI report (v_oi_monthly)
-- Flags deltas so the Controller can spot discrepancies at a glance.
--
-- Delta basis: oi_ar (AR-specific figure from TC report) vs. qb_ar_total (sum of open invoices from QBO)
-- Status thresholds: PASS < $1 000 | WARN $1 000-$5 000 | INVESTIGATE > $5 000

CREATE OR REPLACE VIEW finance.v_ar_oi_reconciliation AS
WITH qb_monthly AS (
    SELECT
        report_month,
        SUM(amount_due)  AS qb_ar_total,
        COUNT(*)         AS invoice_count
    FROM finance.v_ar_aging_snapshot
    GROUP BY report_month
)
SELECT
    COALESCE(qb.report_month, oi.report_month)                          AS report_month,

    -- QuickBooks side
    ROUND(qb.qb_ar_total::numeric, 2)                                   AS qb_ar_total,
    qb.invoice_count                                                     AS qb_invoice_count,

    -- ThinClient OI side
    ROUND(oi.oi_ar::numeric, 2)                                         AS tc_oi_ar,
    oi.client_count                                                      AS tc_client_count,

    -- Delta: positive means TC sees more AR than QB
    ROUND((oi.oi_ar - qb.qb_ar_total)::numeric, 2)                     AS delta,

    -- Percent delta relative to QB total (NULL when QB is zero to avoid divide-by-zero)
    CASE
        WHEN qb.qb_ar_total IS NULL OR qb.qb_ar_total = 0 THEN NULL
        ELSE ROUND(
            ((oi.oi_ar - qb.qb_ar_total) / qb.qb_ar_total * 100)::numeric,
            4
        )
    END                                                                  AS pct_delta,

    -- Reconciliation status based on absolute delta
    CASE
        WHEN qb.qb_ar_total IS NULL THEN 'MISSING_QB'
        WHEN oi.oi_ar       IS NULL THEN 'MISSING_TC'
        WHEN ABS(oi.oi_ar - qb.qb_ar_total) < 1000    THEN 'PASS'
        WHEN ABS(oi.oi_ar - qb.qb_ar_total) < 5000    THEN 'WARN'
        ELSE                                                 'INVESTIGATE'
    END                                                                  AS recon_status

FROM qb_monthly            qb
FULL OUTER JOIN finance.v_oi_monthly oi
    ON qb.report_month = oi.report_month

ORDER BY COALESCE(qb.report_month, oi.report_month);
