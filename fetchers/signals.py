"""Gov signals feed: verified, strength-rated government and regulatory events that may bear on ASX-listed stocks.

Input  : data/signals/events.json  (curated by hand; every figure comes from a linked source)
         data/signals/tickers.json (ASX code -> name and GICS industry group, from the ASX listed-companies list)
         data/matches.json         (engine matches from fetchers/correlator.py; linked by ticker, read only)
         Sector Watch JSON          (optional; --sector-watch DIR or SECTOR_WATCH_DIR; newest signals-YYYY-MM-DD.json, read only)
Output : data/signals/signals.json        canonical feed (schema: data/signals/schema.json, gov.signal.v1)
         data/signals/ratio-signals.json  same signals in tt's ratio.signal.v1 contract, heat-map intersections only

General information only. Australia only. Not personal financial or legal advice. The feed carries
no buy/sell/hold calls, entry points, ladders or broker names; validate() refuses any that appear.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
SYD = ZoneInfo("Australia/Sydney")
SCHEMA = "gov.signal.v1"
RUBRIC_VERSION = "strength-rubric-v1"
DISCLAIMER = ("General information only, Australia only. Not personal financial or legal advice. "
              "No buy, sell or hold calls, entry points or ladders. Verify against the linked primary source before relying on any item.")

# ---------- rubric (documented in data/signals/README.md) ----------
WEIGHTS = {"materiality": 0.35, "certainty": 0.25, "directness": 0.25, "source": 0.15}
COMPONENT_RANGE = {"materiality": (0, 3), "certainty": (0, 3), "directness": (0, 3), "source": (1, 3)}
BANDS = [(0.85, 5), (0.65, 4), (0.45, 3), (0.25, 2), (0.0, 1)]
CAPS = {"secondary_only": 3, "needs_human_verification": 2}
EXPOSURE_UNVERIFIED_CAP = 4

VERIFICATION = ("confirmed_primary", "secondary_only", "needs_human_verification")
DIRECTIONS = ("headwind", "tailwind", "mixed")
TIMEFRAMES = ("days", "weeks", "months", "years")  # same vocabulary as ASX 200 Sector Watch

# GICS industry group -> GICS sector (GICS 2023 structure)
GICS_SECTOR = {
    "Energy": "Energy", "Materials": "Materials",
    "Capital Goods": "Industrials", "Commercial & Professional Services": "Industrials", "Transportation": "Industrials",
    "Automobiles & Components": "Consumer Discretionary", "Consumer Durables & Apparel": "Consumer Discretionary",
    "Consumer Services": "Consumer Discretionary", "Consumer Discretionary Distribution & Retail": "Consumer Discretionary",
    "Retailing": "Consumer Discretionary",
    "Consumer Staples Distribution & Retail": "Consumer Staples", "Food & Staples Retailing": "Consumer Staples",
    "Food, Beverage & Tobacco": "Consumer Staples", "Household & Personal Products": "Consumer Staples",
    "Health Care Equipment & Services": "Health Care", "Pharmaceuticals, Biotechnology & Life Sciences": "Health Care",
    "Banks": "Financials", "Financial Services": "Financials", "Diversified Financials": "Financials", "Insurance": "Financials",
    "Software & Services": "Information Technology", "Technology Hardware & Equipment": "Information Technology",
    "Semiconductors & Semiconductor Equipment": "Information Technology",
    "Telecommunication Services": "Communication Services", "Media & Entertainment": "Communication Services",
    "Utilities": "Utilities",
    "Equity Real Estate Investment Trusts (REITs)": "Real Estate", "Real Estate Management & Development": "Real Estate",
}
# Woods Rotation brackets (time/rotation/data.js; correlator BRACKET). Other sectors sit outside the five brackets.
BRACKET = {"Materials": "Resources", "Energy": "Energy", "Financials": "Financials", "Health Care": "Healthcare", "Industrials": "Industrials"}
# S&P/ASX 200 sector index codes, used to join sector-level Sector Watch cells (codes only; no index data is shipped).
SECTOR_INDEX = {"Energy": "XEJ", "Materials": "XMJ", "Industrials": "XNJ", "Consumer Discretionary": "XDJ", "Consumer Staples": "XSJ",
                "Health Care": "XHJ", "Financials": "XFJ", "Information Technology": "XIJ", "Communication Services": "XTJ",
                "Utilities": "XUJ", "Real Estate": "XRE"}
# Sector Watch writes "Healthcare"; GICS writes "Health Care".
SW_SECTOR_ALIASES = {"Healthcare": "Health Care"}

ASX_HOLIDAYS = {"2026-12-25", "2026-12-28", "2027-01-01", "2027-01-26"}  # from time/rotation/data.js; confirm yearly
ADVICE_TEXT = re.compile(r"\b(we recommend|you should (buy|sell|hold)|buy now|sell now|entry point|target price|price target|strong buy|accumulate|take profit|stop[- ]loss|ladder)\b", re.I)
ADVICE_KEY = re.compile(r"(recommend|suggest|entry|ladder|target_?price|broker_?(name|pick))", re.I)


def load(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if default is not None:
            return default
        raise


def strength(rubric: dict, verification: str, exposure_verified: bool) -> dict:
    parts = {}
    for k, (lo, hi) in COMPONENT_RANGE.items():
        v = rubric[k]["value"]
        if not isinstance(v, int) or not lo <= v <= hi:
            raise ValueError(f"rubric {k} must be an integer {lo}..{hi}, got {v!r}")
        parts[k] = v
    weighted = round(sum(WEIGHTS[k] * parts[k] for k in WEIGHTS) / 3, 3)
    raw = next(s for floor, s in BANDS if weighted >= floor)
    caps = []
    cap = 5
    if verification in CAPS:
        cap = min(cap, CAPS[verification]); caps.append(f"{verification} caps strength at {CAPS[verification]}")
    if not exposure_verified:
        cap = min(cap, EXPOSURE_UNVERIFIED_CAP); caps.append(f"ticker exposure not stated in source caps strength at {EXPOSURE_UNVERIFIED_CAP}")
    return {"value": min(raw, cap), "uncapped": raw, "weighted_score": weighted, "caps_applied": caps if cap < raw else [],
            "components": {k: rubric[k] for k in WEIGHTS}, "rubric_version": RUBRIC_VERSION}


def timeframe_for(ev: dict, as_of: dt.date):
    if ev.get("timeframe_override"):
        return ev["timeframe_override"], ev.get("timeframe_basis", "override")
    bucket = lambda n: "days" if n <= 10 else "weeks" if n <= 56 else "months" if n <= 365 else "years"
    eff = ev.get("effect_date")
    if eff:
        days = (dt.date.fromisoformat(eff) - as_of).days
        return bucket(days), f"Effect or decision date {eff} is {days} days from as-of"
    since = (as_of - dt.date.fromisoformat(ev["date"])).days
    return bucket(since), f"No dated effect or decision in the source; bucketed by recency (event {since} days before as-of)"


def next_trading_day(d: dt.date) -> dt.date:
    d = d + dt.timedelta(days=1)
    while d.weekday() >= 5 or d.isoformat() in ASX_HOLIDAYS:
        d += dt.timedelta(days=1)
    return d


def ticker_index(tickers_doc: dict) -> dict:
    out = {}
    for t in tickers_doc["tickers"]:
        sector = GICS_SECTOR.get(t["gics_industry_group"])
        out[t["code"]] = {**t, "gics_sector": sector, "bracket": BRACKET.get(sector)}
    return out


def latest_sector_watch(sw_dir):
    if not sw_dir or not os.path.isdir(sw_dir):
        return None, None
    files = sorted(glob.glob(os.path.join(sw_dir, "signals-*.json")))
    if not files:
        return None, None
    return load(Path(files[-1])), os.path.basename(files[-1])


def sw_cells(sw: dict):
    """Minimal, non-price subset of Sector Watch cells: id, instrument, sector, timeframe, colour, conviction."""
    out = []
    for c in sw.get("signals", []):
        sector = SW_SECTOR_ALIASES.get(c.get("sector"), c.get("sector"))
        out.append({"id": c.get("id"), "instrument": c.get("instrument"), "sector": sector, "timeframe": c.get("timeframe"),
                    "colour": c.get("colour"), "conviction": c.get("conviction"), "horizon_type": c.get("horizon_type"),
                    "needs_verification": c.get("needs_verification")})
    return out


def join_heatmap(sig: dict, cells, sw_meta):
    key = {"instruments": [a["code"] for a in sig["affected"]], "gics_sectors": sig["gics_sectors"],
           "sector_index_codes": [SECTOR_INDEX[s] for s in sig["gics_sectors"] if s in SECTOR_INDEX], "timeframe": sig["timeframe"]}
    if cells is None:
        return {"status": "awaiting_sector_watch", "join_key": key, "intersects": False, "ticker_cells": [], "sector_cells": []}
    tick = [c for c in cells if c["instrument"] in key["instruments"]]
    sect = [c for c in cells if c["instrument"] in key["sector_index_codes"] or (c["sector"] in key["gics_sectors"] and c["instrument"] not in key["instruments"] and c["instrument"] in SECTOR_INDEX.values())]
    level = "ticker" if tick else "sector" if sect else None
    same_tf = [c["id"] for c in tick + sect if sig["timeframe"] and c["timeframe"] == sig["timeframe"]]
    return {"status": "joined" if level else "no_intersection", "sector_watch_file": sw_meta, "join_key": key,
            "intersects": bool(level), "level": level, "ticker_cells": tick, "sector_cells": sect, "same_timeframe_cells": same_tf}


def build(events_doc: dict, tickers_doc: dict, matches_doc: dict, sw_doc, sw_name, now: dt.datetime):
    as_of = now.date()
    tix = ticker_index(tickers_doc)
    cells = sw_cells(sw_doc) if sw_doc else None
    sw_meta = {"file": sw_name, "generated_at": sw_doc.get("generated_at"), "session_as_of": sw_doc.get("session_as_of")} if sw_doc else None
    engine = matches_doc.get("engine", []) if matches_doc else []
    signals, problems = [], []
    for ev in events_doc["events"]:
        try:
            v = ev["verification"]["status"]
            if v not in VERIFICATION: raise ValueError(f"verification.status {v!r}")
            if ev["direction"] not in DIRECTIONS: raise ValueError(f"direction {ev['direction']!r}")
            if not ev.get("sources") or not all(s.get("url", "").startswith("https://") for s in ev["sources"]):
                raise ValueError("every event needs at least one https source")
            if not ev.get("reasoning"): raise ValueError("reasoning missing")
            affected = []
            for t in ev.get("tickers", []):
                ref = tix.get(t["code"])
                if not ref: raise ValueError(f"ticker {t['code']} not in tickers.json (ASX list check)")
                affected.append({"code": t["code"], "name": ref["name"], "gics_industry_group": ref["gics_industry_group"],
                                 "gics_sector": ref["gics_sector"], "bracket": ref["bracket"], "role": t["role"],
                                 "exposure_in_source": t["exposure_in_source"], "direction": t.get("direction", ev["direction"]),
                                 "asx200_member": None})
            sectors = sorted({a["gics_sector"] for a in affected if a["gics_sector"]} | set(ev.get("sector_level", [])))
            exposure_ok = all(a["exposure_in_source"] for a in affected) if affected else True
            st = strength(ev["rubric"], v, exposure_ok)
            tf, tf_basis = timeframe_for(ev, as_of)
            primary = next((s for s in ev["sources"] if s["kind"] == "primary"), ev["sources"][0])
            fired = dt.datetime.combine(dt.date.fromisoformat(ev["date"]), dt.time(0, 0), SYD)
            verify_items = list(ev["verification"].get("notes", []))
            if not exposure_ok:
                verify_items.append("Ticker exposure is general knowledge, not stated in the source: " + ", ".join(a["code"] for a in affected if not a["exposure_in_source"]))
            related = [m["id"] for m in engine if m.get("record", {}).get("entity") in {a["code"] for a in affected}]
            sig = {
                "id": ev["id"], "event": ev["title"], "category": ev["category"], "jurisdiction": ev["jurisdiction"],
                "date": ev["date"], "date_kind": ev["date_kind"], "time_precision": "date",
                "effect_date": ev.get("effect_date"), "effect_date_precision": ev.get("effect_date_precision", "day" if ev.get("effect_date") else None),
                "key_dates": ev.get("key_dates", []),
                "source_url": primary["url"], "source_kind": primary["kind"], "sources": ev["sources"],
                "affected": affected, "gics_sectors": sectors,
                "brackets": sorted({BRACKET[s] for s in sectors if s in BRACKET}),
                "outside_brackets": sorted(s for s in sectors if s not in BRACKET),
                "direction": ev["direction"], "strength": st, "reasoning": ev["reasoning"],
                "timeframe": tf, "timeframe_basis": tf_basis,
                "verification": {"status": v, "items": verify_items, **{k: ev["verification"][k] for k in ("origin", "regulator") if k in ev["verification"]}},
                "earliest_actionable_at": dt.datetime.combine(next_trading_day(fired.date()), dt.time(10, 0), SYD).isoformat(),
                "related_engine_matches": related,
                "label": "General information, not financial or legal advice.",
            }
            sig["heatmap"] = join_heatmap(sig, cells, sw_meta)
            signals.append(sig)
        except (KeyError, ValueError) as e:
            problems.append({"id": ev.get("id"), "problem": str(e)})
    signals.sort(key=lambda s: (-s["strength"]["value"], VERIFICATION.index(s["verification"]["status"]), -s["strength"]["weighted_score"], s["id"]))
    for i, s in enumerate(signals, 1):
        s["rank"] = i
    doc = {
        "schema": SCHEMA, "generated_at": now.isoformat(timespec="seconds"), "as_of": events_doc.get("as_of"),
        "disclaimer": DISCLAIMER, "scope": "Australia only",
        "rubric": {"version": RUBRIC_VERSION, "weights": WEIGHTS, "component_ranges": COMPONENT_RANGE,
                   "bands": [{"min_weighted": f, "strength": s} for f, s in BANDS], "caps": {**CAPS, "exposure_not_in_source": EXPOSURE_UNVERIFIED_CAP},
                   "doc": "data/signals/README.md"},
        "sector_watch": {"status": "joined" if sw_doc else "awaiting_sector_watch", **(sw_meta or {}),
                         "join": "instrument (ASX code) for ticker cells; S&P/ASX 200 sector index code or GICS sector for sector cells; timeframe days|weeks|months|years",
                         "fields_used": ["id", "instrument", "sector", "timeframe", "colour", "conviction", "horizon_type", "needs_verification"],
                         "fields_not_used": "observed_move_label, summary and sources (prices and index levels are not republished here); fast_move_candidate (trade-candidate flag, out of scope for an information-only feed)"},
        "counts": {"signals": len(signals), "intersecting_heatmap": sum(s["heatmap"]["intersects"] for s in signals),
                   "by_verification": {k: sum(s["verification"]["status"] == k for s in signals) for k in VERIFICATION},
                   "by_strength": {str(n): sum(s["strength"]["value"] == n for s in signals) for n in range(5, 0, -1)}},
        "signals": signals, "excluded": events_doc.get("excluded", []), "problems": problems,
    }
    validate(doc)
    return doc


DIR_MAP = {"tailwind": "incline", "headwind": "decline", "mixed": "neutral"}


def confidence_tag(s):
    if s["verification"]["status"] != "confirmed_primary":
        return "low"
    return "high" if all(a["exposure_in_source"] for a in s["affected"]) and s["source_kind"] == "primary" else "medium"


def to_ratio(doc: dict) -> dict:
    """tt contract ratio.signal.v1 (tt/schemas/ratio-signal.v1.schema.json). Heat-map intersections only."""
    out = []
    for s in doc["signals"]:
        if not s["heatmap"]["intersects"]:
            continue
        d0 = dt.date.fromisoformat(s["date"])
        fired = dt.datetime.combine(d0, dt.time(0, 0), SYD).isoformat()
        expires = dt.datetime.combine(d0 + dt.timedelta(days=30), dt.time(16, 0), SYD).isoformat()
        common = {"score": round(s["strength"]["weighted_score"], 2), "confidence": {"tag": confidence_tag(s)},
                  "signal_fired_at": fired, "earliest_actionable_at": s["earliest_actionable_at"], "expires_at": expires,
                  "friction": {"publication_lag_days": 0},
                  "rationale": {"sentence": s["reasoning"], "contributing_records": [s["id"]], "aggregation_rule_version": RUBRIC_VERSION},
                  "gov": {"strength": s["strength"]["value"], "direction_tag": s["direction"], "verification": s["verification"]["status"],
                          "source_url": s["source_url"], "event": s["event"], "timeframe": s["timeframe"], "heatmap_level": s["heatmap"]["level"],
                          "information_only": True}}
        if s["affected"]:
            for a in s["affected"]:
                out.append({"id": f"gov-{s['id']}-{a['code'].lower()}", "kind": "entity",
                            "instrument": {"symbol": a["code"], "market": "ASX", "name": a["name"]}, "bracket": a["bracket"] or None,
                            **common, "gov": {**common["gov"], "direction_tag": a["direction"]}})
        else:
            for b in s["brackets"]:
                out.append({"id": f"gov-{s['id']}-{b.lower()}", "kind": "bracket", "bracket": b, "direction": DIR_MAP[s["direction"]],
                            "window_months": 3, **common})
    for o in out:
        if o.get("bracket") is None:
            o.pop("bracket", None)
    return {"schema": "ratio.signal.v1", "generated_at": doc["generated_at"], "example": False, "experimental": True,
            "source_feed": "v2-prog/time data/signals/signals.json (gov.signal.v1)",
            "_note": "EXPERIMENTAL, INFORMATION ONLY. Real government and regulatory events, strength-rated and verified as labelled. "
                     "Not a recommendation to buy, sell or hold. score = rubric weighted score (0..1); confidence: high = primary source and named party, "
                     "medium = primary source but ticker exposure not stated in source, low = secondary or needs human verification. "
                     "window_months=3 for bracket rows follows Tic BRACKET_PRIMARY_WINDOW; expires_at = date + 30 days (Ratio L4 maximum lead-lag window) [verify, Doug].",
            "disclaimer": doc["disclaimer"], "signals": out}


def validate(doc: dict):
    def walk(o, path="$"):
        if isinstance(o, dict):
            for k, v in o.items():
                if ADVICE_KEY.search(k) and k not in ("earliest_actionable_at",):
                    raise ValueError(f"advice-like field {k} at {path}")
                walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o): walk(v, f"{path}[{i}]")
        elif isinstance(o, str) and ADVICE_TEXT.search(o) and not o.startswith("General information"):
            raise ValueError(f"advice-like text at {path}: {o[:80]}")
    walk([{k: v for k, v in s.items() if k != "label"} for s in doc["signals"]])
    for s in doc["signals"]:
        assert 1 <= s["strength"]["value"] <= 5
        assert s["direction"] in DIRECTIONS and s["verification"]["status"] in VERIFICATION
        assert s["timeframe"] in TIMEFRAMES + (None,)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sector-watch", default=os.environ.get("SECTOR_WATCH_DIR"))
    ap.add_argument("--now", help="ISO datetime (tests)")
    a = ap.parse_args(argv)
    now = dt.datetime.fromisoformat(a.now) if a.now else dt.datetime.now(SYD)
    sw, sw_name = latest_sector_watch(a.sector_watch)
    if sw is None and (ROOT / "data/signals/sector_watch_join.json").exists():
        sw, sw_name = load(ROOT / "data/signals/sector_watch_join.json"), "data/signals/sector_watch_join.json (cached subset)"
    doc = build(load(ROOT / "data/signals/events.json"), load(ROOT / "data/signals/tickers.json"),
                load(ROOT / "data/matches.json", {}), sw, sw_name, now)
    if sw is not None and a.sector_watch:
        # cache only the minimal non-price subset so scheduled runs (no box access) keep the last join
        cache = {"note": "Minimal subset of ASX 200 Sector Watch cells used for the join (no prices, summaries or sources). Refresh with --sector-watch.",
                 "source_file": sw_name, "generated_at": sw.get("generated_at"), "session_as_of": sw.get("session_as_of"), "signals": sw_cells(sw)}
        (ROOT / "data/signals/sector_watch_join.json").write_text(json.dumps(cache, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (ROOT / "data/signals/signals.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (ROOT / "data/signals/ratio-signals.json").write_text(json.dumps(to_ratio(doc), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    c = doc["counts"]
    print(f"signals: {c['signals']}  intersecting heat map: {c['intersecting_heatmap']}  problems: {len(doc['problems'])}")
    return 0 if not doc["problems"] else 1


if __name__ == "__main__":
    sys.exit(main())
