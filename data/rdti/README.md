# R&D Tax Incentive base ledger — sketch, not live

General information only, not personal financial advice. Australia only. Ledger and ticker matching only: no projections, no alerts.

## Source
- Australian Taxation Office, *Report of information about research and development tax incentive entities*, 2021-22, 2022-23 and 2023-24, published under s3H of the Taxation Administration Act 1953.
- data.gov.au dataset `research-and-development-tax-incentive` (CKAN package checked via `package_show`), licence CC BY 2.5 AU. Source: Australian Taxation Office. This ledger is a derived work; figures are unchanged.
- Retrieved 27 Nov 2026, about 15:19 AEDT. URLs, CKAN last-modified dates, byte sizes and SHA-256 hashes are in `sources.json`. Raw workbooks are not committed; rebuild with `python scripts/rdti/build_ledger.py RAW_DIR ASX_CSV --abr-checked data/rdti/abr_checks.json`.
- ASX listed companies list: https://www.asx.com.au/asx/research/ASXListedCompanies.csv (as at Fri 27 Nov 2026 15:05 AEDT). Used only to infer the ticker; not republished.

## Method
1. **Parse.** Each workbook's report sheet has five columns: company name, ABN/ACN, total R&D expenditure (notional deductions less feedstock adjustments), total amended R&D expenditure, income year.
2. **Identifiers.** 11-digit values are ABNs (modulus-89 check); values of 9 digits or fewer are ACNs, zero-padded to 9 (modulus-10 check). When an ABN's last 9 digits pass the ACN check they are recorded as the ACN. All 38,320 identifiers pass; 2 rows (PHD LABS INC, PFL LABS INC, 2022-23) have no identifier. Not checked against the ABR register except the spot checks in `abr_checks.json`.
3. **Entity key and supersession.** Entity key = ACN, else ABN. Each report also carries late lodgements and amendments for earlier years; for the same entity and income year the later report wins, and `source_report` records which. Two entities appear under an ABN in one report and an ACN in the next; the key merges them.
4. **Effective figure.** The amended figure when present, otherwise the reported figure.
5. **Ticker matching (listed companies only).** The ASX list has no ABN/ACN, so matching is by legal name, then hand-reviewed overrides (`asx_overrides.json`).
   - high: exact normalised name (LIMITED→LTD, punctuation, "THE" removed) to a public (non-PTY) company.
   - medium: match after dropping generic words (GROUP, HOLDINGS, AUSTRALIA, CORPORATION...), or a reviewed subsidiary link.
   - low: a PTY company whose name matches, or starts with, the listed company's core name.
   - Flags: `name_only_match`, `possible_subsidiary`/`subsidiary`, `foreign_registered_parent` (INC/CORP/PLC/N.V. parent), `foreign_listed_parent`, `group_multiple_entities`, `group_restructure`, `dual_listed_group`, `renamed`, `abn_not_cross_checked`.
6. **Derived fields.** YoY % per year (null if a year is missing or the base is zero) and a two-period CAGR from 2021-22 to 2023-24 (null if an endpoint is missing or not positive).
   - R&D share of revenue: null. Revenue isn't in the ATO data, and the claimant is often a subsidiary.
   - R&D share of market cap: null. Market-cap data is ASX/vendor licensed and can't be republished.
   - AusIndustry registered estimate vs ATO claim gap: null. DISR/AusIndustry does not publish per-company registration estimates.

## Checks
- Counts match Rand Advisory's published summary exactly: 11,709 / 13,121 / 13,490 entities, 18,733 distinct companies, the $20m+ band (47 / 88 / 89) and the medians ($331,279 / $374,712 / $374,175). Totals differ for 2021-22 ($11.42b here vs $11.2b) and 2022-23 ($16.48b vs $16.2b), most likely because those totals include later late lodgements and amendments. Unverified.
- Top-claimant re-check and ABN Lookup spot checks: see `comparison.json` and `abr_checks.json`.

## Limitations (verify before any use beyond a sketch)
- Name matching misses listed groups whose R&D is claimed by a differently named subsidiary (e.g. Atlassian's claimant is a subsidiary of a NASDAQ-listed parent; many foreign multinationals). Company-group structure is not resolved.
- Only the current ASX list is used, so companies delisted since lodgement do not match. Delisted status is not flagged automatically.
- Low and medium matches are unverified. Even high matches only confirm the name; ABN↔listing was spot-checked on ABN Lookup for the top 25.
- The ATO figure is notional deductions less feedstock adjustments, not cash R&D spend or the tax offset received.
