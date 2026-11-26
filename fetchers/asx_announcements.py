"""ASX company announcements fetcher (live).

Primary source: the public HTML list at
asx.com.au/asx/v2/statistics/announcements.do (gives the correct idsId for the
document link, Sydney-time timestamps and the price-sensitive marker).
Enrichment: the JSON endpoint asx.com.au's own company pages call
(asx.api.markitdigital.com/asx-research/1.0/companies/{code}/announcements)
adds the announcement type. Its documentKey is NOT the idsId (checked
27 Nov 2026: it resolves to a different document), so links never come from it.
If the HTML list fails, markit records are kept but link to the company's
ASX announcements page instead of a document.

Notes for operators:
- Neither endpoint is a documented public API. ASX's site terms limit use of
  its information to personal, non-commercial purposes; redistribution of
  announcement text needs an ASX licence. We store headline, time, type,
  price-sensitive flag and a link back to ASX only, never the document body.
- robots.txt on www.asx.com.au (checked 27 Nov 2026) disallows only /search*.
- Be gentle: one request per code, >= 1.5 s apart, a few runs a day at most.
- Runs server-side (GitHub Actions cron). The static site only reads the JSON
  this writes, so there are no cross-origin calls or keys in the browser.
"""
from __future__ import annotations

import datetime as dt
import html
import os
import re
import sys
import time
from typing import List, Dict, Tuple

if __package__ in (None, ""):
    sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__file__)))
from fetchers.schema import NormalisedRecord, WATCHED, AEST, http_json, http_get  # noqa: E402

FEED = "asx_announcements"
MARKIT = "https://asx.api.markitdigital.com/asx-research/1.0/companies/{code}/announcements?count={count}"
HTML_LIST = "https://www.asx.com.au/asx/v2/statistics/announcements.do?by=asxCode&asxCode={code}&timeframe=D&period=M6"
DISPLAY = "https://www.asx.com.au/asx/v2/statistics/displayAnnouncement.do?display=pdf&idsId={ids}"
DEFAULT_CODES = ["BHP", "RIO", "FMG", "LYC", "WHC", "ARU", "NTU"]
PAUSE_S = 1.5


def normalise_markit(code: str, item: Dict) -> NormalisedRecord:
    when = dt.datetime.fromisoformat(item["date"].replace("Z", "+00:00")).astimezone(AEST)
    ent = WATCHED.get(code, {})
    return NormalisedRecord(
        feed=FEED, entity=code, entity_name=ent.get("name"),
        event_type="asx_announcement",
        event_subtype=(item.get("announcementType") or "").strip().lower().replace(" ", "_") or None,
        occurred_at=when.isoformat(timespec="seconds"), published_at=when.isoformat(timespec="seconds"),
        title=(item.get("headline") or "").strip(),
        source_url=f"https://www.asx.com.au/markets/trade-our-cash-market/announcements.{code.lower()}",
        jurisdiction="AU", commodity=list(ent.get("commodity", [])),
        raw_confidence=0.9,  # issuer's own disclosure via the exchange
        price_sensitive=bool(item.get("isPriceSensitive")),
        needs_verification=True,
        extra={"document_key": item.get("documentKey"), "file_size": item.get("fileSize"), "via": "markit"},
    )


ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)


def parse_html_list(code: str, page: str) -> List[NormalisedRecord]:
    """Fallback parser for the asx.com.au announcements table (AEST/AEDT local times)."""
    out = []
    ent = WATCHED.get(code, {})
    for row in ROW.findall(page):
        ids = re.search(r"idsId=(\d+)", row)
        m = re.search(r"(\d{2})/(\d{2})/(\d{4})\s*(?:<[^>]*>\s*)*(\d{1,2}):(\d{2})\s*([ap]m)", row, re.S)
        if not ids or not m:
            continue
        d, mo, y, hh, mm, ap = m.groups()
        hh = int(hh) % 12 + (12 if ap == "pm" else 0)
        # The page shows Sydney local time (AEST/AEDT).
        when = dt.datetime(int(y), int(mo), int(d), hh, int(mm), tzinfo=AEST)
        a = re.search(r'<a[^>]*idsId=\d+[^>]*>(.*?)</a>', row, re.S)
        title = html.unescape(re.sub(r"<[^>]+>|\s+", " ", a.group(1) if a else "")).strip()
        title = re.sub(r"\s*\d+ pages?.*$", "", title).strip()
        out.append(NormalisedRecord(
            feed=FEED, entity=code, entity_name=ent.get("name"), event_type="asx_announcement", event_subtype=None,
            occurred_at=when.isoformat(timespec="seconds"), published_at=when.isoformat(timespec="seconds"),
            title=title, source_url=DISPLAY.format(ids=ids.group(1)), commodity=list(ent.get("commodity", [])),
            raw_confidence=0.9, price_sensitive=('title="price sensitive"' in row),
            extra={"ids_id": ids.group(1), "via": "asx_html"},
        ))
    return out


def _merge(html_recs: List[NormalisedRecord], markit_recs: List[NormalisedRecord]) -> List[NormalisedRecord]:
    """Take links from the HTML list; copy announcement type from markit when headline and minute match."""
    by_key = {(m.title.lower(), m.occurred_at[:16]): m for m in markit_recs}
    for h in html_recs:
        m = by_key.get((h.title.lower(), h.occurred_at[:16]))
        if m:
            h.event_subtype = m.event_subtype
            h.extra["via"] = "asx_html+markit"
    return html_recs


def fetch(codes: List[str] = None, count: int = 20) -> Tuple[List[Dict], Dict]:
    codes = codes or DEFAULT_CODES
    records, errors, per_code = [], {}, {}
    for i, code in enumerate(codes):
        if i:
            time.sleep(PAUSE_S)
        html_recs, markit_recs, errs = [], [], []
        try:
            html_recs = parse_html_list(code, http_get(HTML_LIST.format(code=code)).decode("utf-8", "replace"))[:count]
        except Exception as e:
            errs.append(f"html: {type(e).__name__}: {e}"[:200])
        time.sleep(PAUSE_S)
        try:
            data = http_json(MARKIT.format(code=code.lower(), count=count))
            markit_recs = [normalise_markit(code, it) for it in data.get("data", {}).get("items", [])]
        except Exception as e:
            errs.append(f"markit: {type(e).__name__}: {e}"[:200])
        got = _merge(html_recs, markit_recs) if html_recs else markit_recs
        if errs:
            errors[code] = " | ".join(errs)
        per_code[code] = len(got)
        if os.environ.get("TIME_PUBLISH_ASX_HEADLINES") != "1":
            for r in got:
                r.finalise()  # record_id is computed from the real headline first
                kind = (r.event_subtype or "announcement").replace("_", " ")
                r.title = f"{code} {kind}{' (price sensitive)' if r.price_sensitive else ''}: headline on ASX"
                r.extra["headline_withheld"] = True
        records += [r.to_dict() for r in got]
    status = "ok" if records and not errors else ("partial" if records else "error")
    return records, {"status": status, "per_entity": per_code, "errors": errors}


if __name__ == "__main__":
    import json
    recs, health = fetch(sys.argv[1:] or None, count=5)
    print(json.dumps({"health": health, "sample": recs[:3]}, ensure_ascii=False, indent=2))
