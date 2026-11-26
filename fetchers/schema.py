"""NormalisedRecord: the one shape every feed is converted into (iteration 038, layer one).

Fields follow the AusResourcesCorrelator spec: entity, event type and subtype,
occurrence and publication timestamps, stated monetary value, commodity,
origin/destination, jurisdiction, source URL and a raw-confidence score that
reflects how authoritative the feed is (not how important the event is).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import urllib.request
from dataclasses import dataclass, field, asdict
from typing import Optional, List

from zoneinfo import ZoneInfo

# Sydney local time (AEST/AEDT), the market's clock.
AEST = ZoneInfo("Australia/Sydney")
USER_AGENT = "time.vilo.au-feed/1.0 (+https://time.vilo.au; general information research, low rate)"

# Canonical entities the Resources feeds watch. Aliases are for matching only.
WATCHED = {
    "BHP": {"name": "BHP Group Limited", "commodity": ["iron_ore", "copper", "met_coal"], "gics": "Materials", "asx200": True,
            "aliases": ["BHP", "BHP GROUP", "BHP BILLITON", "BHP IRON ORE", "必和必拓"]},
    "RIO": {"name": "Rio Tinto Limited", "commodity": ["iron_ore", "aluminium", "copper"], "gics": "Materials", "asx200": True,
            "aliases": ["RIO TINTO", "HAMERSLEY", "ROBE RIVER"]},
    "FMG": {"name": "Fortescue Ltd", "commodity": ["iron_ore"], "gics": "Materials", "asx200": True,
            "aliases": ["FORTESCUE", "FMG ", "PILBARA IRON ORE"]},
    "LYC": {"name": "Lynas Rare Earths Limited", "commodity": ["rare_earths"], "gics": "Materials", "asx200": True,
            "aliases": ["LYNAS"]},
    "WHC": {"name": "Whitehaven Coal Limited", "commodity": ["thermal_coal", "met_coal"], "gics": "Energy", "asx200": True,
            "aliases": ["WHITEHAVEN"]},
    "ARU": {"name": "Arafura Rare Earths Limited", "commodity": ["rare_earths"], "gics": "Materials", "asx200": False,
            "aliases": ["ARAFURA"]},
    "NTU": {"name": "Northern Minerals Limited", "commodity": ["rare_earths"], "gics": "Materials", "asx200": False,
            "aliases": ["NORTHERN MINERALS"]},
    "MIN": {"name": "Mineral Resources Limited", "commodity": ["iron_ore", "lithium"], "gics": "Materials", "asx200": True,
            "aliases": ["MINERAL RESOURCES"]},
}


@dataclass
class NormalisedRecord:
    feed: str
    entity: Optional[str]            # canonical code (e.g. "BHP") or None when unresolved
    entity_name: Optional[str]
    event_type: str                  # e.g. asx_announcement, mining_lease_granted, agency_announcement
    event_subtype: Optional[str]
    occurred_at: str                 # ISO 8601 with offset
    published_at: str
    title: str
    source_url: str
    jurisdiction: str = "AU"
    commodity: List[str] = field(default_factory=list)
    value_aud: Optional[float] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    raw_confidence: float = 0.5
    price_sensitive: Optional[bool] = None
    needs_verification: bool = True   # stays true until a human checks the primary document
    direction: str = "unassigned"     # Rotation direction tag; set by documented rules, never by a fetcher
    extra: dict = field(default_factory=dict)
    fetched_at: str = ""
    record_id: str = ""

    def finalise(self) -> "NormalisedRecord":
        if not self.fetched_at:
            self.fetched_at = dt.datetime.now(AEST).isoformat(timespec="seconds")
        if not self.record_id:
            key = f"{self.feed}|{self.entity}|{self.occurred_at}|{self.title}|{self.source_url}"
            self.record_id = hashlib.sha1(key.encode()).hexdigest()[:16]
        return self

    def to_dict(self) -> dict:
        return asdict(self.finalise())


def resolve_entity(text: str) -> Optional[str]:
    """Return a canonical code only on an unambiguous alias hit; otherwise None (park, don't guess)."""
    up = (text or "").upper()
    hits = [code for code, e in WATCHED.items() if any(a.upper() in up for a in e["aliases"])]
    return hits[0] if len(hits) == 1 else None


def http_get(url: str, timeout: int = 30, accept: str = "*/*") -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def http_json(url: str, timeout: int = 30):
    return json.loads(http_get(url, timeout, "application/json"))
