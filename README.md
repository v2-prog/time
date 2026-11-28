# Time.vilo.au

Temporal event correlator for Australian resources, semiconductors, and ASX sector rotation verification.
Live at https://time.vilo.au (Cloudflare Pages project `time`, production branch `main`).

The main view (`/`) is a mobile-first status strip: feed health and last run times, new signals today, items that still need a check, upcoming dates, and a link to Tic (`https://tic.vilo.au`). A hidden Audit section (`/audit/`, noindex, not in the main navigation) holds the signal list with collapsed “why” panels, excluded items, the fact-check log, matches and their reasoning, and links to the existing dashboards. Those dashboards stay at their current URLs and are not deleted.

- **Resources** (`resources/aus-dashboard.html`, hidden): live ASX and WA DMPE records, feed health for all 23 spec feeds, sourced matches, policy timeline.
- **Semiconductors** (`chips/chip-dashboard.html`, hidden): verified H20 export-control and NVIDIA items.
- **Rotation Verification** (`rotation/`, hidden): verification queues (iteration 042) plus the iteration 040 measurement fixes in `rotation/logic.js`.
- **Data index** (`/data/index.json`): catalogue of every data feed with its path, schema, last updated time and description. The signals feed stays at `/data/signals/signals.json` (`gov.signal.v1`).

Matches record temporal proximity and shared scope only. No causation, no advice, no broker recommendations or entry points. Australia only; general information, not personal financial advice.

## Data pipeline

`python3 fetchers/run_all.py` runs the live fetchers and writes same-origin JSON:

| Feed | Source | Output |
|---|---|---|
| `asx_announcements` | asx.com.au announcements list (links, times, price-sensitive flag) plus the markitdigital JSON the ASX site uses (announcement type) | `data/feeds/asx_announcements.json` |
| `wa_dmpe_announcements` | wa.gov.au DMPE organisation page and announcement pages | `data/feeds/wa_dmpe_announcements.json` |
| `wa_dmpe_tenements` | SLIP ArcGIS REST, Mining Tenements DMIRS-003 (CC BY 4.0), grants in the last 60 days, company holders only | `data/feeds/wa_dmpe_tenements.json` |

Feed health for every feed (live or never run) goes to `data/feed_health.json`. A failed run keeps the last good data and marks the feed error/stale.

`.github/workflows/fetch-feeds.yml` runs the tests and fetchers on weekdays (about 06:30 and 18:30 Sydney time), commits changed JSON, and Pages redeploys. No secrets are needed, and the browser makes no cross-origin calls.

Record shape: `fetchers/schema.py` (`NormalisedRecord`).

## Matching engine

`python3 fetchers/correlator.py` (run by the workflow after the fetchers) scores every record in `data/feeds/` against `data/policy_timeline.json` and writes `data/matches.json`:

- `engine`: ranked, engine-generated matches. Each one has a score with its parts (temporal, entity, topic, source, volatility weight, verification factor), a separate mechanical confidence, the lag and window, shared tags, a one-line rationale, flags and a link to the source. Earlier engine matches stay for 400 days, marked `archived` once their record leaves the feed.
- `seeded`: the hand-seeded matches, kept unchanged and labelled as seeded.
- `bracket_activity`: engine match counts per Rotation bracket in non-overlapping 30-day windows. The Rotation page uses these for the z-score.

Entities come from `fetchers/schema.py` (`WATCHED`, aliases included). Policy events list the entities and topic tags they affect. ASX headlines are never published: the fetcher turns each headline into coarse topic tags in memory (`fetchers/topics.py`), and the engine matches on ticker, time, type, price-sensitive flag and those tags.

Formula and gates: see the docstring at the top of `fetchers/correlator.py`.

## Gov signals feed (sketch, information only)

`python3 fetchers/signals.py [--sector-watch DIR]` turns hand-checked government and regulatory events (`data/signals/events.json`) into `data/signals/signals.json` (`gov.signal.v1`). Each signal has a source, a verification status, a direction tag, a 1–5 strength rating from a written rubric and plain reasoning. The script joins signals to ASX 200 Sector Watch heat-map cells by ticker or GICS sector and timeframe. It also writes `data/signals/ratio-signals.json` (tt's `ratio.signal.v1`, intersections only). Tic and tt consume these files. The rubric, join contract and what is needed from Sector Watch are in `data/signals/README.md`. No buy, sell or hold calls, entry points or ladders.

## Tests

```
python3 -m unittest discover -s tests -p "test_*.py"
node tests/test_logic.js
```

## Terms and limits

- ASX: the announcement endpoints are not a documented public API. ASX's site terms restrict use to personal, non-commercial purposes. We republish nothing by default: the public JSON holds code, time, type, price-sensitive flag and an ASX link, with headlines withheld (set `TIME_PUBLISH_ASX_HEADLINES=1` only with ASX consent or behind access control). Requests are low rate (one request per code, 1.5 s apart, twice a day). Get an ASX data licence before any commercial or redistributed use.
- WA data: © State of Western Australia (DMPE), CC BY 4.0. Attribution is in the dashboard footer.
- S&P/ASX index levels are licensed, so none are shipped. The Rotation spread calculator takes reader-entered returns.

General information only.
