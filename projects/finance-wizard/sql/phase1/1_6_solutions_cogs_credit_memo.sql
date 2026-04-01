-- Phase 1.6: Credit Memo COGS Adjustment Investigation
-- Goal: Determine whether v_solutions_cogs_txn needs a credit_memo_adj CTE
--       analogous to the one in v_solutions_revenue_txn.
--
-- FINDING: No view change needed. See results/phase1_6_credit_memo_cogs.md.
--
-- The queries below document the investigation.

-- Step 1: Do credit_memo_lines have COGS-side account refs?
SELECT DISTINCT
    (cml._raw -> 'SalesItemLineDetail' -> 'ItemAccountRef' ->> 'name') AS account_ref
FROM raw_quickbooks.credit_memo_lines cml
WHERE
    (cml._raw -> 'SalesItemLineDetail' -> 'ItemAccountRef' ->> 'name') ILIKE '%53%'
    OR (cml._raw -> 'SalesItemLineDetail' -> 'ItemAccountRef' ->> 'name') ILIKE '%cogs%'
    OR (cml._raw -> 'SalesItemLineDetail' -> 'ItemAccountRef' ->> 'name') ILIKE '%cost%';
-- Result: 'SaaS Platform COGS:Fingerprinting Svcs Cost', 'Solutions COGS'
-- Neither maps to a specific 53xxx account used by v_solutions_cogs_txn.

-- Step 2: What transaction types appear in report_cogs_transactions for Solutions COGS accounts?
SELECT DISTINCT transaction_type
FROM raw_quickbooks.report_cogs_transactions
WHERE account_name IN (
    '53010 - Hardware',
    '53020 - Software & Other',
    '53030 - Shipping',
    '53040 - Services'
)
ORDER BY 1;
-- Result includes 'Credit Memo' — so QB already posts COGS-side credit memos
-- directly to the 53xxx accounts and they appear in report_cogs_transactions.

-- Step 3: What COGS account names do credit memos post to in report_cogs_transactions?
SELECT DISTINCT account_name
FROM raw_quickbooks.report_cogs_transactions
WHERE transaction_type = 'Credit Memo'
ORDER BY 1;
-- Result: only '53010 - Hardware' — all within the current WHERE clause filter.

-- Step 4: Full detail of credit memo rows already captured by the view
SELECT
    transaction_date,
    name,
    account_name,
    amount,
    transaction_type
FROM raw_quickbooks.report_cogs_transactions
WHERE
    transaction_type = 'Credit Memo'
    AND account_name IN (
        '53010 - Hardware',
        '53020 - Software & Other',
        '53030 - Shipping',
        '53040 - Services'
    )
ORDER BY transaction_date;
-- 7 rows, all negative amounts (-$2,786.96 total) — correctly reducing COGS.

-- Step 5: Are there any credit memo rows outside the 53xxx filter?
SELECT COUNT(*)
FROM raw_quickbooks.report_cogs_transactions
WHERE
    transaction_type = 'Credit Memo'
    AND account_name NOT IN (
        '53010 - Hardware',
        '53020 - Software & Other',
        '53030 - Shipping',
        '53040 - Services'
    );
-- Result: 0 rows. No credit memos slip outside the filter.

-- Step 6: Check for JE-based COGS reversals tied to credit memos
SELECT
    je.doc_number,
    je.txn_date,
    jel.account_name,
    jel.amount,
    jel.posting_type
FROM raw_quickbooks.journal_entry_lines jel
JOIN raw_quickbooks.journal_entries je ON je.id = jel.journal_entry_id
WHERE jel.account_name IN (
    '53010 - Hardware',
    '53020 - Software & Other',
    '53030 - Shipping',
    '53040 - Services'
)
ORDER BY je.txn_date;
-- Result: 0 rows. No JE-based COGS reversals for these accounts.

-- Step 7: Validate current view output — confirm credit_memo source_type is present
SELECT report_month, gl_account, source_type, SUM(amount) AS total
FROM finance.v_solutions_cogs_txn
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3;

-- CONCLUSION:
-- v_solutions_cogs_txn does NOT need a credit_memo_adj CTE.
-- QuickBooks natively posts credit memo COGS reversals as 'Credit Memo'
-- transaction_type rows directly in report_cogs_transactions against the 53xxx
-- accounts. The existing WHERE clause already captures them. All 7 credit memo
-- rows are present in the view with correct negative amounts.
--
-- The asymmetry with v_solutions_revenue_txn exists because:
--   - Revenue view reads raw invoice_lines / credit_memo_lines (QB API objects)
--   - COGS view reads report_cogs_transactions (a pre-aggregated QB report export)
--     which already consolidates all transaction types including credit memos.
--
-- No CREATE OR REPLACE VIEW was executed. The current definition is correct.
