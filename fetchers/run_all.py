"""Run every live fetcher, write same-origin JSON for the static site, and update feed health.

Usage: python3 fetchers/run_all.py            (writes data/feeds/*.json and data/feed_health.json)

A failed fetch never wipes earlier good data: the previous records are kept and
the feed is marked error/stale, so the dashboard shows silence instead of hiding it.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fetchers import asx_announcements, wa_dmpe  # noqa: E402
from fetchers.schema import AEST  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEEDS_DIR = os.path.join(ROOT, "data", "feeds")
HEALTH = os.path.join(ROOT, "data", "feed_health.json")
STALE_HOURS = 36  # weekday cron; a feed older than this is "stale"

# Every feed named in the iteration 038 spec (as corrected in CORRECTIONS.md).
# Only the ones with a fetcher are live; the rest are listed honestly as never_run.
REGISTRY = [
    ("asx_announcements", "ASX company announcements (Resources codes)", "live"),
    ("wa_dmpe_announcements", "WA DMPE agency announcements", "live"),
    ("wa_dmpe_tenements", "WA DMPE tenement grants (DMIRS-003, CC BY 4.0)", "live"),
    ("asic_disclosures", "ASIC disclosures and substantial holder notices", "never_run"),
    ("abares", "ABARES agricultural production and export data (barley, wine precedents)", "never_run"),
    ("disr_req", "DISR Office of the Chief Economist: Resources and Energy Quarterly", "never_run"),
    ("qld_nrmmrrd", "Qld NRMMRRD mining approvals", "never_run"),
    ("nsw_resources", "NSW Resources (DPIRD) titles and approvals", "never_run"),
    ("nt_dme", "NT Department of Mining and Energy mineral titles", "never_run"),
    ("nt_dlpe", "NT Dept of Lands, Planning and Environment mining environmental licences", "never_run"),
    ("sa_dem", "SA Department for Energy and Mining", "never_run"),
    ("vic_err", "Vic Earth Resources Regulation (name unchecked)", "never_run"),
    ("tas_mrt", "Mineral Resources Tasmania (name unchecked)", "never_run"),
    ("epbc_notices", "EPBC public notices and decisions (DCCEEW)", "never_run"),
    ("firb_treasury", "FIRB / Treasury orders on the Federal Register of Legislation", "never_run"),
    ("ga_critical_minerals", "Geoscience Australia critical minerals assessments", "never_run"),
    ("aus_policy", "Commonwealth policy releases (Critical Minerals Strategy, incentives)", "never_run"),
    ("dfat_trade", "DFAT trade and investment announcements", "never_run"),
    ("china_customs", "China customs (GACC) monthly imports of Australian commodities", "never_run"),
    ("mofcom", "MOFCOM / GACC announcements (trade remedies, export controls)", "never_run"),
    ("jp_kr_offtake", "Japanese and Korean offtake and investment announcements", "never_run"),
    ("port_throughput", "Port throughput (Pilbara Ports, Gladstone, Darwin, Townsville)", "never_run"),
    ("ais_vessels", "AIS vessel tracking (optional)", "never_run"),
]


def now_iso() -> str:
    return dt.datetime.now(AEST).isoformat(timespec="seconds")


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write("\n")


def latest(records):
    ds = sorted((r.get("occurred_at") or "") for r in records)
    return ds[-1] if ds else None


def main():
    prev = {f["id"]: f for f in load(HEALTH, {}).get("feeds", [])}
    results = {}
    recs, h = asx_announcements.fetch()
    results["asx_announcements"] = (recs, h)
    results.update(wa_dmpe.fetch())

    feeds = []
    for fid, label, kind in REGISTRY:
        p = prev.get(fid, {})
        entry = {"id": fid, "label": label, "kind": kind, "status": "never_run", "last_run": None,
                 "last_success": None, "records": 0, "latest_event": None, "errors": [], "per_entity": {}}
        if fid in results:
            recs, h = results[fid]
            path = os.path.join(FEEDS_DIR, f"{fid}.json")
            entry["last_run"] = now_iso()
            if recs:
                write(path, {"feed": fid, "generated_at": now_iso(), "records": recs})
                entry.update(status=h["status"], last_success=now_iso(), records=len(recs), latest_event=latest(recs))
            else:
                old = load(path, {"records": []})["records"]
                entry.update(status="error" if h["status"] == "error" else "silent", last_success=p.get("last_success"),
                             records=len(old), latest_event=latest(old))
            entry["errors"] = h.get("errors") if isinstance(h.get("errors"), list) else [f"{k}: {v}" for k, v in h.get("errors", {}).items()]
            entry["per_entity"] = h.get("per_entity", {})
        feeds.append(entry)
    live = [f for f in feeds if f["kind"] == "live"]
    write(HEALTH, {
        "generated_at": now_iso(), "stale_after_hours": STALE_HOURS,
        "summary": {"total": len(feeds), "live_ok": sum(f["status"] == "ok" for f in live),
                    "live_problem": sum(f["status"] not in ("ok",) for f in live),
                    "never_run": sum(f["status"] == "never_run" for f in feeds)},
        "feeds": feeds,
    })
    bad = [f["id"] for f in live if f["status"] not in ("ok", "partial")]
    print(json.dumps({"ok": not bad, "problem_feeds": bad, "counts": {f["id"]: f["records"] for f in live}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
