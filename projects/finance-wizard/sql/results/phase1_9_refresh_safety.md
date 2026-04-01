# Phase 1.9 — Transaction Safety Analysis: `finance.refresh_fact_revenue()`

**Date:** 2026-04-01
**Analyst:** Claude (Phase 1.9 automated review)
**Conclusion: The function is ALREADY transaction-safe. No code changes are required.**

---

## 1. Is the function transactional?

Yes. `finance.refresh_fact_revenue()` is a `LANGUAGE plpgsql` function. In PostgreSQL, a plpgsql function called without an explicit outer `BEGIN` runs inside an implicit single transaction that the engine manages. If any statement raises an exception, the entire transaction rolls back — including the TRUNCATE statements that ran earlier.

### Checked for transactionality breakers

| Pattern | Present? | Notes |
|---|---|---|
| `COMMIT` or `ROLLBACK` inside function body | **No** | None found in function definition |
| `SET` without `LOCAL` (session-level) | **No** | Only `SET LOCAL app.refresh_authorized = 'true'` is used |
| `PERFORM dblink(...)` or `postgres_fdw` writes | **No** | No cross-connection writes |
| `pg_background` or `pg_partman` async calls | **No** | None present |
| Autonomous transaction tricks | **No** | None present |

The only `SET` statement in the function is `SET LOCAL app.refresh_authorized = 'true'`. `SET LOCAL` is explicitly transaction-scoped — it is automatically reset when the transaction ends (commit or rollback). This is correct and safe.

---

## 2. Triggers on target tables

Two BEFORE ROW triggers exist on the target tables:

| Trigger | Table | Function |
|---|---|---|
| `trg_guard_fact_revenue` | `analytics.fact_revenue` | `analytics.guard_fact_write()` |
| `trg_guard_fact_cogs` | `analytics.fact_cogs` | `analytics.guard_fact_write()` |

Both triggers have `tgtype = 31` (binary `11111`):
- Bit 0 set: **FOR EACH ROW** (not STATEMENT-level)
- Bit 1 set: **BEFORE**
- Bits 2-4 set: fires on INSERT, DELETE, UPDATE

### Critical PostgreSQL behavior: TRUNCATE does not fire FOR EACH ROW triggers

`TRUNCATE` in PostgreSQL only fires `FOR EACH STATEMENT` triggers with event type `TRUNCATE`. It does **not** fire `FOR EACH ROW` triggers. Both guard triggers are `FOR EACH ROW`, so they are **not invoked by the TRUNCATE calls** in the function.

The guard triggers fire on the subsequent `INSERT INTO analytics.fact_revenue` and `INSERT INTO analytics.fact_cogs` rows. At that point, `SET LOCAL app.refresh_authorized = 'true'` has already been set, so `current_setting('app.refresh_authorized', true)` returns `'true'` and the guard passes.

### Guard trigger logic reviewed

```sql
-- analytics.guard_fact_write()
BEGIN
  IF current_setting('app.refresh_authorized', true) IS DISTINCT FROM 'true' THEN
    RAISE EXCEPTION 'Direct % on %.% blocked. Use the refresh function.',
      TG_OP, TG_TABLE_SCHEMA, TG_TABLE_NAME;
  END IF;
  IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END;
```

This trigger:
- Uses `current_setting(..., true)` — the second arg `true` means it returns NULL (not an error) if the setting is missing, which is correct defensive coding.
- Raises an exception if the session setting is not `'true'`, which would roll back the entire transaction — exactly the desired behavior for unauthorized writes.
- Does NOT contain any autonomous transaction logic, `COMMIT`, or session-level `SET` that could break transactionality.

---

## 3. RLS Policies

**No RLS policies exist on `analytics.fact_revenue` or `analytics.fact_cogs`.**

The `SET LOCAL app.refresh_authorized = 'true'` setting is consumed exclusively by the guard triggers, not by any RLS policy.

---

## 4. Overall Safety Assessment

### The original concern was unfounded

The implementation plan flagged that TRUNCATE + INSERT could leave tables empty on mid-execution failure. This is not the case because:

1. The function runs in a single implicit transaction.
2. There are no `COMMIT` statements or cross-connection writes that would break transactionality.
3. `SET LOCAL` is transaction-scoped and resets on rollback.
4. The `RAISE EXCEPTION` in the reasonableness checks causes the full transaction to roll back, restoring both tables to their pre-TRUNCATE state.
5. PostgreSQL's MVCC means concurrent readers see the old table data throughout the function's execution — they are not exposed to the empty-table state mid-refresh.

### Swap pattern: is it worth adding?

A staging-table swap pattern (INSERT into temp table → TRUNCATE → INSERT from temp) would reduce lock duration on `fact_revenue` and `fact_cogs` during the source query. However:

- The function already has strong reasonableness checks that prevent bad data from surviving. If the checks fail, the whole operation rolls back.
- The swap pattern adds meaningful complexity (temp table DDL, additional INSERT step, more code surface area to maintain).
- Lock duration concern is only relevant if the source view `finance.v_fact_revenue_source` is slow AND there are concurrent readers who cannot tolerate stale-read gaps. Given that matview refreshes are decoupled (handled by a separate cron), this is low risk.

**Recommendation: do not add the swap pattern.** The function is correct, safe, and the added complexity is not justified.

---

## 5. Decision

**No SQL changes needed for Phase 1.9.** The function is transaction-safe by construction.

The `sql/phase1/1_9_refresh_fact_revenue.sql` file is intentionally left empty (no-op) as evidence that this phase was reviewed and found to require no modification.
