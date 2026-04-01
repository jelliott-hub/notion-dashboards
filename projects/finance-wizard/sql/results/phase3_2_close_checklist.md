# Phase 3.2: finance.close_checklist

**Date:** 2026-04-01
**Database:** B4All-Hub (`dozjdswqnzqwvieqvwpe`)
**SQL file:** `sql/phase3/3_2_close_checklist.sql`

---

## Status: COMPLETE

All steps executed successfully.

---

## What Was Built

### Table: `finance.close_checklist`

Tracks each month-end close task with full lifecycle metadata.

| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL PK | Auto-increment |
| `close_year` | INTEGER | Template = 0 |
| `close_month` | INTEGER | Template = 0 |
| `phase` | INTEGER | 1–5 |
| `task_number` | TEXT | e.g. `3.9`, `2.1` |
| `task_name` | TEXT | Short label |
| `description` | TEXT | Expanded detail |
| `owner` | TEXT | bookkeeper / controller / manager / system |
| `status` | TEXT | pending / in_progress / completed / blocked / skipped |
| `hub_surface` | TEXT | View or function that supports the task |
| `automated` | BOOLEAN | Whether the Hub can execute it automatically |
| `started_at` | TIMESTAMPTZ | |
| `completed_at` | TIMESTAMPTZ | |
| `completed_by` | TEXT | |
| `notes` | TEXT | |
| `blocked_by` | TEXT[] | Array of task_numbers that must complete first |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

**Unique constraint:** `(close_year, close_month, task_number)`
**Index:** `idx_close_checklist_period_status` on `(close_year, close_month, status)`

---

### Template Rows (year=0, month=0)

43 tasks seeded as the canonical template:

| Phase | Task Count | Automated | Has Hub Surface |
|---|---|---|---|
| 1 — Pre-close | 4 | 0 | 0 |
| 2 — Bookkeeper | 11 | 0 | 0 |
| 3 — Controller | 24 | 18 | 19 |
| 4 — Review | 2 | 0 | 0 |
| 5 — Finalization | 2 | 0 | 0 |
| **Total** | **43** | **18** | **19** |

Phase 3 has the highest automation coverage — 18 of 24 controller tasks have a hub surface (view or function) and are flagged `automated = TRUE`.

---

### Function: `finance.init_close_checklist(p_year INTEGER, p_month INTEGER)`

Copies all template rows (year=0, month=0) into a live checklist for the given year/month. Returns the number of rows inserted. Idempotent — safe to call multiple times due to `ON CONFLICT DO NOTHING`.

**Usage note:** The `run_sql.py` script only commits when there's no result set. Call via a DO block to guarantee commit:

```sql
DO $$ BEGIN PERFORM finance.init_close_checklist(2026, 3); END; $$;
```

**Test result:** `init_close_checklist(2026, 3)` inserted 43 rows for March 2026.

---

### meta.object_registry

Both objects registered in `meta.object_registry` under domain `close-engine`, status `active`, created_by `claude`:

| ID | Type | Object Name |
|---|---|---|
| 13043 | table | `finance.close_checklist` |
| 13048 | function | `finance.init_close_checklist` |

---

## Key Design Decisions

1. **Template pattern (year=0, month=0):** Rather than a separate template table, the main table stores templates as a sentinel period. This keeps the schema simple and makes `init_close_checklist()` a trivial INSERT...SELECT.

2. **`blocked_by TEXT[]`:** Dependencies are stored as an array of task_number strings. This allows the application/Hub to compute ready-to-start tasks by checking whether all blocking tasks have `status = 'completed'`, without requiring a separate dependency join table.

3. **`automated` flag:** Marks which tasks the Hub can execute autonomously (e.g., calling `derive_dn000811()`). Phase 3 has 18 automatable tasks — the majority of controller work.

4. **`hub_surface` column:** Free-text reference to the view or function supporting the task. Allows traceability between checklist tasks and finance schema objects.

---

## Dependency Chain Highlights

```
Phase 1 (1.1-1.4)
    └── Phase 2 (2.1-2.14): all block on Phase 1 completion
         └── Phase 3 entry (3.4): blocks on all Phase 2 tasks
              └── 3.4 → 3.5 → 3.6 → 3.7 → 3.8
                   └── 3.9 (DN000811) → 3.10 → 3.11 → 3.12
                        └── 3.13 → 3.15 → 3.16 → 3.17 → 3.18
                             └── 3.19 → 3.20 → 3.23 → 3.24
                                  └── 3.26 → 3.27 → 3.28
                                       └── 3.30 → 3.33 → 3.34
                                            └── Phase 4 (4.1 → 4.2)
                                                 └── Phase 5 (5.1 → 5.2)
```
