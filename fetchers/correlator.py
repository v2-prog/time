"""Matching engine (correlator_core for the Resources variant).

Scores every fetched record against every policy/regulatory event in
data/policy_timeline.json and writes ranked, explainable matches to
data/matches.json, next to the hand-seeded ones.

A match only says that two events sit close in time with shared scope. It does
not show cause and is not a recommendation.

Score (0-1), each part reported in the output:
  temporal  = 1 - |lag_days| / 31          (lead-lag windows of 7, 14 and 30 days either side)
  entity    = 1.0 if the record's canonical entity is named by the policy event,
              0.5 if it only shares a commodity with the event, else 0 (no match)
  topic     = shared topic/commodity tags / min(3, tags on the policy event), capped at 1
  source    = the feed's raw_confidence (how authoritative the feed is)
  base      = 0.30 temporal + 0.30 entity + 0.25 topic + 0.15 source
  score     = base x volatility weight (low 1.0, medium 0.9, high 0.8)
                   x verification factor (0.85 if the policy event still carries verify: true)
Gates: entity > 0; at least one non-routine shared topic, or a binary event
(tenement grant) for the same entity; score >= MIN_SCORE. If a rationale
can't be written from the parts, the match is dropped.

Confidence is separate from score and mechanical:
  0.4 x feed freshness + 0.3 x (policy verified) + 0.3 x (record verified)
Live records are unverified until someone opens the source, so their confidence
tops out at 0.7.

Licensing: ASX headlines are never read here. Matching uses ticker, time,
announcement type, price-sensitive flag and topic tags. The fetcher derives
the tags from the headline in memory and publishes only the tags.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fetchers.schema import WATCHED, AEST  # noqa: E402
from fetchers.topics import ROUTINE  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
WINDOWS = (7, 14, 30)
MAX_LAG = 30
MIN_SCORE = 0.5
VOL_W = {"low": 1.0, "medium": 0.9, "high": 0.8}
KEEP_DAYS = 400  # engine matches stay listed this long after their record drops out of the feed
BRACKET = {"Materials": "Resources", "Energy": "Energy"}
BINARY_EVENTS = {"mining_lease_granted", "tenement_granted"}


def _date(s: str) -> dt.date:
    return dt.date.fromisoformat(s[:10])


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def record_tags(r: Dict) -> set:
    return set((r.get("extra") or {}).get("topics") or []) | set(r.get("commodity") or [])


def freshness(feed_entry: Dict, now: dt.datetime, stale_hours: float) -> float:
    if not feed_entry or not feed_entry.get("last_success"):
        return 0.0
    age = (now - dt.datetime.fromisoformat(feed_entry["last_success"])).total_seconds() / 3600
    return max(0.0, min(1.0, 1 - (age - stale_hours) / (3 * stale_hours)))


def score_pair(r: Dict, p: Dict, fresh: float = 1.0):
    """Return a match dict or None. Pure function: easy to test."""
    ent = r.get("entity")
    if not r.get("occurred_at"):
        return None
    lag = (_date(r["occurred_at"]) - _date(p["date"])).days
    if abs(lag) > MAX_LAG:
        return None
    p_ents = set(p.get("entities") or [])
    p_tags = set(p.get("topics") or []) | set(p.get("commodity") or [])
    r_tags = record_tags(r)
    if ent and ent in p_ents:
        entity, entity_basis = 1.0, "named entity"
    elif ent and set(WATCHED.get(ent, {}).get("commodity", [])) & set(p.get("commodity") or []):
        entity, entity_basis = 0.5, "shared commodity"
    else:
        return None
    shared = sorted((r_tags & p_tags) - ROUTINE)
    non_commodity = [t for t in shared if t not in set(p.get("commodity") or [])]
    binary = r.get("event_type") in BINARY_EVENTS and entity == 1.0
    if not non_commodity and not binary:
        return None
    if r_tags & ROUTINE and not non_commodity:
        return None
    temporal = 1 - abs(lag) / (MAX_LAG + 1)
    topic = min(1.0, len(shared) / max(1, min(3, len(p_tags))))
    source = float(r.get("raw_confidence") or 0.5)
    base = 0.30 * temporal + 0.30 * entity + 0.25 * topic + 0.15 * source
    vol = VOL_W.get(p.get("volatility"), 0.8)
    ver = 0.85 if p.get("verify") else 1.0
    score = round(base * vol * ver, 3)
    if score < MIN_SCORE:
        return None
    window = next(w for w in WINDOWS if abs(lag) <= w)
    when = "the same day as" if lag == 0 else (f"{abs(lag)} days after" if lag > 0 else f"{abs(lag)} days before")
    kind = (r.get("event_type") or "record").replace("_", " ")
    if r.get("price_sensitive"):
        kind = "price-sensitive " + kind
    rationale = (f"{ent} {kind} on {r['occurred_at'][:10]} came {when} \"{p['title']}\" "
                 f"({p.get('date_kind', 'dated')} {p['date']}); linked by {entity_basis} {ent} and shared tags "
                 f"{', '.join(shared) or 'none'}.")
    if not shared and not binary:
        return None
    flags = ["record_unverified"] if r.get("needs_verification", True) else []
    if p.get("verify"):
        flags.append("policy_verify")
    if p.get("boundary_class"):
        flags.append("boundary_event_policy_or_commercial")
    if (r.get("extra") or {}).get("headline_withheld"):
        flags.append("matched_on_metadata_and_tags")
    if p.get("date_kind") == "scheduled":
        flags.append("scheduled_future_event")
    confidence = round(0.4 * fresh + 0.3 * (0 if p.get("verify") else 1) + 0.3 * (0 if r.get("needs_verification", True) else 1), 2)
    gics = WATCHED.get(ent, {}).get("gics")
    return {
        "id": f"e-{r['record_id']}-{p['id']}", "origin": "engine",
        "record": {"record_id": r["record_id"], "feed": r["feed"], "entity": ent, "entity_name": r.get("entity_name"),
                   "event_type": r.get("event_type"), "event_subtype": r.get("event_subtype"),
                   "date": r["occurred_at"], "title": r.get("title"), "source": r.get("source_url"),
                   "price_sensitive": r.get("price_sensitive"), "tags": sorted(r_tags)},
        "policy": {"ref": p["id"], "title": p["title"], "date": p["date"], "direction": p.get("direction_for_resources"),
                   "verify": bool(p.get("verify")), "verification_ref": p.get("ref")},
        "lag_days": lag, "window_days": window,
        "score": score,
        "parts": {"temporal": round(temporal, 3), "entity": entity, "topic": round(topic, 3), "source": source,
                  "volatility_weight": vol, "verification_factor": ver},
        "confidence": confidence, "bracket": BRACKET.get(gics), "in_asx200_scope": WATCHED.get(ent, {}).get("asx200"),
        "shared_tags": shared, "rationale": rationale, "flags": flags, "verify": True,
    }


def bracket_activity(matches: List[Dict], window_days: int = 30) -> Dict:
    """Engine match counts per bracket in non-overlapping windows (oldest first) for Rotation's z-score."""
    out = {}
    dated = [m for m in matches if m.get("bracket")]
    if not dated:
        return out
    start = min(_date(m["record"]["date"]) for m in dated)
    for m in dated:
        idx = (_date(m["record"]["date"]) - start).days // window_days
        b = out.setdefault(m["bracket"], {})
        b[idx] = b.get(idx, 0) + 1
    res = {}
    for b, counts in out.items():
        n = max(counts) + 1
        res[b] = {"window_days": window_days, "start": start.isoformat(), "counts": [counts.get(i, 0) for i in range(n)]}
    return res


def run(now: dt.datetime | None = None) -> Dict:
    now = now or dt.datetime.now(AEST)
    timeline = _load(os.path.join(DATA, "policy_timeline.json"), {"events": []})["events"]
    health = _load(os.path.join(DATA, "feed_health.json"), {"feeds": []})
    hmap = {f["id"]: f for f in health.get("feeds", [])}
    stale = health.get("stale_after_hours", 36)
    feeds_dir = os.path.join(DATA, "feeds")
    records = []
    for name in sorted(os.listdir(feeds_dir)) if os.path.isdir(feeds_dir) else []:
        if name.endswith(".json"):
            records += _load(os.path.join(feeds_dir, name), {"records": []}).get("records", [])
    fresh = {fid: freshness(f, now, stale) for fid, f in hmap.items()}

    new = {}
    for r in records:
        for p in timeline:
            m = score_pair(r, p, fresh.get(r.get("feed"), 0.0))
            if m:
                new[m["id"]] = m

    path = os.path.join(DATA, "matches.json")
    prev = _load(path, {})
    seeded = prev.get("seeded") or [dict(m, origin="seeded") for m in prev.get("matches", [])]
    for m in seeded:
        m["origin"] = "seeded"
    cutoff = (now.date() - dt.timedelta(days=KEEP_DAYS)).isoformat()
    for m in prev.get("engine", []):  # keep earlier engine matches whose record has dropped out of the feed
        if m["id"] not in new and m["record"]["date"][:10] >= cutoff:
            new[m["id"]] = dict(m, archived=True)
    engine = sorted(new.values(), key=lambda m: (-m["score"], m["record"]["date"]), reverse=False)
    for i, m in enumerate(engine, 1):
        m["rank"] = i
    out = {
        "note": prev.get("note") or "Matches record temporal proximity and shared scope only. No causation, no recommendations.",
        "generated_at": now.isoformat(timespec="seconds"),
        "scoring": (__doc__.split("Score (0-1), each part reported in the output:")[1].split("Licensing:")[0]).strip(),
        "seeded_scoring": "Seeded matches: temporal = 1 - |lag_days|/30; entity = 1.0 same entity, 0.6 named counterparty; commodity = 1.0 match else 0; x volatility weight (low 1.0, medium 0.9, high 0.8). Computed in the browser from score_inputs.",
        "licensing": "ASX headlines are not used or published; engine matches use ticker, time, type, price-sensitive flag and topic tags.",
        "counts": {"seeded": len(seeded), "engine": len(engine), "engine_live": sum(not m.get("archived") for m in engine)},
        "bracket_activity": bracket_activity(engine),
        "seeded": seeded,
        "engine": engine,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    return out


if __name__ == "__main__":
    o = run()
    print(json.dumps({"counts": o["counts"], "top": [
        {k: m[k] for k in ("rank", "score", "confidence", "lag_days")} | {"entity": m["record"]["entity"], "policy": m["policy"]["ref"],
         "tags": m["shared_tags"]} for m in o["engine"][:8]]}, indent=1))
