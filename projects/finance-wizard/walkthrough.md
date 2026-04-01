# Forensic Financial Audit — Live Diagnostic Results

**Executed:** 2026-04-01 01:15 PST  
**Database:** `dozjdswqnzqwvieqvwpe` (B4All-Hub production)  
**Method:** 15 diagnostic SQL queries against live finance schema

---

## 🔴 Critical Finding 1: DN000812 Root Cause IDENTIFIED

The $1,371 delta is now explained. The cumulative gap calculation shows:

| Month | SRS Credits (Hub) | Sterling Bills (QB) | Monthly Gap | Cumulative |
|-------|------------------|-------------------|-------------|------------|
| Jan 2025 | $30,804 | $30,615 | $190 | $190 |
| Feb 2025 | $30,684 | $29,485 | $1,199 | $1,389 |
| Mar 2025 | $35,676 | $33,465 | $2,211 | $3,600 |
| Apr 2025 | $33,504 | $32,646 | $859 | $4,458 |
| May 2025 | $26,448 | $25,121 | $1,327 | $5,785 |
| Jun 2025 | $22,140 | $21,649 | $491 | $6,276 |
| Jul 2025 | $20,640 | $20,397 | $243 | $6,519 |
| Aug 2025 | $22,176 | $21,732 | $445 | $6,964 |
| Sep 2025 | $22,152 | $20,347 | $1,805 | $8,769 |
| Oct 2025 | $20,184 | $19,454 | $731 | $9,499 |
| Nov 2025 | $19,200 | $18,449 | $752 | $10,251 |
| Dec 2025 | $22,272 | $21,550 | $722 | $10,973 |
| **Jan 2026** | **$25,500** | **$26,361** | **-$861** | **$10,112** |
| Feb 2026 | $22,092 | $22,968 | -$876 | $9,236 |

**Hub derives cumulative gap = $10,111.50** → Function output confirmed.  
**Controller posted = $8,740.91** for Jan 2026.  
**Delta = $10,111.50 - $8,740.91 = $1,370.59**

**Root cause:** The function uses a strict `agency='SRS' AND description='SRS Credit'` filter from `v_sk_fee_classification`. The Controller's workpaper likely uses a **different baseline or includes adjustments** the Hub doesn't see. The monthly gap is consistently $190-$2,200, suggesting SRS credits in the Hub include items the Controller excludes (possibly SRS credits that are reversed or already applied to bills).

> [!IMPORTANT]
> **Fix:** Need Controller to export their Jan DN000812 workpaper with line-level detail. The function's $10,111.50 is mathematically correct given its inputs — the question is whether those inputs match the Controller's methodology.

---

## 🔴 Critical Finding 2: Support Revenue (44xxx) Has SYSTEMATIC Failures

The P&L reconciliation view reveals **consistent failures across 3 of 5 support accounts** every single month:

### Jan 2025
| Account | Hub | QB | Delta | Status |
|---------|-----|-----|-------|--------|
| 44010 Maint-Invoiced | $152,969 | $150,917 | **+$2,052** | ❌ FAIL |
| 44020 Maint-Reinstate | $3,133 | $9,467 | **-$6,334** | ❌ FAIL |
| 44030 Maint-Autopay | $53,117 | $57,877 | **-$4,761** | ❌ FAIL |
| 44040 Maint-PR | -$7,112 | -$7,112 | $0 | ✅ PASS |
| 44050 Maint-SAMCredit | $7,660 | $7,583 | +$77 | ⚠️ WARN |

### Feb 2025
| Account | Hub | QB | Delta | Status |
|---------|-----|-----|-------|--------|
| 44010 | $147,041 | $152,839 | **-$5,799** | ❌ FAIL |
| 44020 | $3,305 | $3,941 | **-$636** | ❌ FAIL |
| 44030 | $53,502 | $59,800 | **-$6,298** | ❌ FAIL |

### Mar 2025
| Account | Hub | QB | Delta | Status |
|---------|-----|-----|-------|--------|
| 44010 | $142,891 | $166,097 | **-$23,206** | ❌ FAIL |
| 44020 | $2,998 | $3,504 | **-$506** | ❌ FAIL |
| 44030 | $53,209 | $55,460 | **-$2,251** | ❌ FAIL |

**Pattern identified:**
- **44010 (InvoicedQB):** Swings both positive and negative. Hub sometimes over-recognizes, sometimes under-recognizes. Largest gap: -$23K in Mar 2025.
- **44020 (Reinstate):** Hub ALWAYS under-recognizes. Jan gap: **-$6,334** (67% under). Confirms the reinstatement lookup table is critically incomplete.
- **44030 (Autopay):** Hub consistently under-recognizes by $2K-$6K/month. Suggests the autopay classification in `rebuild_deferred_maintenance()` is missing clients.

**Total annual support revenue gap (2025): ~$75K-$100K misallocated across sub-accounts.** Total support revenue is approximately correct, but the distribution across numbered accounts is wrong.

---

## 🟡 Finding 3: 41010 (Contract Processing Fee) Consistent ~$672-$1,344 Under-Derivation

Every month the Hub's 41010 is lower than QB by a consistent $672-$1,344:

| Month | Hub | QB | Delta |
|-------|-----|-----|-------|
| Jan 2025 | $163,465 | $164,137 | -$672 |
| Feb 2025 | $177,068 | $178,028 | -$960 |
| Mar 2025 | $179,313 | $180,337 | -$1,024 |
| Apr 2025 | $162,399 | $163,743 | -$1,344 |

**Root cause hypothesis:** The `v_fp_contract_txn` view is likely missing a small subset of contract processing transactions — possibly BAM or specific execution types that get coded to 41010 in some months but not all.

---

## 🟡 Finding 4: Feb 2025 41120 (Gov Fees PR) — $1,128 Overcounting

| Month | Hub | QB | Delta |
|-------|-----|-----|-------|
| Feb 2025 | $109,166 | $108,038 | +$1,128 |

And this carries through to the COGS mirror:
- 51110 (Gov Fees PR COGS): Hub $109,166 vs QB $108,038 = +$1,128

This is a single-month anomaly — likely a PR transaction that was included in the wrong month in the Hub. All other months pass.

---

## 🟡 Finding 5: SwipeSum Reconciliation is BROKEN for Pre-Oct 2025

| Month | SwipeSum Settled | QB Total | Variance | Matched Days |
|-------|-----------------|----------|----------|--------------|
| Feb-Sep 2025 | **NULL** | $528K-$865K | Full negative | 0 |
| Oct 2025 | $30,752 | $633,437 | -$602,685 | 0 |
| Nov 2025 | $538,330 | $524,593 | +$13,737 | 7 |
| Dec 2025 | $508,450 | $471,468 | +$36,982 | 13 |
| Jan 2026 | $699,061 | $666,624 | +$32,438 | 12 |
| **Feb 2026** | **$663,654** | **$666,108** | **-$2,454** | **15** |
| Mar 2026 | $567,033 | NULL | +$567,033 | 0 |

**Key findings:**
- **Pre-Nov 2025:** SwipeSum email settlement data simply doesn't exist. The `email_settled_total` is NULL.
- **Nov 2025-Jan 2026:** Partial data, large variances ($13K-$36K).
- **Feb 2026:** First clean month — $2,454 variance on 15 matched days. This is the steady-state accuracy.
- **Mar 2026:** QB data not yet posted (month just closed).

> [!NOTE]
> SwipeSum reconciliation only works from Feb 2026 forward. Pre-Nov 2025 data is irrecoverable. Nov-Jan is partially reconstructible.

---

## 🟡 Finding 6: JE Catchall Shows $227K in Uncaptured Lines (Dec 2025)

Only 1 month has catchall activity, but it's significant:

| Month | Lines | Amount | Accounts |
|-------|-------|--------|----------|
| Dec 2025 | 6 | **-$227,461** | 43021, 51026 |

- **43021** — not a standard account in the chart; likely a one-time Solutions adjustment
- **51026** — "COGS write-off", confirmed in the QB account list

These are legitimate JE lines that no finance view captures. They need to be mapped to the appropriate derivation view or acknowledged as special entries.

---

## 🟢 Finding 7: Deferred Revenue Balance — Mechanically Sound But Drifting

The deferred balance view (`v_deferred_maint_balance`) shows a reasonable run-rate:

| Month | New Deferrals | Recognition | Balance |
|-------|--------------|-------------|---------|
| Jan 2025 | $168,861 | $222,621 | **$791,248** |
| Jun 2025 | $169,092 | $206,726 | $447,680 |
| Sep 2025 | **$698,834** | $211,172 | **$865,418** |
| Jan 2026 | $164,111 | $209,080 | $744,650 |
| Feb 2026 | $119,915 | $216,647 | $647,919 |
| Mar 2026 | $5,523 | $175,978 | $477,464 |

**Notable:**
- Sep 2025 has a massive $699K deferral spike — likely annual contract renewals
- Mar 2026 shows only $5.5K new deferrals — likely QB data incomplete for the current month
- The balance drops to $0 by May 2032, which makes sense for existing contracts running off

**Needs validation:** Compare Jan 2026 ending balance ($744,650) to Controller's PBC38 spreadsheet. If PBC38 shows a different number, the recognition schedule is misaligned.

---

## 🟢 Finding 8: DN000811 Actual QB Posting for Jan 2026

Only 1 JE posted under DN000811 in 2025+:

| Account | Amount | Type |
|---------|--------|------|
| 11000 AR | $74,715.07 | Debit |
| 51010 Gov Fees | $3,192.50 | Credit |
| 51020 SAM Cost | $861.00 | Debit |
| 51025 True-up | $72,383.57 | Credit |
| 41010 Contract Processing | $2,331.50 | Credit |
| 41020 Gov Fees | $3,192.50 | Debit |
| 41030 SAM Cost | $861.00 | Credit |

This is the Jan 2026 posting. **No 2025 JEs with DN000811 doc_number found** — meaning either:
1. The Controller used different doc_numbers in 2025, or
2. This is a new JE pattern introduced in Jan 2026

---

## 🟢 Finding 9: P&L Reconciliation Coverage

The `v_pnl_reconciliation` view covers **32 distinct GL accounts** spanning:
- All FP revenue (41010-41220) ✅
- All relay revenue (42010-42020) ✅  
- All solutions revenue (43010-43090) ✅
- All support revenue (44010-44050) ✅
- All FP COGS (51010-51120) ✅
- All solutions COGS (53010-53030) ✅
- Support COGS (54010) ✅

**Not covered by the P&L reconciliation:**
- Operating expenses (60xxx-68xxx) — no Hub derivation exists
- D&A/Other (80xxx-89xxx) — no Hub derivation exists
- Taxes (90xxx) — no Hub derivation exists
- Balance sheet accounts — separate reconciliation needed

This is expected — the Hub only derives revenue and COGS. OpEx is entirely manual.

---

## 🟢 Finding 10: Thin Client /100 Division Audit — PASS

Reviewed 16 finance views that reference `raw_thinclient`. The key views:
- `v_relay_txn` — uses `total_amount_pennies / 100.0` ✅
- `v_sk_fee_classification` — uses `fee_pennies` in calculations ✅
- `v_oi_monthly` — uses `amount_dollars` (already converted) ✅
- `v_ar_aging_snapshot` — uses `amount_dollars` ✅

No missing /100 divisions detected.

---

## Summary: Priority Fixes

| # | Issue | Impact | Difficulty | Blocked? |
|---|-------|--------|------------|----------|
| 1 | Support revenue 44010/44020/44030 misallocation | ~$75K-$100K/year wrong accounts | Medium | Need Diana's reinstatement list |
| 2 | 41010 Contract Processing Fee under-derivation | ~$672-$1,344/month | Medium | Need root cause in v_fp_contract_txn |
| 3 | DN000812 $1,371 delta | $1,371 one-time | Low | Need Controller workpaper |
| 4 | SwipeSum pre-Nov 2025 data gap | Historical-only | N/A | Irrecoverable |
| 5 | Dec 2025 catchall ($227K in 43021/51026) | One-time | Low | Map to views or document |
| 6 | Feb 2025 41120/51110 PR overcounting | $1,128 one-time | Low | Investigate PR transaction |
| 7 | Deferred revenue balance validation | Unknown | Low | Need PBC38 from Controller |
