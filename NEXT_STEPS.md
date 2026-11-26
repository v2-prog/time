# Next steps for Time.viol.au

## 1. Live fetchers (priority)

- **ASX announcements**: Build fetcher for price-sensitive announcements (BHP, RIO, FMG, NTU, WHC, etc.). Use ASX API or RSS if available; fall back to scraping with rate limits. Store as NormalisedRecord.
- **WA DMPE**: Point at Department of Mines, Petroleum and Exploration mining tenure and approvals. Update from old DMIRS/DEMIRS names.
- Then EPBC public notices, Qld NRMMRRD, Chinese customs monthly tables.
- Integrate with correlator_core matching. Output updated dashboards.

## 2. Clear verify: true / needs_human_verification

Items from CORRECTIONS.md:
- Coal restriction dates (May 2020 verbal, Oct 2020 start, 3 Jan 2023 easing, 14 Mar 2023 full removal) — primary reporting only; seek NDRC/customs primary if exists.
- Provisional wine deposits late Nov 2020.
- Critical Minerals Strategy 2023–2030 release (20 Jun 2023).
- CMPTI announcement (14 May 2024 Budget).
- CMRG start (week of 22 Sep 2025) and Jingbao date.
- 2026 Northern Minerals orders registration date.
- Japanese/Chinese aliases, port/rail relationships.
- Both real commercial seed events (BHP/CMRG 22 Apr 2026, China Energy coal ~6 Jan 2023) against company releases.

## 3. Fold Rotation design-gap fixes (before any live use)

From iteration 040 review:
- Outcomes as spreads vs S&P/ASX 200 sector indices (Financials, Health Care, Materials, Energy, Industrials).
- Direction tags (positive/negative/mixed) on every event, with documented rules.
- Baseline-adjust event intensity (z-score per bracket).
- Mechanical confidence: feed freshness + market-cap coverage + silence detection.
- Log momentum baseline next to every signal.
- Non-overlapping windows for hit rates; backtest Resources on 2020–24 China dispute.
- Spillover to cash/bonds/offshore is hypothesis only.
- T+2 settlement (not T+1).
- Add sector ETF entities to the graph if used for execution.
- Agency name updates (DMPE, NDS, etc.).

## 4. DNS and deploy

- Create Cloudflare Pages project linked to v2-prog/time.
- Point time.vilo.au (or chosen subdomain) CNAME to the Pages URL.
- Ensure _headers for CSP if using the Rotation app.
- Deploy static site first; add backend later for live matching.

## Status

Repo initialised with review documents and shared CSS. Full dashboard HTML/JS (Resources, Chip, Rotation) to be added in follow-up commit from local artifacts. Live fetchers and verification require primary-source checks and coding outside this session.

General information only. Not financial, legal or tax advice.
