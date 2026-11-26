# Time.vilo.au

Temporal event correlator for Australian resources, semiconductors, and ASX sector rotation verification.
Live at https://time.vilo.au (Cloudflare Pages project `time`, production branch `main`).

- **Resources** (`resources/aus-dashboard.html`): live ASX and WA DMPE records, feed health for all 23 spec feeds, sourced matches, policy timeline.
- **Semiconductors** (`chips/chip-dashboard.html`): verified H20 export-control and NVIDIA items.
- **Rotation Verification** (`rotation/`): verification queues (iteration 042) plus the iteration 040 measurement fixes in `rotation/logic.js`.

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
