-- ============================================================
-- Phase 2.2: finance.v_clearing_account_balance
-- ============================================================
-- Purpose: Shows monthly clearing account balances for close validation.
--   - Revenue/COGS clearing accounts (P&L parents): should net to $0 each month
--     after the Controller's reclass JEs reclassify to numbered sub-accounts.
--   - Balance sheet clearing accounts (PayPal, Undeposited Funds): cumulative
--     running balance should be $0 (all receipts deposited/cleared).
--
-- Account types included:
--   P&L PARENT (revenue clearing):
--     'SaaS Platform:Fingerprinting Services'
--     'SaaS Platform COGS:Fingerprinting Svcs Cost'
--     'Support Fees'
--     'Solutions'
--     'Solutions COGS'
--   BALANCE SHEET CLEARING:
--     '10090 - PayPal - Clearing'
--     '11100 - Undeposited Funds'
--
-- Sources:
--   - raw_quickbooks.journal_entry_lines / journal_entries (all accounts)
--   - raw_quickbooks.deposit_lines / deposits  (B/S clearing -- funds flowing out)
--   - raw_quickbooks.deposits.deposit_to_account_name (B/S clearing -- bank receipt draining)
--   - raw_quickbooks.sales_receipts (B/S clearing -- receipts flowing in)
--
-- Opening/ending balance logic:
--   P&L accounts: opening_balance always 0 (P&L resets each month);
--                 ending_balance = net_activity for the month.
--   B/S accounts: cumulative running balance (ending = prior ending + net_activity).
--
-- Status:
--   'CLEAR' = ending_balance = $0.00
--   'OPEN'  = non-zero ending balance (close is incomplete)
-- ============================================================

CREATE OR REPLACE VIEW finance.v_clearing_account_balance AS

WITH

-- ----------------------------------------------------------------
-- 1. Define clearing accounts and their type
-- ----------------------------------------------------------------
clearing_accounts (account_name, account_type) AS (
  VALUES
    ('SaaS Platform:Fingerprinting Services',        'PL_PARENT'),
    ('SaaS Platform COGS:Fingerprinting Svcs Cost',  'PL_PARENT'),
    ('Support Fees',                                  'PL_PARENT'),
    ('Solutions',                                     'PL_PARENT'),
    ('Solutions COGS',                                'PL_PARENT'),
    ('10090 - PayPal - Clearing',                     'BS_CLEARING'),
    ('11100 - Undeposited Funds',                     'BS_CLEARING')
),

-- ----------------------------------------------------------------
-- 2. JE activity for ALL clearing accounts
--    Debit  = positive (increases balance / debit-normal B/S asset)
--    Credit = negative
-- ----------------------------------------------------------------
je_activity AS (
  SELECT
    jel.account_name,
    DATE_TRUNC('month', je.txn_date)::date                                    AS month,
    SUM(CASE WHEN jel.posting_type = 'Debit'  THEN  jel.amount ELSE 0 END)   AS debits,
    SUM(CASE WHEN jel.posting_type = 'Credit' THEN  jel.amount ELSE 0 END)   AS credits,
    SUM(CASE WHEN jel.posting_type = 'Debit'  THEN  jel.amount
                                                     ELSE -jel.amount END)    AS net
  FROM raw_quickbooks.journal_entry_lines jel
  JOIN raw_quickbooks.journal_entries je ON je.id = jel.journal_entry_id
  WHERE jel.account_name IN (SELECT account_name FROM clearing_accounts)
  GROUP BY 1, 2
),

-- ----------------------------------------------------------------
-- 3. Deposit_lines activity for B/S clearing accounts
--    deposit_lines records what's being sourced FROM a holding account
--    (e.g. "from Undeposited Funds") — this drains the clearing account.
--    Amount is the cash amount moved; we treat it as a credit to clearing.
-- ----------------------------------------------------------------
deposit_line_activity AS (
  SELECT
    dl.account_name,
    DATE_TRUNC('month', d.txn_date)::date  AS month,
    0::numeric                              AS debits,
    SUM(dl.amount)                          AS credits,
    -SUM(dl.amount)                         AS net   -- drains the clearing account
  FROM raw_quickbooks.deposit_lines dl
  JOIN raw_quickbooks.deposits d ON d.id = dl.deposit_id
  WHERE dl.account_name IN (SELECT account_name FROM clearing_accounts)
  GROUP BY 1, 2
),

-- ----------------------------------------------------------------
-- 4. Deposits that go TO a clearing account
--    (deposit_to_account_name = PayPal Clearing / Undeposited Funds)
--    When a bank deposit's destination IS the clearing account, it's
--    a receipt that flows INTO the clearing pool — treated as a credit
--    increasing the liability-like clearing balance.
--    (Sales receipts posted to PayPal land here; this drains it later
--    when the bank sweep happens.)
-- ----------------------------------------------------------------
deposit_to_activity AS (
  SELECT
    deposit_to_account_name                 AS account_name,
    DATE_TRUNC('month', txn_date)::date     AS month,
    0::numeric                              AS debits,
    SUM(total_amount)                       AS credits,
    -SUM(total_amount)                      AS net   -- PayPal cleared to bank = drain
  FROM raw_quickbooks.deposits
  WHERE deposit_to_account_name IN (SELECT account_name FROM clearing_accounts)
  GROUP BY 1, 2
),

-- ----------------------------------------------------------------
-- 5. Sales receipts deposited directly to a clearing account
--    (receipt received → sits in PayPal or Undeposited Funds)
--    This ADDS to the clearing balance (debit clearing, credit revenue).
--    From the clearing account's perspective: debit (positive).
-- ----------------------------------------------------------------
sales_receipt_activity AS (
  SELECT
    deposit_to_account_name                 AS account_name,
    DATE_TRUNC('month', txn_date)::date     AS month,
    SUM(total_amount)                       AS debits,
    0::numeric                              AS credits,
    SUM(total_amount)                       AS net   -- adds to clearing balance
  FROM raw_quickbooks.sales_receipts
  WHERE deposit_to_account_name IN (SELECT account_name FROM clearing_accounts)
  GROUP BY 1, 2
),

-- ----------------------------------------------------------------
-- 6. Union all activity sources
-- ----------------------------------------------------------------
all_activity AS (
  SELECT account_name, month, debits, credits, net FROM je_activity
  UNION ALL
  SELECT account_name, month, debits, credits, net FROM deposit_line_activity
  UNION ALL
  SELECT account_name, month, debits, credits, net FROM deposit_to_activity
  UNION ALL
  SELECT account_name, month, debits, credits, net FROM sales_receipt_activity
),

-- ----------------------------------------------------------------
-- 7. Aggregate by account + month
-- ----------------------------------------------------------------
monthly_activity AS (
  SELECT
    ca.account_name,
    ca.account_type,
    a.month                          AS report_month,
    ROUND(SUM(a.debits),  2)         AS debits,
    ROUND(SUM(a.credits), 2)         AS credits,
    ROUND(SUM(a.net),     2)         AS net_activity
  FROM all_activity a
  JOIN clearing_accounts ca ON ca.account_name = a.account_name
  GROUP BY 1, 2, 3
),

-- ----------------------------------------------------------------
-- 8. Compute opening / ending balances
--    P&L accounts: no running balance (resets monthly) → opening = 0
--    B/S accounts: cumulative SUM of prior months' net_activity
-- ----------------------------------------------------------------
with_balances AS (
  SELECT
    account_name,
    account_type,
    report_month,
    debits,
    credits,
    net_activity,
    CASE
      WHEN account_type = 'BS_CLEARING'
        THEN ROUND(
          SUM(net_activity) OVER (
            PARTITION BY account_name
            ORDER BY report_month
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
          ), 2)
      ELSE 0::numeric
    END                              AS opening_balance,
    CASE
      WHEN account_type = 'BS_CLEARING'
        THEN ROUND(
          SUM(net_activity) OVER (
            PARTITION BY account_name
            ORDER BY report_month
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
          ), 2)
      ELSE ROUND(net_activity, 2)
    END                              AS ending_balance
  FROM monthly_activity
)

-- ----------------------------------------------------------------
-- 9. Final output with status flag
-- ----------------------------------------------------------------
SELECT
  account_name,
  account_type,
  report_month,
  COALESCE(opening_balance, 0)                             AS opening_balance,
  debits,
  credits,
  net_activity,
  CASE
    WHEN account_type = 'BS_CLEARING'
      THEN COALESCE(opening_balance, 0) + net_activity
    ELSE net_activity
  END                                                       AS ending_balance,
  CASE
    WHEN (
      CASE
        WHEN account_type = 'BS_CLEARING'
          THEN COALESCE(opening_balance, 0) + net_activity
        ELSE net_activity
      END
    ) = 0
      THEN 'CLEAR'
    ELSE 'OPEN'
  END                                                       AS status
FROM with_balances
ORDER BY account_type, account_name, report_month;
