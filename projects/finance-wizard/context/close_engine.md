# Close Engine — DN000811 / DN000812

## DN000811: AR/COGS True-Up
**Function**: `finance.derive_dn000811(p_year, p_month)`
**Returns**: 7 JE lines (11000, 51010, 51020, 51025, 41010, 41020, 41030)
**Posted as**: Variable doc_number (changes monthly)

### Calculation Steps
1. **OI delta**: current month - prior month from `raw_thinclient.sk_outstanding_invoices`
2. **DN000807 AR**: subtract server-tracked cost adj (11000 lines from DN000807 JE)
3. **Other JE AR**: sum other JE adjustments to 11000, excluding DN000807/811/802 and Tier 5 reversals via `lookup.je_tier_classification`
4. **AR amount** = OI delta - DN807 + other adj
5. **Gov fees (51010)** = SK gov fees (CADOJ, FBINV, FDLE, PRDOJD) - actual vendor bills (DOJ, FBI, FDLE purchases)
6. **SAM cost (51020)** = SRS credits - Sterling Identity bills
7. **Plug (51025)** = -(AR - 51010 - 51020)

### Critical Dependency
- `lookup.je_tier_classification` must exist (45 rows) — used in Step 3 to filter Tier 5 reversals
- Was accidentally dropped; restored 2026-03-31

## DN000812: AP True-Up (SAM Payable)
**Function**: `finance.derive_dn000812(p_year, p_month)`
**Returns**: 2 JE lines (51025, 20000)
**Baseline**: 2025-01-01 (hardcoded as `v_baseline_date`)

### Calculation
1. Cumulative SRS credits from `v_sk_fee_classification` (agency='SRS', description='SRS Credit') from baseline through target month
2. Cumulative Sterling Identity bills from `raw_quickbooks.bill_lines` from baseline through target month
3. Gap = SRS - Sterling
4. Subtract prior DN000812 postings (debit to 51025)
5. Amount = gap - prior postings

### Known Issue
- Jan 2026: function produces $10,111.50; Controller posted $8,740.91
- $1,371 delta — possible bill timing or filter difference
- Self-corrects: Feb subtracts actual Jan posting ($8,740.91), producing $494.59

### Data Sources (monthly SRS vs Sterling, 2025)
| Month | SRS Credits | Sterling Bills | Gap | Cumulative |
|---|---|---|---|---|
| Jan 2025 | $30,804 | $30,615 | $190 | $190 |
| ... | | | | |
| Sep 2025 | $22,152 | $20,347 | $1,805 | $8,769 |
| Jan 2026 | $25,500 | $26,361 | -$861 | $10,112 |
