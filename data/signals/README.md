# Gov signals feed (`gov.signal.v1`): sketch, information only

This feed covers Australian government and regulatory events that may bear on ASX-listed stocks: tenders, policy, ASIC, mergers (ACCC and schemes) and approvals (FIRB, EPBC, state). Each event is checked by hand against a linked source, given a strength rating from a written rubric, and joined to ASX 200 Sector Watch heat-map cells where the two intersect.

> **General information only, Australia only. Not personal financial or legal advice.** The feed has no buy, sell or hold calls, no entry points, no ladders and no broker names. `fetchers/signals.py` refuses any output that contains advice-like fields or phrases. Items from US regulators (FDA) appear only as events of ASX-listed companies and are labelled that way.

| File | What it is |
|---|---|
| `events.json` | Curated input, one entry per event. Every figure comes from the linked source. |
| `tickers.json` | ASX code, company name and GICS industry group for the codes used, checked against the ASX listed-companies list as at 28 Nov 2026. |
| `sector_watch_join.json` | Cached minimal subset of Sector Watch cells: id, instrument, sector, timeframe, colour, conviction, horizon type and the verification flag. It holds no prices, summaries or move labels. |
| `signals.json` | Canonical output, schema in `schema.json`. Tic consumes this file. |
| `ratio-signals.json` | The same signals in tt's `ratio.signal.v1` contract, restricted to heat-map intersections. |

Run it with `python3 fetchers/signals.py --sector-watch /workspace/asx-sector-watch`. The box path is read only and the folder is never modified. Without the flag, the script reuses the cached subset.

## Strength rubric (`strength-rubric-v1`)

Four components are scored by hand. Each score has a written basis in `events.json`.

| Component | Weight | 0 | 1 | 2 | 3 |
|---|---|---|---|---|---|
| **Materiality**: size relative to the affected companies | 35% | negligible | small | moderate | large or structural |
| **Certainty / stage** | 25% | proposal, commentary, or pending with timing reported only | introduced, notified, open tender, or proceedings/allegations | passed, decided or approved, but not yet effective or with conditions pending | final and effective, implemented, or data released |
| **Directness of exposure** | 25% | macro or sector-wide, no company | sector with plausible but unnamed exposure | a regulated class the company belongs to, or a named company with an indirect dependency | the company is named as a party |
| **Source reliability** | 15% | (not used) | secondary only (media or trade press) | primary statement or summary from a party | primary government, regulator, court or ASX-lodged document |

`weighted = (0.35·M + 0.25·C + 0.25·D + 0.15·S) / 3`, which gives a value from 0 to 1. It is then banded: **5** at 0.85 or above, **4** at 0.65 or above, **3** at 0.45 or above, **2** at 0.25 or above, and **1** below that.

Three caps apply:
- `secondary_only` caps strength at 3.
- `needs_human_verification` caps it at 2.
- If a ticker's exposure is general knowledge but not stated in the source, strength is capped at 4.

Both the uncapped value and the caps applied are kept on each signal.

Strength measures how solid and direct the link is. It does **not** forecast price.

## Other fields

- **Direction tag:** `headwind`, `tailwind` or `mixed` (which includes unclear). It describes the likely sign of the effect on the affected companies, not a price call.
- **Verification:** `confirmed_primary`, `secondary_only` or `needs_human_verification`, plus the open items on each signal.
- **Timeframe:** uses the same values as Sector Watch (`days`, `weeks`, `months`, `years`). The bucket is set by the time from as-of to the effect or decision date: 10 days or less, 56 days or less, 365 days or less, or longer. If there is no forward date, it is bucketed by how long ago the event was.
- **Rotation bracket:** the GICS sector maps to Woods Rotation as Materials → Resources, Energy → Energy, Financials → Financials, Health Care → Healthcare and Industrials → Industrials. Utilities and other sectors are reported as `outside_brackets`.
- **ASX 200 membership:** always `null` here. S&P/ASX constituents are licensed, so membership has to come from Sector Watch.

## Sector Watch join

The join key is `instrument` (the ASX code) for ticker cells, and the S&P/ASX 200 sector index code (XEJ, XMJ, XFJ, XHJ, XNJ, XUJ and so on) or GICS sector for sector cells. Sector Watch's `Healthcare` is treated as GICS `Health Care`. A signal **intersects** if any affected ticker or sector has a cell. `same_timeframe_cells` lists the cells with the same timeframe. Only intersecting signals go to tt.

**What we need from Sector Watch** (see Woods iteration 045):
1. A stable file path, or a published URL that the scheduled GitHub run can reach. The box folder is not visible to Actions.
2. An S&P/ASX 200 Industrials (XNJ) row and a Utilities (XUJ) row. Without them, the gas, CIS, trade and ports signals cannot join.
3. An `asx200_member` flag per ticker row, or a constituents list.
4. Ticker rows for names this feed rates: STO, ORG, WDS, RWC, CGF, MYX, ALD, CBA, MQG, BHP, GMD, MPL and NHF.
5. Confirmation that `fast_move_candidate` "candidate trades" is not meant to travel to tt. This feed does not carry that flag.
