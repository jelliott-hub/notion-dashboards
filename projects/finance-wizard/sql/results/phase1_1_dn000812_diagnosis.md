# DN000812 SAM AP True-Up Delta Diagnosis
**Date:** 2026-04-01  
**Database:** `dozjdswqnzqwvieqvwpe` (B4All-Hub)  
**Delta under investigation:** Hub derives $10,111.50 vs Controller posted $8,740.91 → gap = **$1,370.59**

---

## 1. Function Output — `finance.derive_dn000812(2026, 1)`

| account_code | account_name | debit | credit | memo |
|---|---|---|---|---|
| 51025 | 51025 - Residual FP Cost | 10,111.50 | — | SAM payable AP true-up: cumulative SRS-Sterling gap from Jan 2025 - Jan 2026 |
| 20000 | 20000 - Accounts Payable | — | 10,111.50 | SAM payable AP true-up: cumulative SRS-Sterling gap from Jan 2025 - Jan 2026 |

---

## 2. SRS Credits by Month from `finance.v_sk_fee_classification`
Filter: `agency = 'SRS' AND description = 'SRS Credit'`, Jan 2025 – Jan 2026

| Month | Total SRS Credits | Row Count |
|---|---|---|
| 2025-01 | 30,804.00 | 367 |
| 2025-02 | 30,684.00 | 380 |
| 2025-03 | 35,676.00 | 371 |
| 2025-04 | 33,504.00 | 355 |
| 2025-05 | 26,448.00 | 294 |
| 2025-06 | 22,140.00 | 306 |
| 2025-07 | 20,640.00 | 339 |
| 2025-08 | 22,176.00 | 380 |
| 2025-09 | 22,152.00 | 318 |
| 2025-10 | 20,184.00 | 288 |
| 2025-11 | 19,200.00 | 257 |
| 2025-12 | 22,272.00 | 255 |
| 2026-01 | 25,500.00 | 275 |
| **TOTAL** | **331,380.00** | **4,385** |

**Note:** Only ONE description exists for `agency = 'SRS'` — `'SRS Credit'` (classified as `sam_cost`). No other SRS-related description variants exist. There are separate `'Offset from Contract Credit and SRS Payment'` rows (classified as `srs_offset`, agency=`B4ALL`), but these are excluded by the function's filter and not relevant to the Sterling comparison.

---

## 3. Sterling Identity Bills by Month
Source: `raw_quickbooks.bill_lines JOIN raw_quickbooks.bills`, Jan 2025 – Jan 2026

| Month (txn_date) | Invoice # | Sterling Billed |
|---|---|---|
| 2025-01 | 10179197 | 30,614.50 |
| 2025-02 | 10216067 | 29,485.00 |
| 2025-03 | 10237322 | 33,465.00 |
| 2025-04 | 10283766 | 32,645.50 |
| 2025-05 | 10309715 | 25,121.00 |
| 2025-06 | 10344237 | 21,649.00 |
| 2025-07 | 10373536 | 20,397.00 |
| 2025-08 | INV 10419460 | 21,731.50 |
| 2025-09 | Inv 10450482 | 20,347.00 |
| 2025-10 | Inv 10481775 | 19,453.50 |
| 2025-11 | Inv 10512911 | 18,448.50 |
| 2025-12 | Inv 10542011 | 21,550.00 |
| 2026-01 | Inv 10572681 | 26,361.00 |
| **TOTAL** | | **321,268.50** |

All bills have `balance = 0.00` (fully paid). Bill totals match line sums exactly. One late payment fee of $4.54 exists (May 2024 — outside the period). No credit memos or adjustments for Sterling.

---

## 4. Month-by-Month Gap and Running Cumulative

| Month | SRS Credits | Sterling Billed | Monthly Gap | Cumulative Gap |
|---|---|---|---|---|
| 2025-01 | 30,804.00 | 30,614.50 | 189.50 | 189.50 |
| 2025-02 | 30,684.00 | 29,485.00 | 1,199.00 | 1,388.50 |
| 2025-03 | 35,676.00 | 33,465.00 | 2,211.00 | 3,599.50 |
| 2025-04 | 33,504.00 | 32,645.50 | 858.50 | 4,458.00 |
| 2025-05 | 26,448.00 | 25,121.00 | 1,327.00 | 5,785.00 |
| 2025-06 | 22,140.00 | 21,649.00 | 491.00 | 6,276.00 |
| 2025-07 | 20,640.00 | 20,397.00 | 243.00 | 6,519.00 |
| 2025-08 | 22,176.00 | 21,731.50 | 444.50 | 6,963.50 |
| **2025-09** | **22,152.00** | **20,347.00** | **1,805.00** | **8,768.50** |
| 2025-10 | 20,184.00 | 19,453.50 | 730.50 | 9,499.00 |
| 2025-11 | 19,200.00 | 18,448.50 | 751.50 | 10,250.50 |
| 2025-12 | 22,272.00 | 21,550.00 | 722.00 | 10,972.50 |
| 2026-01 | 25,500.00 | 26,361.00 | (861.00) | **10,111.50** |

The function's cumulative gap = **$10,111.50** is correct arithmetic for the Jan 2025 – Jan 2026 window.

---

## 5. Other SRS-Related Entries (Non-Matching Filter)

| Agency | Description | Classified As | Total $ (Jan 2025 – Jan 2026) |
|---|---|---|---|
| B4ALL | Offset from Contract Credit and SRS Payment | srs_offset | (94,921.34) |

These `srs_offset` entries are offset transactions on different contract codes. They are correctly excluded from the function's SRS-Sterling comparison because they represent contra-entries to customer billing adjustments, not SAM costs. They do not explain the delta.

---

## 6. Controller's Posted Entry for DN000812

| doc_number | txn_date | posting_type | amount | account_name |
|---|---|---|---|---|
| DN000812 | 2026-01-31 | Debit | 8,740.91 | 51025 - True-up of CMS AR to TC AR |
| DN000812 | 2026-01-31 | Credit | 8,740.91 | 20000 - Accounts Payable |

**Description:** "To true-up B4All SAM AP balance based on actual SAM costs payable"

There is only ONE DN000812 entry in the system, dated 2026-01-31. No prior DN000812 variants exist.

---

## 7. Prior SAM AP True-Up History (All Doc Numbers)

This is the critical finding. The controller has been posting SAM AP true-up entries throughout 2025 under DIFFERENT doc numbers:

| doc_number | txn_date | 51025 Posting | Amount | Net on AP |
|---|---|---|---|---|
| DN000316-2 | 2024-11-30 | — | 15,295.99 | AP Credit |
| DN000360-2 | 2024-12-31 | — | 578.94 | AP Credit |
| DN000360-2 | 2025-01-31 | Debit | 533.11 | AP Credit |
| DN000410-2 | 2025-02-28 | Debit | 40,757.62 | AP Credit |
| DN000420-2 | 2025-03-31 | Debit | 25,785.04 | AP Credit |
| DN000463-2 | 2025-04-30 | Credit | 10,753.11 | AP Debit |
| DN000509 | 2025-05-31 | Debit | 17,272.32 | AP Credit |
| DN000558 | 2025-06-30 | Credit | 7,256.67 | AP Debit |
| DN000603 | 2025-07-31 | Debit | 10,000.00 | AP Credit |
| DN000725 | 2025-09-30 | Credit | 20,860.92 | AP Debit |
| DN000726 | 2025-10-31 | Credit | 12,096.17 | AP Debit |
| DN000798 | 2025-12-31 | Debit | 20,673.48 | AP Credit |
| **DN000812** | **2026-01-31** | **Debit** | **8,740.91** | **AP Credit** |

The function's `v_prior_dn812` lookup filters `doc_number LIKE 'DN000812%'` — finding exactly **$0** in prior offsets. It completely misses all prior SAM AP postings under different doc numbers.

However, these prior entries (Feb 2025: $40,757; Mar 2025: $25,785; etc.) are far too large to represent only the SRS-Sterling gap. They clearly include OTHER SAM cost components beyond the Sterling fingerprinting gap. The function was designed as a standalone reconciliation of a specific sub-component (SRS credit vs Sterling billing), while the controller's broader SAM AP accrual includes multiple cost streams.

---

## 8. Month-Boundary Check: Dec 2025 / Jan 2026 Sterling Bills

| Invoice | txn_date | due_date | Amount | Balance |
|---|---|---|---|---|
| Inv 10542011 (Dec 2025) | 2025-12-31 | 2026-01-30 | 21,550.00 | 0.00 |
| Inv 10572681 (Jan 2026) | 2026-01-31 | 2026-03-02 | 26,361.00 | 0.00 |

No straddling issue: the function uses `txn_date < target_date + 1 month`, so it correctly includes both the Dec 2025 bill (txn_date 2025-12-31 < 2026-02-01) and the Jan 2026 bill (txn_date 2026-01-31 < 2026-02-01). Both are included in the $321,268.50 total.

---

## 9. Arithmetic Trace of the Function

```
v_baseline_date      = 2025-01-01
v_target_date        = 2026-01-01

v_cumulative_srs     = 331,380.00   (SRS Credit, Jan 2025 – Jan 2026)
v_cumulative_sterling= 321,268.50   (Sterling bills, Jan 2025 – Jan 31 2026)
v_cumulative_gap     = 10,111.50

v_prior_dn812        = 0.00         (filter: doc_number LIKE 'DN000812%' AND txn_date < 2026-01-01)
                                     Only existing DN000812 is txn_date 2026-01-31 → excluded)

v_amount             = 10,111.50 - 0.00 = 10,111.50

Controller posted     = 8,740.91
Delta                 = 1,370.59
```

---

## Root Cause Analysis

### Primary Root Cause: Controller Used a Stale/Different Date Window

The controller's $8,740.91 most closely matches the **cumulative SRS-Sterling gap through September 2025 = $8,768.50** (difference of only $27.59). No other plausible date window or filter variant produces a number close to $8,740.91:

| Scenario | Amount | Distance from $8,740.91 |
|---|---|---|
| Cumulative thru Sep 2025 | 8,768.50 | **27.59** |
| Cumulative thru May 2025 (excl. one month) | 8,784.50 | 43.59 |
| Cumulative thru Feb 2025 (excl. one month) | 8,912.50 | 171.59 |
| Cumulative thru Jan 2026 (function result) | 10,111.50 | 1,370.59 |
| Cumulative thru Dec 2025 | 10,972.50 | 2,231.59 |

The $27.59 residual between the Sep 2025 cumulative and the controller's number is most likely explained by the controller having pulled SRS data from an **earlier extract of the Sep 2025 SK report** — before some credits were finalized (or a minor rounding difference). This is not determinable without the controller's source spreadsheet.

### Secondary Issue: Function's Prior-Posting Logic Is Broken

The function subtracts only `doc_number LIKE 'DN000812%'` entries as prior offsets. This is too narrow:
- The first (and only) DN000812 posting is dated 2026-01-31, which falls OUTSIDE the `txn_date < 2026-01-01` filter, so `v_prior_dn812 = 0` for the Jan 2026 calculation.
- Even if the function were called for Feb 2026, it would find the $8,740.91 debit and only subtract that — ignoring the prior months' SAM AP entries under other doc numbers.
- However, this is a design choice: the function is computing the SRS-Sterling sub-component only, not the full SAM AP balance. The prior entries under other doc numbers appear to cover broader SAM costs beyond Sterling fingerprinting.

### Why the Delta Cannot Self-Resolve Without Intervention

The $1,370.59 delta represents months Oct–Dec 2025 and Jan 2026 SRS-Sterling gap that the controller's calculation did not capture (because their spreadsheet appears to have been last refreshed through Sep 2025 data). The Jan 2026 Sterling bill alone produced a **negative** monthly gap (-$861), meaning the function's total is actually lower than the Dec 2025 cumulative peak of $10,972.50.

---

## Conclusion: Root Cause and Fix

### Exact Root Cause
The controller computed DN000812 ($8,740.91) using a cumulative SRS-Sterling gap that was **cut off at approximately September 2025** (cumulative gap at that point: $8,768.50). The additional 9 months of data (Oct 2025 through Jan 2026) were not incorporated. The $27.59 remaining difference is consistent with a stale SK report extract for Sep 2025 used in the controller's spreadsheet.

The function `derive_dn000812(2026, 1)` correctly computes the Jan 2025–Jan 2026 cumulative gap at $10,111.50 using current database data.

### What Would Need to Change to Fix It

**Option A — Controller needs to revise DN000812 (blocked on Controller input):**  
The controller would need to post an adjusting entry for the $1,370.59 difference (additional Debit 51025 / Credit AP 20000), acknowledging that their Sep 2025 cutoff understated the cumulative gap. This requires the controller to agree that the function's methodology (Jan 2025 baseline, inclusive through Jan 2026) is correct.

**Option B — Function methodology needs adjustment (if controller's window is "right"):**  
If the business decision is that the SAM AP true-up should only cover Jan 2025–Sep 2025 (e.g., because Oct 2025 onward was handled via a different tracking mechanism), the function's `v_target_date` approach would need a hard cutoff or a configurable baseline-end date. This would require explicit sign-off on what period the SAM AP accrual covers.

**Option C — Reconcile the function's prior-offset logic:**  
The function could be updated to subtract ALL prior SAM AP true-up postings (not just `DN000812%` entries), but this would require identifying which prior entries are SRS-Sterling-specific vs. other SAM cost components — information that lives only in the controller's spreadsheet.

**Bottom line:** The delta is **blocked on Controller input**. The controller must either (a) confirm their Sep 2025 cutoff was intentional and the remaining gap is being tracked separately, or (b) post an adjusting entry for $1,370.59. The function's arithmetic is correct given its Jan 2025–Jan 2026 window; the controller's source data appears to be stale by ~4 months.
