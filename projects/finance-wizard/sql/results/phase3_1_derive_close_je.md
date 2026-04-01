# Phase 3.1: `finance.derive_close_je(p_year, p_month)`

**Created:** 2026-04-01
**Status:** SQL WRITTEN — pending live execution against B4All-Hub (`dozjdswqnzqwvieqvwpe`)
**SQL file:** `/Users/jackelliott/commandcenter/projects/finance-wizard/sql/phase3/3_1_derive_close_je.sql`
**Supports:** Close checklist tasks 3.9, 3.12, 3.16, 3.17, 3.18

---

## Purpose

`finance.derive_close_je` is the **master close JE derivation function**. It aggregates three JE segments into a single, consistently formatted result set for a given month-end, which the Controller posts to QuickBooks after review.

| Segment | `je_source` label | Source | Accounts | Lines |
|---|---|---|---|---|
| SaaS/Relay AR+COGS true-up | `DN000811` | `finance.derive_dn000811()` | 11000, 41010, 41020, 41030, 51010, 51020, 51025 | 7 |
| SAM AP/COGS true-up | `DN000812` | `finance.derive_dn000812()` | 51025, 20000 | 2 |
| Deferred maint reclass | `DEFERRED_RECLASS` | `v_deferred_maint_close_je` WHERE `je_type = 'JE1_RECLASS'` | 23000, 44010–44050, SUPPORT_FEES_CLR | varies |
| Deferred maint deferral | `DEFERRED_DEFERRAL` | `v_deferred_maint_close_je` WHERE `je_type = 'JE2_DEFERRAL'` | 23000, 44010–44050, SUPPORT_FEES_CLR | varies |
| Deferred maint recognition | `DEFERRED_RECOGNITION` | `v_deferred_maint_close_je` WHERE `je_type = 'JE3_RECOGNITION'` | 23000, 44010–44050, SUPPORT_FEES_CLR | varies |

---

## Function Signature

```sql
finance.derive_close_je(p_year INTEGER, p_month INTEGER)
RETURNS TABLE(
  je_source    TEXT,
  account_code TEXT,
  account_name TEXT,
  debit        NUMERIC,
  credit       NUMERIC,
  memo         TEXT
)
LANGUAGE plpgsql STABLE
```

---

## Design Decisions

### 1. `je_source` labels vs. raw `je_type`

`v_deferred_maint_close_je.je_type` uses the raw view names (`JE1_RECLASS`, `JE2_DEFERRAL`, `JE3_RECOGNITION`). The function maps these to the canonical `je_source` namespace (`DEFERRED_RECLASS`, `DEFERRED_DEFERRAL`, `DEFERRED_RECOGNITION`) so all five labels are human-readable and consistent across the Hub surface. Any future `je_type` values not in the map are passed through unchanged to avoid silent data loss.

### 2. `account_name` for deferred maintenance lines

The view's `account` column contains either a GL code string (e.g. `'23000'`, `'44010'`) or a logical name (`'SUPPORT_FEES_CLR'`). Since there is no join target for a name lookup at this point, the function applies a `CASE` lookup for known codes and falls back to the raw account value. This produces readable output without a schema dependency on an account master table.

### 3. `STABLE` volatility

All three underlying sources are read-only views/functions over `finance` tables that do not mutate state. `STABLE` (vs. `VOLATILE`) allows PostgreSQL to cache calls within a single query execution and permits use inside other `STABLE` functions or index expressions.

### 4. Balance invariant

Each `je_source` segment is expected to balance independently (total debit = total credit). This is validated in Step 4 of the SQL file. An imbalanced segment would indicate a bug in the upstream function or view.

### 5. `make_date(p_year, p_month, 1)` for the month filter

`v_deferred_maint_close_je.month` is a `date` column stored as the first of the month. Using `make_date()` is cleaner than string concatenation and avoids locale-dependent formatting issues.

---

## Expected Output — Jan 2026

### Step 3: Full output (ordered by je_source, account_code)

| je_source | account_code | account_name | debit | credit | memo |
|---|---|---|---|---|---|
| DEFERRED_DEFERRAL | 23000 | Deferred Revenue | ... | ... | Deferred maintenance JE2_DEFERRAL — 2026-01 |
| DEFERRED_DEFERRAL | 44010–44050 | Support Revenue — ... | ... | ... | Deferred maintenance JE2_DEFERRAL — 2026-01 |
| DEFERRED_DEFERRAL | SUPPORT_FEES_CLR | Support Fees Clearing | ... | ... | Deferred maintenance JE2_DEFERRAL — 2026-01 |
| DEFERRED_RECLASS | ... | ... | ... | ... | Deferred maintenance JE1_RECLASS — 2026-01 |
| DEFERRED_RECOGNITION | ... | ... | ... | ... | Deferred maintenance JE3_RECOGNITION — 2026-01 |
| DN000811 | 11000 | ... | ... | ... | ... |
| DN000811 | 41010 | ... | ... | ... | ... |
| DN000811 | 41020 | ... | ... | ... | ... |
| DN000811 | 41030 | ... | ... | ... | ... |
| DN000811 | 51010 | ... | ... | ... | ... |
| DN000811 | 51020 | ... | ... | ... | ... |
| DN000811 | 51025 | ... | ... | ... | ... |
| DN000812 | 20000 | ... | ... | ... | ... |
| DN000812 | 51025 | ... | ... | ... | ... |

*Exact amounts populated after live execution.*

### Step 4: Balance check (expected result)

| je_source | total_debit | total_credit | imbalance | balance_status |
|---|---|---|---|---|
| DEFERRED_DEFERRAL | X.XX | X.XX | 0.00 | BALANCED |
| DEFERRED_RECLASS | X.XX | X.XX | 0.00 | BALANCED |
| DEFERRED_RECOGNITION | X.XX | X.XX | 0.00 | BALANCED |
| DN000811 | X.XX | X.XX | 0.00 | BALANCED |
| DN000812 | X.XX | X.XX | 0.00 | BALANCED |

*All segments must show `BALANCED`. Any `IMBALANCED` result requires investigation of the upstream function/view.*

### Step 5: Line counts (expected minimums)

| je_source | line_count |
|---|---|
| DN000811 | 7 |
| DN000812 | 2 |
| DEFERRED_RECLASS | >= 1 |
| DEFERRED_DEFERRAL | >= 1 |
| DEFERRED_RECOGNITION | >= 1 |

---

## Dependency Map

```
finance.derive_close_je(year, month)
  ├── finance.derive_dn000811(year, month)      [Phase 1.x — must pre-exist]
  ├── finance.derive_dn000812(year, month)      [Phase 1.x — must pre-exist]
  └── finance.v_deferred_maint_close_je         [Phase 1.x — must pre-exist]
       ├── je_type = 'JE1_RECLASS'   -> DEFERRED_RECLASS
       ├── je_type = 'JE2_DEFERRAL'  -> DEFERRED_DEFERRAL
       └── je_type = 'JE3_RECOGNITION' -> DEFERRED_RECOGNITION
```

---

## Close Checklist Integration

| Task | What | Hub surface |
|---|---|---|
| 3.9 | SaaS/Relay true-up | `derive_close_je()` filtered to `je_source = 'DN000811'` |
| 3.12 | SAM cost true-up | `derive_close_je()` filtered to `je_source = 'DN000812'` |
| 3.16 | Auto Maintenance reclass | `derive_close_je()` filtered to `je_source = 'DEFERRED_RECLASS'` |
| 3.17 | Support reclass to deferred revenue | `derive_close_je()` filtered to `je_source = 'DEFERRED_DEFERRAL'` |
| 3.18 | Support amortization | `derive_close_je()` filtered to `je_source = 'DEFERRED_RECOGNITION'` |

The Controller can run one call to get the full close JE package, or filter by `je_source` to produce individual JEs for sequential posting.

---

## Usage Examples

```sql
-- Full close JE package for January 2026
SELECT * FROM finance.derive_close_je(2026, 1)
ORDER BY je_source, account_code;

-- Just the DN000811 JE (SaaS/Relay true-up)
SELECT account_code, account_name, debit, credit, memo
FROM finance.derive_close_je(2026, 1)
WHERE je_source = 'DN000811';

-- Balance verification (run before posting)
SELECT je_source,
       SUM(debit)              AS total_debit,
       SUM(credit)             AS total_credit,
       SUM(debit) - SUM(credit) AS imbalance
FROM finance.derive_close_je(2026, 1)
GROUP BY je_source
ORDER BY je_source;

-- Grand total across all segments
SELECT SUM(debit) AS grand_debit, SUM(credit) AS grand_credit,
       SUM(debit) - SUM(credit) AS grand_imbalance
FROM finance.derive_close_je(2026, 1);
```

---

## meta.object_registry

Step 7 of the SQL file registers `finance.derive_close_je` in `meta.object_registry` if that table exists. The DO block is idempotent (`ON CONFLICT DO NOTHING`) and emits a `RAISE NOTICE` confirming registration or skipping gracefully.

---

## Next Steps

1. Execute `3_1_derive_close_je.sql` against B4All-Hub using:
   ```
   /tmp/xlenv/bin/python /tmp/run_sql.py "$(cat sql/phase3/3_1_derive_close_je.sql)"
   ```
   Or run each step individually against `$SUPABASE_DB_URL`.
2. Record actual balance check output (Step 4) in this file.
3. If any `je_source` shows `IMBALANCED`, trace back to the upstream function and fix before posting.
4. Confirm `meta.object_registry` registration (`RAISE NOTICE` output).
5. Use this function as the data source for Phase 3.3 (close JE posting workflow) if planned.
