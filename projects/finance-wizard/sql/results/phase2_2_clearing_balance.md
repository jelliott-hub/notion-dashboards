# Phase 2.2: finance.v_clearing_account_balance — Findings

**Run date:** 2026-04-01
**View created:** `finance.v_clearing_account_balance`
**SQL file:** `sql/phase2/2_2_clearing_balance.sql`

---

## View Design

The view covers two distinct categories of clearing accounts:

| Category | Accounts | Balance Logic |
|---|---|---|
| `PL_PARENT` | SaaS Platform:FP Services, SaaS Platform COGS:FP Svcs Cost, Support Fees, Solutions, Solutions COGS | Monthly net only (P&L resets — opening_balance = 0) |
| `BS_CLEARING` | 10090 - PayPal - Clearing, 11100 - Undeposited Funds | Cumulative running balance (prior months carry forward) |

### Data Sources

- **JE lines** (`raw_quickbooks.journal_entry_lines` + `journal_entries`) — all accounts
- **deposit_lines** (`raw_quickbooks.deposit_lines` + `deposits`) — funds sourced FROM B/S clearing accounts (drains)
- **deposit_to_account** (`raw_quickbooks.deposits.deposit_to_account_name`) — bank sweeps draining PayPal/Undeposited
- **sales_receipts** (`raw_quickbooks.sales_receipts.deposit_to_account_name`) — receipts flowing IN to clearing accounts

---

## Key Findings

### All accounts are OPEN — zero months with CLEAR status (2025 onward)

#### PL_PARENT Accounts: Reclass JEs Do Not Zero Out Parent Accounts

The Controller's month-end reclass JEs credit sub-accounts (e.g., `44010`, `44020`, `44030`) but the debits that flow through the parent accounts (`Support Fees`, `Solutions`) are **not fully offset** each month. This results in large non-zero net_activity on the parents every month.

**Pattern by account:**

| Account | Behavior | Jan 2025 Net | Interpretation |
|---|---|---|---|
| `Solutions` | Debits only (no credits) | +$161,746 | Invoice lines post to parent; reclass JEs credit sub-accounts directly but do NOT credit the parent. Parent is never cleared. |
| `Solutions COGS` | Credits only (no debits) | -$63,176 | Same structure, COGS direction. |
| `Support Fees` | Mixed, large net debit | +$127,061 | Original postings debit parent heavily; reclass credits only partial (~30%). Residual stays in parent. |
| `SaaS Platform:FP Services` | Large net debit | +$263,965 | Same pattern; reclass credits sub-accounts but debits from invoices through the parent are not fully offset. |
| `SaaS Platform COGS:FP Svcs Cost` | Net credit each month | -$567,318 | COGS parent: original postings come in as debits; reclass JEs credit this account heavily (more than debits), netting to large credit. |

**Conclusion on PL_PARENT:** These parent accounts are used as **routing/pass-through accounts** in QB, not true clearing accounts that net to zero. The accounting design routes original transactions through the parent and then reclasses to sub-accounts in separate JEs, but the two legs are not equal per month (often staggered between months). The view correctly captures the net-activity-only (no cumulative carryforward) since these are P&L accounts. The OPEN status reflects the accounting structure, not a close error.

**Notable anomaly — June 2025 `Support Fees`:** Net debit of **$648,225** vs typical $57K–$127K range. Likely an unusually large batch of maintenance fees or a one-off adjustment posted to the parent. Flag for Controller review.

---

#### BS_CLEARING Accounts: Significant Open Balances

**10090 - PayPal - Clearing**

- Data starts: 2025-06-01 (no activity in QB before then)
- Cumulative ending balance as of Feb 2026: **-$391,613**
- Negative balance means more cash was swept OUT to the bank than receipts recorded flowing IN, OR there are receipts flowing in via a source not captured (e.g., PayPal settlement transactions not synced to QB as sales_receipts/deposits).
- Monthly net is consistently negative: sales_receipts credited to PayPal are NOT being offset by deposit transactions in `raw_quickbooks.deposits`.

**11100 - Undeposited Funds**

- Historical balance from QB going back to 2006. As of end of 2024: **+$164,572** (old items never cleared — likely legacy write-offs needed)
- 2025 H2 explosion: sales_receipts (Jun–Dec 2025) posted $434,234 TO Undeposited Funds with **zero corresponding deposit transactions clearing them**.
- Ending balance as of Dec 2025: **+$592,187**
- This is a material open item: 7 months of PayPal-routed sales receipts (Jun–Dec 2025) landed in Undeposited Funds but were never formally deposited to a bank account in QB.

---

## Summary Table (2025 months, all OPEN)

| Account | Type | Months | Min Ending Balance | Max Ending Balance |
|---|---|---|---|---|
| 10090 - PayPal - Clearing | BS_CLEARING | 9 | -$396,006 | -$50,429 |
| 11100 - Undeposited Funds | BS_CLEARING | 9 | +$156,987 | +$592,187 |
| SaaS Platform COGS:FP Svcs Cost | PL_PARENT | 14 | -$881,510 | -$567,318 |
| SaaS Platform:FP Services | PL_PARENT | 14 | +$197,392 | +$437,956 |
| Solutions | PL_PARENT | 14 | +$42,766 | +$228,230 |
| Solutions COGS | PL_PARENT | 14 | -$96,129 | -$12,074 |
| Support Fees | PL_PARENT | 14 | +$56,660 | +$648,225 |

---

## Action Items for Controller

1. **Undeposited Funds ($592K OPEN, Dec 2025):** Confirm whether Jun–Dec 2025 PayPal receipts were physically deposited. If yes, create deposit transactions in QB to clear the backlog. If the receipts flowed directly into PayPal Clearing instead, the mapping needs correction.

2. **PayPal Clearing (-$391K cumulative):** The negative running balance suggests QB is recording PayPal settlements as bank deposits (debiting a bank account, crediting PayPal Clearing) at a higher rate than sales receipts are being credited to PayPal Clearing. Review the `v_paypal_reconciliation` view for the corresponding bank-side entries.

3. **Support Fees parent — June 2025 spike (+$648K):** Investigate whether a large batch was posted to the parent account in error vs. to the numbered sub-accounts. Compare against `v_support_revenue_proof` for June 2025.

4. **PL_PARENT accounts — accounting design:** Consider whether the Controller's close process should add a step to explicitly debit/credit the parent accounts to zero (round-trip reclass). Currently, the design allows residuals to accumulate in parent accounts each month.

---

## View Columns Reference

| Column | Description |
|---|---|
| `account_name` | QB account name |
| `account_type` | `PL_PARENT` or `BS_CLEARING` |
| `report_month` | First day of the month |
| `opening_balance` | Cumulative balance entering the month (B/S only; 0 for P&L) |
| `debits` | Total debits to the account in the month (all sources) |
| `credits` | Total credits to the account in the month (all sources) |
| `net_activity` | debits - credits (positive = net debit) |
| `ending_balance` | opening_balance + net_activity |
| `status` | `CLEAR` if ending_balance = $0.00; `OPEN` otherwise |
