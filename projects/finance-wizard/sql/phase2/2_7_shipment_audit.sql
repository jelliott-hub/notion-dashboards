-- =============================================================================
-- Phase 2.7: finance.v_solutions_shipment_audit
-- Close Checklist Task 3.22: Confirm all shipped orders are invoiced
--
-- CONTEXT: B4ALL has no dedicated shipment tracking table. Shipments are
-- proxied by QB Estimates (SO-numbered), which represent orders committed
-- to customers before invoicing. This view audits the estimate-to-invoice
-- pipeline using two complementary sources:
--
--   1. raw_quickbooks.invoice_linked_txns  -- QB-native estimate->invoice links
--   2. finance.v_qb_estimates              -- Email-based estimate event log (SO#s)
--
-- "Shipment" proxy = a QB Estimate that was sent or accepted by a customer.
-- "Invoiced"       = the estimate has a corresponding QB invoice.
-- =============================================================================

CREATE OR REPLACE VIEW finance.v_solutions_shipment_audit AS

-- -----------------------------------------------------------------
-- Part A: QB-native estimate-to-invoice linkage
--   Aggregates all invoices that were converted from QB estimates.
--   Each row = one distinct invoice, with its linked estimate IDs.
-- -----------------------------------------------------------------
WITH estimate_invoices AS (
    SELECT
        i.id                                        AS invoice_id,
        i.doc_number                                AS so_number,
        i.customer_name,
        i.txn_date                                  AS invoice_date,
        i.due_date,
        i.total_amount,
        i.balance,
        i.status                                    AS invoice_status,
        -- Collect all QB estimate IDs linked to this invoice
        STRING_AGG(ilt.linked_txn_id::text, ', '
                   ORDER BY ilt.linked_txn_id)      AS linked_estimate_ids,
        COUNT(DISTINCT ilt.linked_txn_id)           AS estimate_link_count
    FROM raw_quickbooks.invoice_linked_txns ilt
    JOIN raw_quickbooks.invoices i
        ON ilt.invoice_id = i.id
    WHERE ilt.linked_txn_type = 'Estimate'
    GROUP BY
        i.id, i.doc_number, i.customer_name,
        i.txn_date, i.due_date,
        i.total_amount, i.balance, i.status
),

-- -----------------------------------------------------------------
-- Part B: Email estimate events (finance.v_qb_estimates)
--   Deduplicated to one row per SO number, capturing the latest
--   event type and the highest amount seen.
-- -----------------------------------------------------------------
email_estimates AS (
    SELECT
        so_number,
        MAX(event_type)                             AS last_event_type,
        MAX(amount)                                 AS estimate_amount,
        MAX(received_at)                            AS last_email_at,
        COUNT(*)                                    AS email_event_count
    FROM finance.v_qb_estimates
    WHERE event_type IN ('sent', 'accepted', 'payment_request', 'payment_receipt')
    GROUP BY so_number
)

-- -----------------------------------------------------------------
-- Final: Join email estimates to QB invoices on SO number.
--   Rows appear for every estimate that has an email event OR
--   a QB invoice link (FULL OUTER JOIN via UNION approach below).
--
--   audit_status logic:
--     'INVOICED_PAID'       -- estimate converted to invoice, fully paid
--     'INVOICED_OPEN'       -- estimate converted to invoice, balance remaining
--     'EMAIL_ONLY_NO_INV'   -- estimate emailed but no QB invoice found
--     'INVOICE_NO_EMAIL'    -- QB invoice from estimate but no email event logged
-- -----------------------------------------------------------------
SELECT
    COALESCE(ee.so_number, ei.so_number)            AS so_number,
    COALESCE(ei.customer_name, NULL)                AS customer_name,
    ei.invoice_id,
    ei.invoice_date,
    ei.due_date,
    ei.invoice_status,
    ei.total_amount                                 AS invoice_amount,
    ei.balance                                      AS invoice_balance,
    ei.linked_estimate_ids,
    ei.estimate_link_count,
    ee.last_event_type                              AS estimate_email_event,
    ee.estimate_amount                              AS estimate_email_amount,
    ee.last_email_at                                AS estimate_email_at,
    ee.email_event_count,

    -- Audit status flag
    CASE
        WHEN ei.invoice_id IS NOT NULL AND ei.invoice_status = 'Paid'
            THEN 'INVOICED_PAID'
        WHEN ei.invoice_id IS NOT NULL AND ei.invoice_status = 'Open'
            THEN 'INVOICED_OPEN'
        WHEN ei.invoice_id IS NULL AND ee.so_number IS NOT NULL
            THEN 'EMAIL_ONLY_NO_INV'
        WHEN ei.invoice_id IS NOT NULL AND ee.so_number IS NULL
            THEN 'INVOICE_NO_EMAIL'
        ELSE 'UNKNOWN'
    END                                             AS audit_status,

    -- Flag invoices with outstanding balance
    CASE
        WHEN ei.balance IS NOT NULL AND ei.balance > 0
            THEN TRUE
        ELSE FALSE
    END                                             AS has_open_balance,

    -- Days outstanding for open invoices
    CASE
        WHEN ei.invoice_status = 'Open' AND ei.invoice_date IS NOT NULL
            THEN (CURRENT_DATE - ei.invoice_date)
        ELSE NULL
    END                                             AS days_outstanding

FROM email_estimates ee
FULL OUTER JOIN estimate_invoices ei
    ON ee.so_number = ei.so_number

ORDER BY
    -- Surface problems first: open balances, then missing invoices
    CASE
        WHEN ei.invoice_status = 'Open'         THEN 1
        WHEN ee.so_number IS NOT NULL
         AND ei.invoice_id IS NULL              THEN 2
        WHEN ei.invoice_status = 'Paid'         THEN 3
        ELSE 4
    END,
    ei.invoice_date DESC NULLS LAST;

-- =============================================================================
-- Companion summary query (run manually for close checklist sign-off)
-- =============================================================================
-- SELECT
--     audit_status,
--     COUNT(*)                        AS record_count,
--     SUM(invoice_amount)             AS total_invoice_amt,
--     SUM(invoice_balance)            AS total_open_balance
-- FROM finance.v_solutions_shipment_audit
-- GROUP BY audit_status
-- ORDER BY 1;
