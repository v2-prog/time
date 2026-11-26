"""WA Department of Mines, Petroleum and Exploration (DMPE) fetcher (live).

DMPE took over WA resource regulation from DEMIRS (formerly DMIRS). Two public sources:

1. Agency announcements on wa.gov.au. The DMPE organisation page lists the latest
   announcements; each announcement page carries og:title, og:description and a
   <time datetime> element. wa.gov.au robots.txt does not disallow these paths.
2. Mining tenement grants from the "Mining Tenements (DMIRS-003)" dataset on
   data.wa.gov.au (CC BY 4.0), queried through the public SLIP ArcGIS REST
   service. No key needed. We ask only for attributes, never geometry.

Privacy: many tenement holders are private individuals. We keep a grant only
when a holder is a company (PTY / LTD / LIMITED etc.), and we publish only
company holder names. Personal names are dropped before anything is written.

Runs server-side (GitHub Actions cron); the static site reads the output JSON.
"""
from __future__ import annotations

import datetime as dt
import html
import re
import sys
import time
import urllib.parse
from typing import List, Dict, Tuple

if __package__ in (None, ""):
    sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__file__)))
from fetchers.schema import NormalisedRecord, AEST, http_get, http_json, resolve_entity, WATCHED  # noqa: E402
from fetchers.topics import topics_for  # noqa: E402

FEED_ANN = "wa_dmpe_announcements"
FEED_TEN = "wa_dmpe_tenements"
ORG_PAGE = "https://www.wa.gov.au/organisation/department-of-mines-petroleum-and-exploration"
BASE = "https://www.wa.gov.au"
TENEMENT_LAYER = ("https://public-services.slip.wa.gov.au/public/rest/services/"
                  "SLIP_Public_Services/Industry_and_Mining/MapServer/3/query")
TENEMENT_DATASET = "https://catalogue.data.wa.gov.au/dataset/mining-tenements-dmirs-003"
COMPANY = re.compile(r"\b(PTY|LTD|LIMITED|CORPORATION|CORP|INC|N\.?L\.?|LLC|PLC|GMBH|COMPANY)\b", re.I)
PAUSE_S = 1.0
WA = dt.timezone(dt.timedelta(hours=8))


def parse_org_links(page: str) -> List[str]:
    seen, out = set(), []
    for m in re.finditer(r'href="(/government/announcements/[a-z0-9-]+)"', page):
        if m.group(1) not in seen:
            seen.add(m.group(1)); out.append(BASE + m.group(1))
    return out


def parse_announcement(url: str, page: str) -> NormalisedRecord:
    def meta(p):
        m = re.search(r'<meta property="og:%s" content="([^"]*)"' % p, page)
        return html.unescape(m.group(1)).strip() if m else ""
    t = re.search(r'<time datetime="([^"]+)"', page)
    when = dt.datetime.fromisoformat(t.group(1)) if t else None
    title = meta("title")
    desc = meta("description")
    return NormalisedRecord(
        feed=FEED_ANN, entity=resolve_entity(title + " " + desc), entity_name=None,
        event_type="agency_announcement", event_subtype=None,
        occurred_at=when.isoformat() if when else "", published_at=when.isoformat() if when else "",
        title=title, source_url=url, jurisdiction="AU-WA", raw_confidence=0.95,
        extra={"summary": desc[:400], "agency": "DMPE", "topics": topics_for(title, desc)},
    )


def fetch_announcements(limit: int = 8) -> Tuple[List[NormalisedRecord], List[str]]:
    errs, out = [], []
    links = parse_org_links(http_get(ORG_PAGE).decode("utf-8", "replace"))[:limit]
    for url in links:
        time.sleep(PAUSE_S)
        try:
            out.append(parse_announcement(url, http_get(url).decode("utf-8", "replace")))
        except Exception as e:
            errs.append(f"{url}: {type(e).__name__}: {e}"[:200])
    return out, errs


def company_holders(attrs: Dict) -> List[str]:
    names = [(attrs.get(f"holder{i}") or "").strip() for i in range(1, 10)]
    return [n for n in names if n and COMPANY.search(n)]


def normalise_tenement(attrs: Dict) -> NormalisedRecord | None:
    holders = company_holders(attrs)
    if not holders:
        return None  # individual holders only: not published
    g = attrs.get("grantdate")
    if not g or g > 4102444800000:  # pending tenements carry a year-3000 sentinel
        return None
    granted = dt.datetime.fromtimestamp(g / 1000, dt.timezone.utc).astimezone(WA).date()
    extracted = attrs.get("extract_da")
    pub = (dt.datetime.fromtimestamp(extracted / 1000, dt.timezone.utc).astimezone(AEST).isoformat(timespec="seconds")
           if extracted else granted.isoformat())
    ent = None
    for h in holders:
        ent = ent or resolve_entity(h)
    tid = attrs.get("fmt_tenid") or ""
    return NormalisedRecord(
        feed=FEED_TEN, entity=ent, entity_name=holders[0],
        event_type="mining_lease_granted" if (attrs.get("type") or "").upper() == "MINING LEASE" else "tenement_granted",
        event_subtype=(attrs.get("type") or "").lower().replace(" ", "_"),
        occurred_at=granted.isoformat(), published_at=pub,
        title=f"{attrs.get('type','Tenement').title()} {tid} granted to {holders[0]}",
        source_url=TENEMENT_DATASET, jurisdiction="AU-WA",
        commodity=list(WATCHED.get(ent, {}).get("commodity", [])) if ent else [],
        raw_confidence=0.95,
        extra={"tenement_id": tid, "status": attrs.get("tenstatus"), "holders": holders,
               "area": attrs.get("legal_area"), "area_unit": (attrs.get("unit_of_me") or "").strip(),
               "agency": "DMPE", "licence": "CC BY 4.0 (data.wa.gov.au, DMIRS-003)",
               "topics": ["approval", "mining_lease"] if (attrs.get("type") or "").upper() == "MINING LEASE" else ["approval"]},
    )


def fetch_tenements(days: int = 60, types=("MINING LEASE", "GENERAL PURPOSE LEASE", "RETENTION LICENCE")) -> List[NormalisedRecord]:
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    tlist = ",".join(f"'{t}'" for t in types)
    q = {
        "where": f"grantdate >= DATE '{since}' AND grantdate < DATE '2100-01-01' AND type IN ({tlist})",
        "outFields": "fmt_tenid,type,tenstatus,holder1,holder2,holder3,holder4,holder5,holder6,holder7,holder8,holder9,grantdate,legal_area,unit_of_me,extract_da",
        "returnGeometry": "false", "orderByFields": "grantdate DESC", "resultRecordCount": "500", "f": "json",
    }
    data = http_json(TENEMENT_LAYER + "?" + urllib.parse.urlencode(q), timeout=60)
    if "error" in data:
        raise RuntimeError(str(data["error"])[:200])
    out = [normalise_tenement(f["attributes"]) for f in data.get("features", [])]
    return [r for r in out if r]


def fetch() -> Dict[str, Tuple[List[Dict], Dict]]:
    res = {}
    try:
        ann, errs = fetch_announcements()
        res[FEED_ANN] = ([r.to_dict() for r in ann], {"status": "ok" if ann and not errs else ("partial" if ann else "error"), "errors": errs})
    except Exception as e:
        res[FEED_ANN] = ([], {"status": "error", "errors": [f"{type(e).__name__}: {e}"[:200]]})
    try:
        ten = fetch_tenements()
        res[FEED_TEN] = ([r.to_dict() for r in ten], {"status": "ok" if ten else "silent", "errors": []})
    except Exception as e:
        res[FEED_TEN] = ([], {"status": "error", "errors": [f"{type(e).__name__}: {e}"[:200]]})
    return res


if __name__ == "__main__":
    import json
    for feed, (recs, health) in fetch().items():
        print(feed, json.dumps(health), len(recs))
        for r in recs[:3]:
            print("  ", r["occurred_at"], r["entity"], r["title"][:90])
