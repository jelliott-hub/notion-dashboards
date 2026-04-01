-- =============================================================================
-- Phase 3.1: Create finance.derive_close_je(p_year, p_month)
-- Database: B4All-Hub (dozjdswqnzqwvieqvwpe)
-- Purpose: Master close JE derivation function — aggregates DN000811,
--          DN000812, and all three deferred maintenance JE types into a
--          single, balanced set of journal entry lines for a given month-end.
-- Supports: Close checklist tasks 3.9, 3.12, 3.16, 3.17, 3.18
-- =============================================================================

-- =============================================================================
-- STEP 1: Verify existing dependencies
-- =============================================================================

-- 1a. Verify derive_dn000811 exists and returns data
SELECT * FROM finance.derive_dn000811(2026, 1);

-- 1b. Verify derive_dn000812 exists and returns data
SELECT * FROM finance.derive_dn000812(2026, 1);

-- 1c. Verify v_deferred_maint_close_je exists and returns data for target month
SELECT * FROM finance.v_deferred_maint_close_je
WHERE month = '2026-01-01';

-- 1d. Confirm view column names (in case they differ from spec)
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'finance'
  AND table_name   = 'v_deferred_maint_close_je'
ORDER BY ordinal_position;

-- =============================================================================
-- STEP 2: Create the master function
-- =============================================================================

CREATE OR REPLACE FUNCTION finance.derive_close_je(
  p_year  INTEGER,
  p_month INTEGER
)
RETURNS TABLE(
  je_source    TEXT,   -- 'DN000811' | 'DN000812' | 'DEFERRED_RECLASS' | 'DEFERRED_DEFERRAL' | 'DEFERRED_RECOGNITION'
  account_code TEXT,
  account_name TEXT,
  debit        NUMERIC,
  credit       NUMERIC,
  memo         TEXT
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN

  ---------------------------------------------------------------------------
  -- Segment 1: DN000811 — SaaS/Relay AR + COGS true-up
  -- Accounts: 11000, 51010, 51020, 51025, 41010, 41020, 41030  (7 lines)
  ---------------------------------------------------------------------------
  RETURN QUERY
  SELECT
    'DN000811'::TEXT,
    d.account_code,
    d.account_name,
    d.debit,
    d.credit,
    d.memo
  FROM finance.derive_dn000811(p_year, p_month) d;

  ---------------------------------------------------------------------------
  -- Segment 2: DN000812 — SAM AP/COGS true-up
  -- Accounts: 51025, 20000  (2 lines)
  ---------------------------------------------------------------------------
  RETURN QUERY
  SELECT
    'DN000812'::TEXT,
    d.account_code,
    d.account_name,
    d.debit,
    d.credit,
    d.memo
  FROM finance.derive_dn000812(p_year, p_month) d;

  ---------------------------------------------------------------------------
  -- Segment 3: Deferred maintenance close JEs
  -- Source: finance.v_deferred_maint_close_je
  --   je_type values: JE1_RECLASS, JE2_DEFERRAL, JE3_RECOGNITION
  --   Accounts: 23000, 44010–44050, SUPPORT_FEES_CLR
  --   side values: 'DR' | 'CR'
  --
  -- je_source mapping:
  --   JE1_RECLASS       -> 'DEFERRED_RECLASS'
  --   JE2_DEFERRAL      -> 'DEFERRED_DEFERRAL'
  --   JE3_RECOGNITION   -> 'DEFERRED_RECOGNITION'
  ---------------------------------------------------------------------------
  RETURN QUERY
  SELECT
    -- Map view je_type to canonical je_source label
    CASE v.je_type
      WHEN 'JE1_RECLASS'     THEN 'DEFERRED_RECLASS'
      WHEN 'JE2_DEFERRAL'    THEN 'DEFERRED_DEFERRAL'
      WHEN 'JE3_RECOGNITION' THEN 'DEFERRED_RECOGNITION'
      ELSE v.je_type   -- pass through any future types unchanged
    END::TEXT                                                   AS je_source,

    v.account::TEXT                                             AS account_code,

    -- account_name: use a human-readable label for known clearing accounts,
    -- otherwise fall back to the account code itself.
    CASE v.account
      WHEN '23000'           THEN 'Deferred Revenue'
      WHEN '44010'           THEN 'Support Revenue — InvoicedQB'
      WHEN '44020'           THEN 'Support Revenue — Reinstatement'
      WHEN '44030'           THEN 'Support Revenue — Autopay'
      WHEN '44040'           THEN 'Support Revenue — Other A'
      WHEN '44050'           THEN 'Support Revenue — Other B'
      WHEN 'SUPPORT_FEES_CLR' THEN 'Support Fees Clearing'
      ELSE v.account
    END::TEXT                                                   AS account_name,

    -- Debit / credit split based on side flag
    CASE WHEN v.side = 'DR' THEN v.amount ELSE 0::NUMERIC END  AS debit,
    CASE WHEN v.side = 'CR' THEN v.amount ELSE 0::NUMERIC END  AS credit,

    -- Descriptive memo
    (
      'Deferred maintenance ' || v.je_type
      || ' — '
      || p_year::TEXT || '-' || LPAD(p_month::TEXT, 2, '0')
    )::TEXT                                                     AS memo

  FROM finance.v_deferred_maint_close_je v
  WHERE v.month = make_date(p_year, p_month, 1);

  RETURN;
END;
$$;

COMMENT ON FUNCTION finance.derive_close_je(INTEGER, INTEGER) IS
  'Master close JE derivation function. Aggregates three JE segments for the '
  'given year/month: (1) DN000811 — SaaS/Relay AR+COGS true-up (7 lines); '
  '(2) DN000812 — SAM AP/COGS true-up (2 lines); '
  '(3) Deferred maintenance RECLASS, DEFERRAL, and RECOGNITION JEs from '
  'v_deferred_maint_close_je. Returns je_source, account_code, account_name, '
  'debit, credit, memo. Each je_source segment should balance (debits = credits). '
  'STABLE — safe to call multiple times in a transaction.';

-- =============================================================================
-- STEP 3: Validate — full output for Jan 2026
-- =============================================================================

SELECT
  je_source,
  account_code,
  account_name,
  debit,
  credit,
  memo
FROM finance.derive_close_je(2026, 1)
ORDER BY je_source, account_code;

-- =============================================================================
-- STEP 4: Balance check — each je_source must have debit = credit
-- =============================================================================

SELECT
  je_source,
  SUM(debit)            AS total_debit,
  SUM(credit)           AS total_credit,
  SUM(debit) - SUM(credit) AS imbalance,
  CASE
    WHEN ABS(SUM(debit) - SUM(credit)) < 0.005 THEN 'BALANCED'
    ELSE 'IMBALANCED *** INVESTIGATE'
  END                   AS balance_status
FROM finance.derive_close_je(2026, 1)
GROUP BY je_source
ORDER BY je_source;

-- =============================================================================
-- STEP 5: Line count check — confirm expected segment sizes
-- =============================================================================

SELECT
  je_source,
  COUNT(*)              AS line_count
FROM finance.derive_close_je(2026, 1)
GROUP BY je_source
ORDER BY je_source;

-- Expected minimum counts:
--   DN000811            -> 7 lines
--   DN000812            -> 2 lines
--   DEFERRED_RECLASS    -> >= 1 line  (JE1)
--   DEFERRED_DEFERRAL   -> >= 1 line  (JE2)
--   DEFERRED_RECOGNITION-> >= 1 line  (JE3)

-- =============================================================================
-- STEP 6: Smoke test for an adjacent month (Feb 2026)
-- =============================================================================

SELECT
  je_source,
  SUM(debit)            AS total_debit,
  SUM(credit)           AS total_credit,
  SUM(debit) - SUM(credit) AS imbalance
FROM finance.derive_close_je(2026, 2)
GROUP BY je_source
ORDER BY je_source;

-- =============================================================================
-- STEP 7: Register in meta.object_registry (if the registry exists)
-- =============================================================================

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema = 'meta'
      AND table_name   = 'object_registry'
  ) THEN
    INSERT INTO meta.object_registry (
      schema_name,
      object_name,
      object_type,
      description,
      created_at
    )
    VALUES (
      'finance',
      'derive_close_je',
      'function',
      'Master close JE derivation function. Calls derive_dn000811(), '
        'derive_dn000812(), and v_deferred_maint_close_je to produce a '
        'complete, balanced set of JE lines for a given year/month close. '
        'je_source labels: DN000811, DN000812, DEFERRED_RECLASS, '
        'DEFERRED_DEFERRAL, DEFERRED_RECOGNITION. '
        'Supports close checklist tasks 3.9, 3.12, 3.16, 3.17, 3.18.',
      NOW()
    )
    ON CONFLICT DO NOTHING;

    RAISE NOTICE 'Registered finance.derive_close_je in meta.object_registry';
  ELSE
    RAISE NOTICE 'meta.object_registry not found — skipping registration';
  END IF;
END;
$$;

-- =============================================================================
-- STEP 8: Final confirmation — function signature in pg_proc
-- =============================================================================

SELECT
  p.proname                           AS function_name,
  pg_get_function_arguments(p.oid)    AS arguments,
  pg_get_function_result(p.oid)       AS return_type,
  p.provolatile                       AS volatility  -- 's' = STABLE
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'finance'
  AND p.proname = 'derive_close_je';
