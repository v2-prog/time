# Rotation fork (iteration 040) — review

Nov 26, 2026 · @amar

## Summary

The Rotation fork is sound, and its strongest part is the mandatory separation of score from confidence (line 45). The biggest gap is that the spec never says how an "incline" or "decline" will be measured, so the system can't actually be checked. A few agency and policy names are out of date, and two seed entities sit outside the ASX 200 scope.

## Facts to correct

Five references in the spec are out of date or undefined. Line numbers refer to the iteration 040 file.

| Line | What the spec says | Issue | Fix |
| --- | --- | --- | --- |
| 19 | DMIRS approvals | DMIRS was renamed DEMIRS in Dec 2023; from 1 Jul 2025 its resource regulation function became the [Department of Mines, Petroleum and Exploration (DMPE)](https://www.wa.gov.au/organisation/department-of-mines-petroleum-and-exploration/about-the-department-of-mines-petroleum-and-exploration) | Point the WA ingestion feed at DMPE |
| 22 | Defence White Paper | White papers were replaced by a [National Defence Strategy](https://www.minister.defence.gov.au/media-releases/2024-04-17/2024-national-defence-strategy) revised every two years; the current edition is the [2026 NDS](https://news.usni.org/2026/04/17/2026-australian-national-defence-strategy), released 16 Apr 2026 | Use the NDS and its Integrated Investment Program; treat the two-year cycle as a scheduled policy event |
| 19 | Northern Minerals, Arafura as seed entities | Arafura was only [added to the ASX 300](https://www.investsmart.com.au/investment-tools/shares/asx-price-sensitive-announcements/asx-arr/2498742) in Mar 2026; Northern Minerals is a small cap. Both are outside the "top 200" scope on line 11 | Drop them, or mark them as watch-list names outside scope |
| 19, 23 | Whitehaven in Resources | Whitehaven is classed as Energy, not Materials, under GICS | Decide whether Energy folds into Resources; if it stays separate, Whitehaven belongs there |
| 61 | "2023 banking-sector policy aftermath" and "a PBS delisting event" | The 2023 banking crisis was SVB and Credit Suisse, not an Australian event; neither worked example is named | Name a specific Australian event for each (e.g. a specific APRA response or RBA decision; a specific PBS delisting) |

## Design gaps

Nine gaps, roughly in order of how much they block validation.

1. **Outcomes have to be measured relative to something.** Rotation is about one bracket against another, but line 51 asks "did financials actually decline". In a falling market every bracket declines. Measure each bracket's return against the ASX 200, using the S&P/ASX 200 sector indices (Financials, Health Care, Materials, Energy, Industrials) as benchmarks. The rotation outcome is the spread between the two brackets over the window.
2. **Counting events gives activity, not direction.** Line 41 counts and weights events, but nothing says whether an event pushes a bracket up or down. A rate cut and a rate hike are both "RBA events". Each event needs a direction tag (positive, negative or mixed for this bracket) with documented rules, including the indirect impacts from line 37.
3. **Brackets produce news at very different rates.** Financials gets RBA meetings, APRA releases and Treasury papers all year; Healthcare gets lumpy PBS schedule changes. Raw counts will always make Financials look active. Score each bracket against its own historical baseline, such as a z-score of event intensity.
4. **"Magnitude" has no units.** Line 51 compares outcomes to the magnitude estimate, which only works once magnitude means something: expected relative return in percent, or a rank. Pick one for version one.
5. **There needs to be a baseline to beat.** If Rotation can't beat plain momentum (whichever bracket outperformed over the last three months keeps doing so), the policy layer adds nothing. Log the momentum baseline next to every signal from day one.
6. **The sample is small, and overlapping windows hide that.** Five brackets on three-month windows give about 20 independent observations a year; sliding windows make it look like hundreds. Report hit rates on non-overlapping windows only, and backtest the Resources bracket on the 2020–2024 China dispute before going live.
7. **Money leaving one bracket need not go to another.** Line 55 assumes it must, but it can go to cash, bonds or offshore markets. Keep it as a hypothesis to test, not an assumption built into the spillover score.
8. **Spell out how confidence is calculated.** Line 45 is the most important rule but leaves confidence as "human-style judgement". Make it mechanical so it can't drift: feed freshness, the share of the bracket's market cap with recent events, and whether key sources have gone silent.
9. **A rotation has two legs, and both need the execution layer.** Exiting one bracket and entering another means two execution plans from iteration 039, each with its own delay before Doug can act. ASX settles T+2, not T+1 (the fix from the 039 review carries over). If Doug rotates through sector ETFs rather than individual stocks, the entity graph needs to model those ETFs.

## What to keep and next step

Keep the score-versus-confidence rule (line 45) and the design rationale on line 67 as written; calling Rotation experimental is an accurate description, not hedging.

- [ ] Fold these fixes and the 039 review fixes into revised 039 and 040 files for the build

## Sources

- [About the Department of Mines, Petroleum and Exploration](https://www.wa.gov.au/organisation/department-of-mines-petroleum-and-exploration/about-the-department-of-mines-petroleum-and-exploration) (WA Government)
- [2024 National Defence Strategy media release](https://www.minister.defence.gov.au/media-releases/2024-04-17/2024-national-defence-strategy) (Minister for Defence)
- [2026 Australian National Defence Strategy](https://news.usni.org/2026/04/17/2026-australian-national-defence-strategy) (USNI News)
- [S&P DJI March 2026 quarterly rebalance summary](https://www.investsmart.com.au/investment-tools/shares/asx-price-sensitive-announcements/asx-arr/2498742) (InvestSMART)
- [ASX T+1 settlement cycle](https://asx.com.au/markets/clearing-and-settlement-services/t1-settlement-cycle) (ASX)
