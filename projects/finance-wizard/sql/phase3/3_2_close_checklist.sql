-- =============================================================================
-- Phase 3.2: Create finance.close_checklist table
-- Database: B4All-Hub (dozjdswqnzqwvieqvwpe)
-- Purpose: Track each month-end close task with status, owner, timestamp,
--          and blocking dependencies across ~47 tasks in 5 phases.
-- =============================================================================

-- Step 1: Check if table already exists
SELECT EXISTS (
  SELECT 1 FROM information_schema.tables
  WHERE table_schema = 'finance' AND table_name = 'close_checklist'
) AS table_exists;

-- Step 2: Create the table
CREATE TABLE IF NOT EXISTS finance.close_checklist (
  id                SERIAL PRIMARY KEY,
  close_year        INTEGER NOT NULL,
  close_month       INTEGER NOT NULL,
  phase             INTEGER NOT NULL,          -- 1-5
  task_number       TEXT    NOT NULL,          -- e.g. '3.9', '2.1'
  task_name         TEXT    NOT NULL,
  description       TEXT,
  owner             TEXT,                      -- 'controller', 'bookkeeper', 'system', 'manager'
  status            TEXT    DEFAULT 'pending', -- pending, in_progress, completed, blocked, skipped
  hub_surface       TEXT,                      -- which finance view/function supports this
  automated         BOOLEAN DEFAULT FALSE,     -- can the Hub do this automatically?
  started_at        TIMESTAMPTZ,
  completed_at      TIMESTAMPTZ,
  completed_by      TEXT,
  notes             TEXT,
  blocked_by        TEXT[],                    -- array of task_numbers this depends on
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(close_year, close_month, task_number)
);

-- Step 3: Index on (close_year, close_month, status) for common query patterns
CREATE INDEX IF NOT EXISTS idx_close_checklist_period_status
  ON finance.close_checklist (close_year, close_month, status);

-- Step 4: Seed template tasks (year=0, month=0 is the canonical template)
-- These rows serve as the source-of-truth template that init_close_checklist() copies.

INSERT INTO finance.close_checklist
  (close_year, close_month, phase, task_number, task_name, description, owner, hub_surface, automated, blocked_by)
VALUES

-- ── Phase 1: Pre-close ────────────────────────────────────────────────────────
(0, 0, 1, '1.1',
 'Post fixed JEs (rent, insurance)',
 'Post standard monthly journal entries for fixed expenses: rent, insurance premiums.',
 'bookkeeper', NULL, FALSE, NULL),

(0, 0, 1, '1.2',
 'Post commission amortization',
 'Amortize prepaid commissions per the commission schedule.',
 'bookkeeper', NULL, FALSE, NULL),

(0, 0, 1, '1.3',
 'Post prepaid amortization',
 'Amortize all other prepaid assets per the prepaid schedule.',
 'bookkeeper', NULL, FALSE, NULL),

(0, 0, 1, '1.4',
 'Post depreciation',
 'Post monthly depreciation journal entries from the fixed-asset schedule.',
 'bookkeeper', NULL, FALSE, NULL),

-- ── Phase 2: Bookkeeper tasks ─────────────────────────────────────────────────
(0, 0, 2, '2.1',
 'Bank posting — primary operating account',
 'Reconcile and post all transactions from the primary operating bank account.',
 'bookkeeper', NULL, FALSE, ARRAY['1.1','1.2','1.3','1.4']),

(0, 0, 2, '2.2',
 'Bank posting — payroll account',
 'Reconcile and post all transactions from the payroll funding account.',
 'bookkeeper', NULL, FALSE, ARRAY['1.1','1.2','1.3','1.4']),

(0, 0, 2, '2.3',
 'Bank posting — savings / reserve account',
 'Reconcile and post transactions from reserve/savings accounts.',
 'bookkeeper', NULL, FALSE, ARRAY['1.1','1.2','1.3','1.4']),

(0, 0, 2, '2.4',
 'Bank posting — other accounts',
 'Reconcile and post any remaining bank accounts.',
 'bookkeeper', NULL, FALSE, ARRAY['1.1','1.2','1.3','1.4']),

(0, 0, 2, '2.5',
 'Credit card posting — primary card',
 'Code and post all primary company credit card transactions.',
 'bookkeeper', NULL, FALSE, ARRAY['1.1','1.2','1.3','1.4']),

(0, 0, 2, '2.6',
 'Credit card posting — secondary cards',
 'Code and post secondary/employee credit card transactions.',
 'bookkeeper', NULL, FALSE, ARRAY['1.1','1.2','1.3','1.4']),

(0, 0, 2, '2.7',
 'Credit card posting — PayPal',
 'Code and post PayPal transactions; cross-reference ACH receipts.',
 'bookkeeper', NULL, FALSE, ARRAY['1.1','1.2','1.3','1.4']),

(0, 0, 2, '2.8',
 'Credit card posting — SwipeSum / merchant accounts',
 'Code and post SwipeSum and other merchant processor transactions.',
 'bookkeeper', NULL, FALSE, ARRAY['1.1','1.2','1.3','1.4']),

(0, 0, 2, '2.12',
 'Vendor bills — AP entry',
 'Enter all outstanding vendor bills received during the period.',
 'bookkeeper', NULL, FALSE, ARRAY['2.1','2.2','2.3','2.4']),

(0, 0, 2, '2.13',
 'Vendor bills — verify approvals',
 'Confirm all entered vendor bills have appropriate approval documentation.',
 'bookkeeper', NULL, FALSE, ARRAY['2.12']),

(0, 0, 2, '2.14',
 'Vendor bills — AP aging review',
 'Review AP aging for any past-due items or duplicates before controller handoff.',
 'bookkeeper', NULL, FALSE, ARRAY['2.13']),

-- ── Phase 3: Controller tasks ─────────────────────────────────────────────────
(0, 0, 3, '3.4',
 'Payroll JE — import TriNet gross pay',
 'Pull gross payroll detail from TriNet and prepare the payroll journal entry.',
 'controller', NULL, FALSE, ARRAY['2.1','2.2','2.3','2.4','2.5','2.6','2.7','2.8','2.12','2.13','2.14']),

(0, 0, 3, '3.5',
 'Payroll JE — employer taxes & benefits',
 'Add employer payroll tax and benefits lines to the payroll JE.',
 'controller', NULL, FALSE, ARRAY['3.4']),

(0, 0, 3, '3.6',
 'Payroll JE — department allocation',
 'Allocate payroll costs to COGS vs. OpEx by department/role.',
 'controller', NULL, FALSE, ARRAY['3.5']),

(0, 0, 3, '3.7',
 'Payroll JE — post to QuickBooks',
 'Post the approved payroll journal entry to QBO.',
 'controller', NULL, FALSE, ARRAY['3.6']),

(0, 0, 3, '3.8',
 'Payroll JE — verify payroll liability accounts',
 'Confirm payroll liability accounts clear to zero after posting.',
 'controller', NULL, FALSE, ARRAY['3.7']),

(0, 0, 3, '3.9',
 'SaaS/Relay true-up (DN000811)',
 'Run derive_dn000811() to compute the SaaS relay revenue true-up and post the JE.',
 'controller', 'derive_dn000811()', TRUE, ARRAY['3.7','3.8']),

(0, 0, 3, '3.10',
 'FP Revenue breakout',
 'Break out Field Products revenue by line using v_fp_contract_txn and v_relay_txn.',
 'controller', 'v_fp_contract_txn, v_relay_txn', TRUE, ARRAY['3.9']),

(0, 0, 3, '3.11',
 'FP COGS breakout',
 'Break out Field Products COGS using v_fp_cogs_proof and post the JE.',
 'controller', 'v_fp_cogs_proof', TRUE, ARRAY['3.10']),

(0, 0, 3, '3.12',
 'SAM cost true-up (DN000812)',
 'Run derive_dn000812() to compute the SAM cost true-up and post the JE.',
 'controller', 'derive_dn000812()', TRUE, ARRAY['3.11']),

(0, 0, 3, '3.13',
 'AR balance reconciliation',
 'Reconcile AR per QBO to SK AR balance using v_ar_oi_reconciliation.',
 'controller', 'v_ar_oi_reconciliation', TRUE, ARRAY['3.12']),

(0, 0, 3, '3.15',
 'Shipping COGS reclass',
 'Reclassify shipping charges to COGS using v_shipping_cogs_reclass.',
 'controller', 'v_shipping_cogs_reclass', TRUE, ARRAY['3.13']),

(0, 0, 3, '3.16',
 'Auto Maintenance adjustment',
 'Post deferred maintenance close JE using v_deferred_maint_close_je.',
 'controller', 'v_deferred_maint_close_je', TRUE, ARRAY['3.15']),

(0, 0, 3, '3.17',
 'Support reclass to deferred revenue',
 'Reclassify support billings to deferred revenue using v_deferred_maint_deferral.',
 'controller', 'v_deferred_maint_deferral', TRUE, ARRAY['3.16']),

(0, 0, 3, '3.18',
 'Support amortization',
 'Recognize deferred support revenue for the period using v_deferred_maint_recognition.',
 'controller', 'v_deferred_maint_recognition', TRUE, ARRAY['3.17']),

(0, 0, 3, '3.19',
 'Support rollforward',
 'Verify deferred maintenance balance rollforward using v_deferred_maint_balance.',
 'controller', 'v_deferred_maint_balance', TRUE, ARRAY['3.18']),

(0, 0, 3, '3.20',
 'Support Revenue breakout',
 'Break out Support revenue by contract type using v_support_revenue_txn.',
 'controller', 'v_support_revenue_txn', TRUE, ARRAY['3.19']),

(0, 0, 3, '3.23',
 'Solutions Revenue breakout',
 'Break out Solutions revenue by project using v_solutions_revenue_txn.',
 'controller', 'v_solutions_revenue_txn', TRUE, ARRAY['3.20']),

(0, 0, 3, '3.24',
 'Solutions COGS breakout',
 'Break out Solutions COGS by project using v_solutions_cogs_txn.',
 'controller', 'v_solutions_cogs_txn', TRUE, ARRAY['3.23']),

(0, 0, 3, '3.26',
 'Cash reconciliation',
 'Reconcile ACH, PayPal, and SwipeSum cash using v_ach_*, v_paypal_*, v_swipesum_* views.',
 'controller', 'v_ach_*, v_paypal_*, v_swipesum_*', TRUE, ARRAY['3.24']),

(0, 0, 3, '3.27',
 'AR reconciliation',
 'Reconcile AR aging snapshot to general ledger using v_ar_aging_snapshot.',
 'controller', 'v_ar_aging_snapshot', TRUE, ARRAY['3.26']),

(0, 0, 3, '3.28',
 'Deferred Revenue reconciliation',
 'Confirm deferred revenue balance per GL matches rollforward using v_deferred_maint_balance.',
 'controller', 'v_deferred_maint_balance', TRUE, ARRAY['3.27']),

(0, 0, 3, '3.30',
 'Balance sheet reconciliation',
 'Reconcile all balance sheet accounts; partial hub surface available.',
 'controller', 'partial hub surface', FALSE, ARRAY['3.28']),

(0, 0, 3, '3.33',
 'Trial balance',
 'Pull and review trial balance using v_trial_balance; confirm debits = credits.',
 'controller', 'v_trial_balance', TRUE, ARRAY['3.30']),

(0, 0, 3, '3.34',
 'Variance analysis',
 'Run month-over-month and budget variance analysis using v_variance_analysis.',
 'controller', 'v_variance_analysis', TRUE, ARRAY['3.33']),

-- ── Phase 4: Review ───────────────────────────────────────────────────────────
(0, 0, 4, '4.1',
 'Manager P&L review',
 'Manager reviews the finalized P&L for accuracy and business reasonableness.',
 'manager', NULL, FALSE, ARRAY['3.33','3.34']),

(0, 0, 4, '4.2',
 'Variance sign-off',
 'Manager signs off on all material variances flagged by the controller.',
 'manager', NULL, FALSE, ARRAY['4.1']),

-- ── Phase 5: Finalization ─────────────────────────────────────────────────────
(0, 0, 5, '5.1',
 'Lock period',
 'Lock the accounting period in QuickBooks to prevent further edits.',
 'controller', NULL, FALSE, ARRAY['4.2']),

(0, 0, 5, '5.2',
 'Generate reports',
 'Generate and distribute final close reports (P&L, BS, cash flow) to stakeholders.',
 'controller', NULL, FALSE, ARRAY['5.1'])

ON CONFLICT (close_year, close_month, task_number) DO NOTHING;

-- Step 5: Function to initialize a new month's checklist from the template
CREATE OR REPLACE FUNCTION finance.init_close_checklist(p_year INTEGER, p_month INTEGER)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
  v_inserted INTEGER;
BEGIN
  INSERT INTO finance.close_checklist (
    close_year, close_month, phase, task_number, task_name, description,
    owner, status, hub_surface, automated, blocked_by,
    notes, created_at, updated_at
  )
  SELECT
    p_year,
    p_month,
    phase,
    task_number,
    task_name,
    description,
    owner,
    'pending',       -- always start fresh
    hub_surface,
    automated,
    blocked_by,
    NULL,            -- no notes on init
    NOW(),
    NOW()
  FROM finance.close_checklist
  WHERE close_year = 0
    AND close_month = 0
  ON CONFLICT (close_year, close_month, task_number) DO NOTHING;

  GET DIAGNOSTICS v_inserted = ROW_COUNT;
  RETURN v_inserted;
END;
$$;

COMMENT ON FUNCTION finance.init_close_checklist(INTEGER, INTEGER) IS
  'Copies the template tasks (year=0, month=0) into a live checklist for the given year/month. Returns the number of rows inserted. Safe to call multiple times (idempotent via ON CONFLICT DO NOTHING).';

-- Step 6: Register in meta.object_registry (if the registry table exists)
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'meta' AND table_name = 'object_registry'
  ) THEN
    INSERT INTO meta.object_registry (schema_name, object_name, object_type, description, created_at)
    VALUES
      ('finance', 'close_checklist', 'table',
       'Month-end close task tracker. Template rows stored at year=0, month=0. Use finance.init_close_checklist() to seed a live period.',
       NOW()),
      ('finance', 'init_close_checklist', 'function',
       'Copies template close tasks (year=0, month=0) into a live checklist for a given year/month. Returns insert count.',
       NOW())
    ON CONFLICT DO NOTHING;

    RAISE NOTICE 'Registered finance.close_checklist and finance.init_close_checklist in meta.object_registry';
  ELSE
    RAISE NOTICE 'meta.object_registry not found — skipping registration';
  END IF;
END;
$$;

-- Verification query
SELECT
  phase,
  COUNT(*)                                    AS task_count,
  COUNT(*) FILTER (WHERE automated = TRUE)   AS automated_count,
  COUNT(*) FILTER (WHERE hub_surface IS NOT NULL) AS has_hub_surface
FROM finance.close_checklist
WHERE close_year = 0 AND close_month = 0
GROUP BY phase
ORDER BY phase;
