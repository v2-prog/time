"""Build data/index.json — a machine-readable catalogue of every data feed.

Does not modify signals.json or any other feed. The public path
/data/signals/signals.json and the gov.signal.v1 schema stay frozen.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "index.json"
SYD = timezone(timedelta(hours=11))

# Public URL path, schema id or label, description. updated_at is filled from the file.
CATALOGUE = [
    {
        "id": "gov_signals",
        "path": "/data/signals/signals.json",
        "file": "data/signals/signals.json",
        "schema": "gov.signal.v1",
        "description": "Canonical government and regulatory signals: source, verification, direction, strength rating and reasoning. Frozen path and schema.",
    },
    {
        "id": "ratio_signals",
        "path": "/data/signals/ratio-signals.json",
        "file": "data/signals/ratio-signals.json",
        "schema": "ratio.signal.v1",
        "description": "The same signals in tt's contract, restricted to Sector Watch heat-map intersections.",
    },
    {
        "id": "gov_signal_events",
        "path": "/data/signals/events.json",
        "file": "data/signals/events.json",
        "schema": "gov.signal.events",
        "description": "Hand-curated input events for the signals feed, including excluded items.",
    },
    {
        "id": "gov_signal_tickers",
        "path": "/data/signals/tickers.json",
        "file": "data/signals/tickers.json",
        "schema": "gov.signal.tickers",
        "description": "ASX code, company name and GICS industry group for codes used in the signals feed.",
    },
    {
        "id": "gov_signal_schema",
        "path": "/data/signals/schema.json",
        "file": "data/signals/schema.json",
        "schema": "json-schema",
        "description": "JSON Schema for gov.signal.v1.",
    },
    {
        "id": "sector_watch_join",
        "path": "/data/signals/sector_watch_join.json",
        "file": "data/signals/sector_watch_join.json",
        "schema": "sector_watch_join.v1",
        "description": "Minimal cached Sector Watch cells used for the join (no prices, summaries or move labels).",
    },
    {
        "id": "matches",
        "path": "/data/matches.json",
        "file": "data/matches.json",
        "schema": "time.matches.v1",
        "description": "Engine-generated and hand-seeded matches of commercial records to policy events, with scores and rationales.",
    },
    {
        "id": "verification",
        "path": "/data/verification.json",
        "file": "data/verification.json",
        "schema": "time.verification.v1",
        "description": "Fact-check log of flagged claims against primary sources (confirmed, corrected, unverifiable).",
    },
    {
        "id": "feed_health",
        "path": "/data/feed_health.json",
        "file": "data/feed_health.json",
        "schema": "time.feed_health.v1",
        "description": "Status, last run and last success times for every fetcher, live or not yet built.",
    },
    {
        "id": "asx_announcements",
        "path": "/data/feeds/asx_announcements.json",
        "file": "data/feeds/asx_announcements.json",
        "schema": "time.normalised_records.v1",
        "description": "Live ASX announcements for the watched resources codes (links, times, type, price-sensitive flag; headlines withheld).",
    },
    {
        "id": "wa_dmpe_announcements",
        "path": "/data/feeds/wa_dmpe_announcements.json",
        "file": "data/feeds/wa_dmpe_announcements.json",
        "schema": "time.normalised_records.v1",
        "description": "Live WA Department of Mines, Petroleum and Exploration announcements.",
    },
    {
        "id": "wa_dmpe_tenements",
        "path": "/data/feeds/wa_dmpe_tenements.json",
        "file": "data/feeds/wa_dmpe_tenements.json",
        "schema": "time.normalised_records.v1",
        "description": "WA mining tenement grants (DMIRS-003, CC BY 4.0), company holders, last 60 days.",
    },
    {
        "id": "policy_timeline",
        "path": "/data/policy_timeline.json",
        "file": "data/policy_timeline.json",
        "schema": "time.policy_timeline.v1",
        "description": "Policy and regulatory events for the Resources correlator, with entities and topic tags.",
    },
    {
        "id": "chips",
        "path": "/data/chips.json",
        "file": "data/chips.json",
        "schema": "time.chips.v1",
        "description": "Seeded US export-control and NVIDIA events for the semiconductor correlator.",
    },
    {
        "id": "rdti_counts",
        "path": "/data/rdti/counts.json",
        "file": "data/rdti/counts.json",
        "schema": "time.rdti.counts",
        "description": "R&D Tax Incentive ledger entity and spend totals by income year (sketch, not live).",
    },
    {
        "id": "rdti_listed_matches",
        "path": "/data/rdti/listed-matches.json",
        "file": "data/rdti/listed-matches.json",
        "schema": "time.rdti.listed_matches",
        "description": "R&DTI claimants matched to ASX tickers, with confidence tiers (sketch, not live).",
    },
    {
        "id": "rdti_ledger_2021_22",
        "path": "/data/rdti/ledger-2021-22.json",
        "file": "data/rdti/ledger-2021-22.json",
        "schema": "time.rdti.ledger",
        "description": "ATO R&D Tax Incentive transparency report 2021-22, parsed ledger (sketch, not live).",
    },
    {
        "id": "rdti_ledger_2022_23",
        "path": "/data/rdti/ledger-2022-23.json",
        "file": "data/rdti/ledger-2022-23.json",
        "schema": "time.rdti.ledger",
        "description": "ATO R&D Tax Incentive transparency report 2022-23, parsed ledger (sketch, not live).",
    },
    {
        "id": "rdti_ledger_2023_24",
        "path": "/data/rdti/ledger-2023-24.json",
        "file": "data/rdti/ledger-2023-24.json",
        "schema": "time.rdti.ledger",
        "description": "ATO R&D Tax Incentive transparency report 2023-24, parsed ledger (sketch, not live).",
    },
    {
        "id": "rdti_schema",
        "path": "/data/rdti/schema.json",
        "file": "data/rdti/schema.json",
        "schema": "json-schema",
        "description": "JSON Schema for the R&DTI ledger files.",
    },
    {
        "id": "rdti_sources",
        "path": "/data/rdti/sources.json",
        "file": "data/rdti/sources.json",
        "schema": "time.rdti.sources",
        "description": "Source URLs and licences for the R&DTI ledger.",
    },
    {
        "id": "rdti_ledger_2021_22_csv",
        "path": "/data/rdti/ledger-2021-22.csv",
        "file": "data/rdti/ledger-2021-22.csv",
        "schema": "csv",
        "description": "CSV export of the 2021-22 R&DTI ledger (sketch, not live).",
    },
    {
        "id": "rdti_ledger_2022_23_csv",
        "path": "/data/rdti/ledger-2022-23.csv",
        "file": "data/rdti/ledger-2022-23.csv",
        "schema": "csv",
        "description": "CSV export of the 2022-23 R&DTI ledger (sketch, not live).",
    },
    {
        "id": "rdti_ledger_2023_24_csv",
        "path": "/data/rdti/ledger-2023-24.csv",
        "file": "data/rdti/ledger-2023-24.csv",
        "schema": "csv",
        "description": "CSV export of the 2023-24 R&DTI ledger (sketch, not live).",
    },
]


def _stamp(obj):
    if not isinstance(obj, dict):
        return None
    for key in ("generated_at", "as_of", "checked_at", "updated_at"):
        if obj.get(key):
            return obj[key]
    meta = obj.get("meta")
    if isinstance(meta, dict):
        for key in ("generated_at", "as_of", "asx_list_as_at", "updated_at"):
            if meta.get(key):
                return meta[key]
    return None


def updated_at(path: Path):
    if not path.exists():
        return None
    if path.suffix.lower() == ".json":
        try:
            return _stamp(json.loads(path.read_text()))
        except (json.JSONDecodeError, OSError):
            return None
    return None


def build(root: Path = ROOT) -> dict:
    now = datetime.now(SYD).replace(microsecond=0).isoformat()
    feeds = []
    for entry in CATALOGUE:
        item = {
            "id": entry["id"],
            "path": entry["path"],
            "schema": entry["schema"],
            "updated_at": updated_at(root / entry["file"]),
            "description": entry["description"],
        }
        feeds.append(item)
    return {
        "schema": "time.data-index.v1",
        "generated_at": now,
        "feeds": feeds,
    }


def write(root: Path = ROOT) -> Path:
    doc = build(root)
    out = root / "data" / "index.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return out


if __name__ == "__main__":
    path = write()
    print(f"wrote {path}")
