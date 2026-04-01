-- =============================================================================
-- Phase 3.4: finance.validate_close(year, month)
-- Automated close quality gate — runs all proof views and returns a
-- structured pass/fail report with variance amounts.
-- =============================================================================

CREATE OR REPLACE FUNCTION finance.validate_close(p_year INTEGER, p_month INTEGER)
RETURNS TABLE(
  check_name       TEXT,
  check_category   TEXT,   -- 'pnl', 'cash', 'ar', 'deferred', 'catchall', 'summary'
  status           TEXT,   -- 'PASS', 'WARN', 'FAIL'
  detail           TEXT,
  variance_amount  NUMERIC
) AS $$
DECLARE
  v_period_start   DATE;
  v_period_end     DATE;
  v_report_month   DATE;

  -- counters for summary
  v_fail_count     INTEGER := 0;
  v_warn_count     INTEGER := 0;
  v_pass_count     INTEGER := 0;

  -- intermediate record holders
  r_pnl            RECORD;
  r_clearing       RECORD;
  r_ar             RECORD;
  r_catchall       RECORD;
  r_deferred       RECORD;
  r_ach            RECORD;
  r_paypal         RECORD;
  r_swipesum       RECORD;
BEGIN
  -- Normalise the target period
  v_period_start := DATE_TRUNC('month', make_date(p_year, p_month, 1))::DATE;
  v_period_end   := (v_period_start + INTERVAL '1 month')::DATE;
  v_report_month := v_period_start;   -- alias used by views that call it report_month

  -- =========================================================================
  -- A. P&L RECONCILIATION  (one row per GL account)
  -- =========================================================================
  FOR r_pnl IN
    SELECT
      gl_code,
      gl_name,
      hub_total,
      qb_total,
      delta,
      status AS pnl_status
    FROM finance.v_pnl_reconciliation
    WHERE period_start = v_period_start
    ORDER BY gl_code
  LOOP
    check_name      := 'PnL: ' || r_pnl.gl_code || ' - ' || r_pnl.gl_name;
    check_category  := 'pnl';
    status          := r_pnl.pnl_status;           -- view already emits PASS/WARN/FAIL
    detail          := 'Hub=' || COALESCE(r_pnl.hub_total::TEXT,'NULL')
                       || '  QB=' || COALESCE(r_pnl.qb_total::TEXT,'NULL')
                       || '  delta=' || COALESCE(r_pnl.delta::TEXT,'NULL');
    variance_amount := r_pnl.delta;

    IF r_pnl.pnl_status = 'FAIL' THEN v_fail_count := v_fail_count + 1;
    ELSIF r_pnl.pnl_status = 'WARN' THEN v_warn_count := v_warn_count + 1;
    ELSE v_pass_count := v_pass_count + 1;
    END IF;

    RETURN NEXT;
  END LOOP;

  -- =========================================================================
  -- B. CLEARING ACCOUNT BALANCES
  -- =========================================================================
  FOR r_clearing IN
    SELECT
      account_name,
      account_type,
      ending_balance,
      net_activity,
      status AS clr_status
    FROM finance.v_clearing_account_balance
    WHERE report_month = v_report_month
    ORDER BY account_name
  LOOP
    -- Clearing accounts should be zero-balanced at close; OPEN means still
    -- has a balance — treat as WARN (informational; may close next period)
    check_name      := 'Clearing: ' || r_clearing.account_name;
    check_category  := 'cash';
    status          := CASE r_clearing.clr_status
                         WHEN 'OPEN' THEN 'WARN'
                         ELSE 'PASS'
                       END;
    detail          := 'ending_balance=' || COALESCE(r_clearing.ending_balance::TEXT,'NULL')
                       || '  net_activity=' || COALESCE(r_clearing.net_activity::TEXT,'NULL')
                       || '  view_status=' || COALESCE(r_clearing.clr_status,'NULL');
    variance_amount := r_clearing.ending_balance;

    IF status = 'FAIL' THEN v_fail_count := v_fail_count + 1;
    ELSIF status = 'WARN' THEN v_warn_count := v_warn_count + 1;
    ELSE v_pass_count := v_pass_count + 1;
    END IF;

    RETURN NEXT;
  END LOOP;

  -- =========================================================================
  -- C. ACH RECONCILIATION
  -- =========================================================================
  SELECT *
  INTO r_ach
  FROM finance.v_ach_reconciliation_monthly
  WHERE month = v_period_start;

  IF r_ach IS NULL THEN
    check_name      := 'Cash: ACH reconciliation';
    check_category  := 'cash';
    status          := 'WARN';
    detail          := 'No ACH data for period';
    variance_amount := NULL;
    v_warn_count    := v_warn_count + 1;
    RETURN NEXT;
  ELSE
    check_name      := 'Cash: ACH reconciliation';
    check_category  := 'cash';
    -- deposit_variance = 0 and no discrepancy_days → PASS; otherwise WARN/FAIL
    status := CASE
                WHEN r_ach.deposit_variance = 0 AND r_ach.deposit_discrepancy_days = 0
                     THEN 'PASS'
                WHEN ABS(r_ach.deposit_variance) <= 500
                     THEN 'WARN'
                ELSE 'FAIL'
              END;
    detail          := 'bank=' || COALESCE(r_ach.total_ach_bank::TEXT,'NULL')
                       || '  qb_deposits=' || COALESCE(r_ach.total_qb_deposits::TEXT,'NULL')
                       || '  deposit_variance=' || COALESCE(r_ach.deposit_variance::TEXT,'NULL')
                       || '  discrepancy_days=' || COALESCE(r_ach.deposit_discrepancy_days::TEXT,'NULL');
    variance_amount := r_ach.deposit_variance;

    IF status = 'FAIL' THEN v_fail_count := v_fail_count + 1;
    ELSIF status = 'WARN' THEN v_warn_count := v_warn_count + 1;
    ELSE v_pass_count := v_pass_count + 1;
    END IF;
    RETURN NEXT;
  END IF;

  -- =========================================================================
  -- D. PAYPAL RECONCILIATION
  -- =========================================================================
  SELECT *
  INTO r_paypal
  FROM finance.v_paypal_reconciliation_monthly
  WHERE month = v_period_start;

  IF r_paypal IS NULL THEN
    check_name      := 'Cash: PayPal reconciliation';
    check_category  := 'cash';
    status          := 'WARN';
    detail          := 'No PayPal data for period';
    variance_amount := NULL;
    v_warn_count    := v_warn_count + 1;
    RETURN NEXT;
  ELSE
    check_name      := 'Cash: PayPal reconciliation';
    check_category  := 'cash';
    -- Use the view's own status field (PASS / INVESTIGATE / etc.)
    status := CASE r_paypal.status
                WHEN 'PASS' THEN 'PASS'
                WHEN 'INVESTIGATE' THEN 'WARN'
                ELSE 'FAIL'
              END;
    detail          := 'email_gross=' || COALESCE(r_paypal.email_gross::TEXT,'NULL')
                       || '  qb_net_deposits=' || COALESCE(r_paypal.qb_net_deposits::TEXT,'NULL')
                       || '  residual_variance=' || COALESCE(r_paypal.residual_variance::TEXT,'NULL')
                       || '  view_status=' || COALESCE(r_paypal.status,'NULL');
    variance_amount := r_paypal.residual_variance;

    IF status = 'FAIL' THEN v_fail_count := v_fail_count + 1;
    ELSIF status = 'WARN' THEN v_warn_count := v_warn_count + 1;
    ELSE v_pass_count := v_pass_count + 1;
    END IF;
    RETURN NEXT;
  END IF;

  -- =========================================================================
  -- E. SWIPESUM RECONCILIATION
  -- =========================================================================
  SELECT *
  INTO r_swipesum
  FROM finance.v_swipesum_reconciliation_monthly
  WHERE month = v_period_start;

  IF r_swipesum IS NULL THEN
    check_name      := 'Cash: SwipeSum reconciliation';
    check_category  := 'cash';
    status          := 'WARN';
    detail          := 'No SwipeSum data for period';
    variance_amount := NULL;
    v_warn_count    := v_warn_count + 1;
    RETURN NEXT;
  ELSE
    check_name      := 'Cash: SwipeSum reconciliation';
    check_category  := 'cash';
    -- SwipeSum view has no status column; derive from variance
    status := CASE
                WHEN r_swipesum.variance = 0                  THEN 'PASS'
                WHEN ABS(r_swipesum.variance) <= 1000          THEN 'WARN'
                ELSE 'FAIL'
              END;
    detail          := 'email_settled=' || COALESCE(r_swipesum.email_settled_total::TEXT,'NULL')
                       || '  qb_total=' || COALESCE(r_swipesum.qb_total::TEXT,'NULL')
                       || '  variance=' || COALESCE(r_swipesum.variance::TEXT,'NULL')
                       || '  discrepancy_days=' || COALESCE(r_swipesum.discrepancy_days::TEXT,'NULL');
    variance_amount := r_swipesum.variance;

    IF status = 'FAIL' THEN v_fail_count := v_fail_count + 1;
    ELSIF status = 'WARN' THEN v_warn_count := v_warn_count + 1;
    ELSE v_pass_count := v_pass_count + 1;
    END IF;
    RETURN NEXT;
  END IF;

  -- =========================================================================
  -- F. AR / OPEN INVOICES RECONCILIATION
  -- =========================================================================
  SELECT *
  INTO r_ar
  FROM finance.v_ar_oi_reconciliation
  WHERE report_month = v_report_month;

  IF r_ar IS NULL THEN
    check_name      := 'AR: QB vs OI reconciliation';
    check_category  := 'ar';
    status          := 'WARN';
    detail          := 'No AR data for period';
    variance_amount := NULL;
    v_warn_count    := v_warn_count + 1;
    RETURN NEXT;
  ELSE
    check_name      := 'AR: QB vs OI reconciliation';
    check_category  := 'ar';
    status          := CASE r_ar.recon_status
                         WHEN 'PASS' THEN 'PASS'
                         WHEN 'WARN' THEN 'WARN'
                         ELSE 'FAIL'
                       END;
    detail          := 'qb_ar=' || COALESCE(r_ar.qb_ar_total::TEXT,'NULL')
                       || '  tc_oi_ar=' || COALESCE(r_ar.tc_oi_ar::TEXT,'NULL')
                       || '  delta=' || COALESCE(r_ar.delta::TEXT,'NULL')
                       || '  pct_delta=' || COALESCE(r_ar.pct_delta::TEXT,'NULL') || '%';
    variance_amount := r_ar.delta;

    IF status = 'FAIL' THEN v_fail_count := v_fail_count + 1;
    ELSIF status = 'WARN' THEN v_warn_count := v_warn_count + 1;
    ELSE v_pass_count := v_pass_count + 1;
    END IF;
    RETURN NEXT;
  END IF;

  -- =========================================================================
  -- G. CATCHALL MONITOR
  -- =========================================================================
  SELECT *
  INTO r_catchall
  FROM finance.v_catchall_monitor
  WHERE report_month = v_report_month;

  IF r_catchall IS NULL THEN
    -- No catchall rows = nothing unclassified → PASS
    check_name      := 'Catchall: unclassified transactions';
    check_category  := 'catchall';
    status          := 'PASS';
    detail          := 'No unclassified activity in period';
    variance_amount := 0;
    v_pass_count    := v_pass_count + 1;
    RETURN NEXT;
  ELSE
    check_name      := 'Catchall: unclassified transactions';
    check_category  := 'catchall';
    status          := CASE r_catchall.status
                         WHEN 'OK'    THEN 'PASS'
                         WHEN 'ALERT' THEN 'FAIL'
                         ELSE 'WARN'
                       END;
    detail          := 'uncaptured_total=' || COALESCE(r_catchall.uncaptured_total::TEXT,'NULL')
                       || '  line_count=' || COALESCE(r_catchall.uncaptured_line_count::TEXT,'NULL')
                       || '  mom_change=' || COALESCE(r_catchall.mom_change::TEXT,'NULL')
                       || '  view_status=' || COALESCE(r_catchall.status,'NULL');
    variance_amount := r_catchall.uncaptured_total;

    IF status = 'FAIL' THEN v_fail_count := v_fail_count + 1;
    ELSIF status = 'WARN' THEN v_warn_count := v_warn_count + 1;
    ELSE v_pass_count := v_pass_count + 1;
    END IF;
    RETURN NEXT;
  END IF;

  -- =========================================================================
  -- H. DEFERRED REVENUE BALANCE
  --    The view covers future recognition; we look for the month that
  --    represents the balance *as of* the close month (opening balance of
  --    the following month = ending balance of close month).
  -- =========================================================================
  SELECT *
  INTO r_deferred
  FROM finance.v_deferred_maint_balance
  WHERE month = v_period_start;

  IF r_deferred IS NULL THEN
    check_name      := 'Deferred: maintenance revenue balance';
    check_category  := 'deferred';
    status          := 'WARN';
    detail          := 'No deferred revenue entry found for period';
    variance_amount := NULL;
    v_warn_count    := v_warn_count + 1;
    RETURN NEXT;
  ELSE
    check_name      := 'Deferred: maintenance revenue balance';
    check_category  := 'deferred';
    status := CASE
                WHEN r_deferred.deferred_balance_23000 > 0  THEN 'PASS'
                WHEN r_deferred.deferred_balance_23000 = 0  THEN 'WARN'
                ELSE 'FAIL'   -- negative deferred balance is an error
              END;
    detail          := 'deferred_balance_23000=' || COALESCE(r_deferred.deferred_balance_23000::TEXT,'NULL')
                       || '  new_deferrals=' || COALESCE(r_deferred.new_deferrals::TEXT,'NULL')
                       || '  recognition=' || COALESCE(r_deferred.recognition::TEXT,'NULL')
                       || '  net_change=' || COALESCE(r_deferred.net_change::TEXT,'NULL');
    variance_amount := r_deferred.deferred_balance_23000;

    IF status = 'FAIL' THEN v_fail_count := v_fail_count + 1;
    ELSIF status = 'WARN' THEN v_warn_count := v_warn_count + 1;
    ELSE v_pass_count := v_pass_count + 1;
    END IF;
    RETURN NEXT;
  END IF;

  -- =========================================================================
  -- Z. SUMMARY ROW
  -- =========================================================================
  check_name      := 'OVERALL CLOSE STATUS';
  check_category  := 'summary';
  status          := CASE
                       WHEN v_fail_count > 0  THEN 'FAIL'
                       WHEN v_warn_count > 0  THEN 'WARN'
                       ELSE 'PASS'
                     END;
  detail          := 'pass=' || v_pass_count
                     || '  warn=' || v_warn_count
                     || '  fail=' || v_fail_count
                     || '  period=' || TO_CHAR(v_period_start, 'YYYY-MM');
  variance_amount := v_fail_count;   -- number of FAILs is the key signal

  RETURN NEXT;

END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION finance.validate_close(INTEGER, INTEGER) IS
  'Quality gate for month-end close. Runs all proof views and returns a '
  'structured pass/fail report. Call as: SELECT * FROM finance.validate_close(2026, 1);';
