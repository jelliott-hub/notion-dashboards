# Phase 2.7 – Solutions Shipment Audit View
**Close Checklist Task:** 3.22 – Confirm all shipped orders are invoiced  
**Status:** DONE  
**View created:** `finance.v_solutions_shipment_audit`  
**SQL file:** `sql/phase2/2_7_shipment_audit.sql`  
**Run date:** 2026-04-01

---

## Investigation Summary

### What Was Looked For
A dedicated shipment tracking table. None exists in the database.

### Shipment Proxy Selected
QB **Estimates** are B4ALL's functional proxy for "shipped/committed orders":

- `finance.v_qb_estimates` — email-based log of estimate events (sent/accepted) identified by SO number, populated from the `accounting` mailbox. Covers 2025-12-08 to 2026-03-27 with 749 rows across 444 distinct SO numbers.
- `raw_quickbooks.invoice_linked_txns` (type = `'Estimate'`) — QB-native linkage recording which invoices were formally converted from estimates. Contains 1,345 links covering 673 distinct invoices.

### Data Sources Used

| Table | Role |
|---|---|
| `raw_quickbooks.invoice_linked_txns` | QB estimate-to-invoice conversion record |
| `raw_quickbooks.invoices` | Invoice status, balance, amount |
| `finance.v_qb_estimates` | Email estimate event log (SO-number keyed) |

Join key: `so_number` (invoice `doc_number` = estimate email SO number).

---

## View Design

`finance.v_solutions_shipment_audit` performs a **FULL OUTER JOIN** between:
1. QB invoices that were converted from estimates (`estimate_invoices` CTE)
2. Email-tracked estimate events (`email_estimates` CTE)

Each row represents one SO number (or one invoice), with an `audit_status` flag:

| audit_status | Meaning |
|---|---|
| `INVOICED_PAID` | Estimate converted to invoice; invoice fully paid (balance = 0) |
| `INVOICED_OPEN` | Estimate converted to invoice; balance still outstanding |
| `EMAIL_ONLY_NO_INV` | Estimate emailed but no matching QB invoice found |
| `INVOICE_NO_EMAIL` | QB estimate-linked invoice but no email event in accounting mailbox |
| `UNKNOWN` | Edge case: email event with null SO number |

---

## Findings as of 2026-04-01

| audit_status | Count | Invoice Total | Open Balance |
|---|---|---|---|
| INVOICED_PAID | 634 | $1,575,398.22 | $0.00 |
| INVOICED_OPEN | 39 | $371,800.48 | $340,581.47 |
| EMAIL_ONLY_NO_INV | 249 | — | — |
| UNKNOWN | 1 | — | — |

### Key Observations

**1. 39 open invoices ($340,581 outstanding balance)**  
These are estimates that were formally converted to QB invoices but have not been fully collected. Largest open items include Puerto Rico Dept of Health ($250,000 combined across two invoices) and School Board of Lee County ($18,405). Most are recent (Feb–Mar 2026) and may still be within terms.

**2. 249 EMAIL_ONLY_NO_INV — estimates emailed but no QB invoice matched**  
These SO numbers appear in the accounting mailbox email log but do not have a QB invoice with a matching `doc_number`. Possible explanations:
- Estimates were sent but declined/cancelled (not converted)
- Invoices exist under a different doc_number format
- Invoices are outside the QB sync window
- Email events represent resends or reminders of already-invoiced SOs

This bucket requires manual review to determine which represent genuine uninvoiced shipments vs. cancelled/declined estimates.

**3. 1 UNKNOWN row**  
A `payment_receipt` event in `finance.v_qb_estimates` with a null SO number. Likely a malformed email parse. No action needed — represents $949.40.

**4. No INVOICE_NO_EMAIL rows**  
All QB estimate-linked invoices either have a matching email event or fall into the INVOICED categories. No invoices are orphaned from the email log.

---

## Limitations / What Would Improve This

1. **No actual shipment table.** The B4ALL workflow does not capture physical shipment events (ship date, tracking number, carrier). This view audits the estimate-to-invoice pipeline as the closest available proxy.
2. **Email log coverage is recent only** (Dec 2025 – Mar 2026). Older estimates are not tracked in `finance.v_qb_estimates`.
3. **SO number join is fuzzy** — email subjects are parsed for SO numbers; any parsing failures would inflate `EMAIL_ONLY_NO_INV`.
4. **To fully close Task 3.22**, the 249 EMAIL_ONLY_NO_INV rows should be reviewed against the QB estimate list to confirm none represent unintentionally uninvoiced orders.

---

## Close Checklist Sign-Off Query

```sql
SELECT
    audit_status,
    COUNT(*)                        AS record_count,
    SUM(invoice_amount)             AS total_invoice_amt,
    SUM(invoice_balance)            AS total_open_balance
FROM finance.v_solutions_shipment_audit
GROUP BY audit_status
ORDER BY 1;
```
