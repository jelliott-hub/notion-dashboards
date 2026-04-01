# Solutions Revenue Dedup (v_solutions_revenue_txn)

## Problem (Fixed 2026-03-31)
Invoices with `GroupLineDetail` were double-counted:
- `invoice_direct` picked up SalesItemLineDetail lines
- `invoice_group_expanded` expanded GroupLineDetail sub-lines
- Both fired for the same invoice, adding $2,775/month (Feb 2026: +$1,110 Hardware, +$1,605 Services, +$60 Shipping)

## Fix
Added `group_invoice_ids` CTE that collects all invoice_ids with GroupLineDetail lines. The `invoice_direct` CTE now excludes these:
```sql
AND il.invoice_id NOT IN (SELECT invoice_id FROM group_invoice_ids)
```

## View Structure (5 source CTEs)
1. `invoice_direct` — SalesItemLineDetail lines (EXCLUDING group invoices)
2. `invoice_shipping` — SHIPPING_ITEM_ID lines
3. `invoice_group_expanded` — GroupLineDetail sub-lines via jsonb_array_elements
4. `je_breakout` — JE lines to Solutions accounts
5. `credit_memo_adj` — Credit memo lines (negative amounts)

All UNION ALL'd with columns: source_record_id, report_month, transaction_date, customer_key, gl_account, amount, line_type, source_type, source_system.

## GL Accounts Covered
43010 Hardware, 43020 Hardware Discounts, 43030 Services, 43040 Software, 43050 Software & Services Disc, 43060 System-Applc-Livescn-SW (JE only), 43070 Shipping, 43080 Reinstatement Fee (JE only), 43090 Finance Charges
