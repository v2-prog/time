"""Build the R&DTI base ledger (sketch, not live) into data/rdti/.

Usage: python scripts/rdti/build_ledger.py RAW_DIR ASX_CSV [--abr-checked data/rdti/abr_checks.json]
RAW_DIR holds rdti-2021-22.xlsx, rdti-2022-23.xlsx, rdti-2023-24.xlsx downloaded from data.gov.au (URLs in parse_ato.REPORTS).
ASX_CSV is https://www.asx.com.au/asx/research/ASXListedCompanies.csv (not committed; ASX terms).
Ledger and ticker matching only: no projections, no alerts.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import statistics
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from parse_ato import REPORTS, YEARS, parse  # noqa: E402
from match_asx import load_asx, match  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "data", "rdti")
LABEL = "sketch, not live"
DISCLAIMER = "General information only, not personal financial advice. Australia only. Figures are as published by the ATO; matches to ASX tickers are inferred and need human verification."
FOREIGN_SUFFIX = re.compile(r"\b(INC|CORP|CORPORATION|PLC|N\.?V|SE|AG|LLC)\.?$")

NULL_REVENUE = "Not computed: company revenue is not in the ATO report; public filings would have to be parsed per company and the claimant is often a subsidiary whose revenue differs from the listed group's."
NULL_MCAP = "Not computed: market capitalisation comes from ASX/market-data feeds whose terms do not permit republication here; no free, licensed source is wired in."
NULL_GAP = "Not computed: AusIndustry (DISR) does not publish per-company registered R&D estimates; only the ATO claim figure is public (s3H TAA 1953 transparency report)."


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 16), b""):
            h.update(b)
    return h.hexdigest()


def yoy(a, b):
    if a is None or b is None:
        return None, "missing year"
    if a == 0:
        return None, "zero base year"
    return round((b - a) / a * 100, 1), None


def cagr(first, last, periods):
    if first is None or last is None:
        return None, "missing first or last year"
    if first <= 0 or last <= 0:
        return None, "non-positive endpoint"
    return round(((last / first) ** (1 / periods) - 1) * 100, 1), None


def build(raw_dir, asx_csv, abr_checks=None):
    ledger, stats = parse(raw_dir)
    abr_checks = abr_checks or {}
    latest = {}
    for (k, iy), v in sorted(ledger.items(), key=lambda kv: kv[0][1]):
        latest[k] = v["company_name"]
    with open(asx_csv, encoding="utf-8", errors="replace") as f:
        asx_text = f.read()
    asx = load_asx(asx_text)
    asof = re.search(r"as at (.+)$", asx_text.splitlines()[0])
    with open(os.path.join(OUT, "asx_overrides.json")) as f:
        overrides = {k: v for k, v in json.load(f).items() if not k.startswith("_")}
    matches = match(latest, asx, overrides)
    for k, m in matches.items():
        m["flags"] = list(dict.fromkeys(m.get("flags", [])))
        if m.get("asx_name") and FOREIGN_SUFFIX.search(m["asx_name"].strip()) and "foreign_registered_parent" not in m["flags"]:
            m["flags"].append("foreign_registered_parent")
        if k in abr_checks and "abn_not_cross_checked" in m["flags"]:
            m["flags"].remove("abn_not_cross_checked")
            m["abr_check"] = abr_checks[k]
    codes = defaultdict(list)
    for k, m in matches.items():
        if m.get("asx_code"):
            codes[m["asx_code"]].append(k)
    for code, ks in codes.items():
        if len(ks) > 1:
            for k in ks:
                if "group_multiple_entities" not in matches[k]["flags"]:
                    matches[k]["flags"].append("group_multiple_entities")

    os.makedirs(OUT, exist_ok=True)
    fields = ["entity_key", "company_name", "abn", "acn", "id_type", "id_checksum_valid", "income_year", "rd_expenditure",
              "rd_expenditure_amended", "rd_expenditure_effective", "amended_to_nil", "source_report", "asx_code", "match_confidence"]
    counts = {}
    by_entity = defaultdict(dict)
    for y in YEARS:
        rows = []
        for (k, iy), v in ledger.items():
            if iy != y:
                continue
            m = matches.get(k) or {}
            r = {"entity_key": k, **{f: v[f] for f in fields if f in v}}
            r["amended_to_nil"] = v["rd_expenditure_amended"] == 0
            r["asx_code"] = m.get("asx_code")
            r["match_confidence"] = m.get("confidence") if m.get("asx_code") else None
            rows.append({f: r.get(f) for f in fields})
            by_entity[k][y] = v["rd_expenditure_effective"]
        rows.sort(key=lambda r: (-(r["rd_expenditure_effective"] or 0), r["company_name"]))
        meta = {"label": LABEL, "disclaimer": DISCLAIMER, "income_year": y, "rows": len(rows),
                "source": "ATO R&D Tax Incentive transparency reports via data.gov.au (CC BY 2.5 AU)", "schema": "schema.json"}
        with open(os.path.join(OUT, f"ledger-{y}.json"), "w") as f:
            json.dump({"meta": meta, "rows": rows}, f, ensure_ascii=False, separators=(",", ":"))
        with open(os.path.join(OUT, f"ledger-{y}.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        counts[y] = {"entities": len(rows), "with_positive_or_unamended_figure": sum(1 for r in rows if not r["amended_to_nil"]),
                     "amended_to_nil": sum(1 for r in rows if r["amended_to_nil"]),
                     "amended_rows": sum(1 for r in rows if r["rd_expenditure_amended"] is not None),
                     "late_or_amended_from_later_report": sum(1 for r in rows if r["source_report"] != y),
                     "total_effective_aud": sum(r["rd_expenditure_effective"] or 0 for r in rows),
                     "effective_zero": sum(1 for r in rows if r["rd_expenditure_effective"] == 0),
                     "effective_20m_plus": sum(1 for r in rows if (r["rd_expenditure_effective"] or 0) >= 20_000_000),
                     "median_positive_aud": statistics.median([r["rd_expenditure_effective"] for r in rows if (r["rd_expenditure_effective"] or 0) > 0]),
                     "id_checksum_invalid_or_missing": sum(1 for r in rows if not r["id_checksum_valid"])}

    listed = []
    for k, m in matches.items():
        if not m.get("asx_code"):
            continue
        spend = {y: by_entity[k].get(y) for y in YEARS}
        y1, r1 = yoy(spend["2021-22"], spend["2022-23"])
        y2, r2 = yoy(spend["2022-23"], spend["2023-24"])
        c, rc = cagr(spend["2021-22"], spend["2023-24"], 2)
        anyrow = next(v for (kk, iy), v in ledger.items() if kk == k)
        listed.append({"entity_key": k, "company_name": latest[k], "abn": anyrow["abn"], "acn": anyrow["acn"],
                       "asx_code": m["asx_code"], "asx_name": m["asx_name"], "gics_group": m.get("gics_group"),
                       "confidence": m["confidence"], "method": m["method"], "flags": m["flags"], "note": m.get("note"),
                       "abr_check": m.get("abr_check"),
                       "rd_expenditure_effective": spend,
                       "yoy_pct": {"2022-23": y1, "2023-24": y2}, "yoy_null_reason": {"2022-23": r1, "2023-24": r2},
                       "cagr_pct_2021_22_to_2023_24": c, "cagr_null_reason": rc,
                       "rd_share_of_revenue": None, "rd_share_of_revenue_null_reason": NULL_REVENUE,
                       "rd_share_of_market_cap": None, "rd_share_of_market_cap_null_reason": NULL_MCAP,
                       "ausindustry_registered_vs_ato_gap": None, "ausindustry_gap_null_reason": NULL_GAP})
    listed.sort(key=lambda r: -(r["rd_expenditure_effective"]["2023-24"] or 0))
    not_listed = [{"entity_key": k, "company_name": latest[k], **{kk: vv for kk, vv in m.items() if kk in ("status", "flags", "note")}}
                  for k, m in matches.items() if not m.get("asx_code")]
    conf = defaultdict(int)
    for r in listed:
        conf[r["confidence"]] += 1
    with open(os.path.join(OUT, "listed-matches.json"), "w") as f:
        json.dump({"meta": {"label": LABEL, "disclaimer": DISCLAIMER, "asx_list_as_at": asof.group(1) if asof else None,
                            "asx_list_url": "https://www.asx.com.au/asx/research/ASXListedCompanies.csv",
                            "asx_listed_companies": len(asx), "matched_entities": len(listed),
                            "matched_codes": len({r['asx_code'] for r in listed}), "by_confidence": dict(conf)},
                   "matches": listed, "excluded_not_asx_listed": not_listed}, f, ensure_ascii=False, indent=1)

    src = {"label": LABEL, "dataset": "https://data.gov.au/data/dataset/research-and-development-tax-incentive",
           "ckan_api": "https://data.gov.au/data/api/3/action/package_show?id=research-and-development-tax-incentive",
           "licence": "Creative Commons Attribution 2.5 Australia (CC BY 2.5 AU). Source: Australian Taxation Office.",
           "retrieved": "2026-11-27T15:19+11:00", "reports": {}}
    ckan = {}
    pkg = os.path.join(raw_dir, "pkg.json")
    if os.path.exists(pkg):
        for r in json.load(open(pkg))["result"]["resources"]:
            ckan[r["id"]] = r
    for y in YEARS:
        rid, url = REPORTS[y]
        p = os.path.join(raw_dir, f"rdti-{y}.xlsx")
        src["reports"][y] = {"resource_id": rid, "url": url, "bytes": os.path.getsize(p), "sha256": sha256(p),
                             "ckan_name": ckan.get(rid, {}).get("name"), "ckan_last_modified_utc": ckan.get(rid, {}).get("last_modified"),
                             "sheet": stats[y]["sheet"], "raw_rows": stats[y]["rows"], "columns": stats[y]["header"]}
    with open(os.path.join(OUT, "sources.json"), "w") as f:
        json.dump(src, f, indent=1)
    all_entities = {k for (k, iy) in ledger}
    counts["_all_years"] = {"distinct_entities": len(all_entities)}
    return counts, listed, matches, ledger


RAND = {  # https://randadvisory.com.au/rd-tax-incentive-statistics (page states last verified 27 Sep 2026); read 27 Nov 2026
    "url": "https://randadvisory.com.au/rd-tax-incentive-statistics",
    "note": "Rand Advisory publishes summary statistics and a search UI built on the same ATO reports; no bulk download, so only its published summary figures are compared (no scraping).",
    "distinct_companies": 18733,
    "years": {"2021-22": {"companies": 11709, "total_aud_b": 11.2, "20m_plus": 47, "median_aud": 331279},
              "2022-23": {"companies": 13121, "total_aud_b": 16.2, "20m_plus": 88, "median_aud": 374712},
              "2023-24": {"companies": 13490, "total_aud_b": 16.7, "20m_plus": 89, "median_aud": 374175, "amended_to_nil": 66}},
}
CLAIMS = [("Atlassian", "166799542", 236e6), ("Fortescue", "002594872", 155e6), ("Cochlear", "002618073", 146e6),
          ("CSL", "051588348", 114e6), ("Rio Tinto", "004458404", 105e6), ("ResMed", "003765133", 104e6)]


def comparison(counts, ledger, matches):
    years = {}
    for y, r in RAND["years"].items():
        c = counts[y]
        years[y] = {"ours_entities": c["entities"], "rand_companies": r["companies"], "diff": c["entities"] - r["companies"],
                    "ours_total_aud_b": round(c["total_effective_aud"] / 1e9, 2), "rand_total_aud_b": r["total_aud_b"],
                    "ours_20m_plus": c["effective_20m_plus"], "rand_20m_plus": r["20m_plus"],
                    "ours_median_positive": c["median_positive_aud"], "rand_median": r["median_aud"],
                    "ours_effective_zero": c["effective_zero"], "rand_amended_to_nil": r.get("amended_to_nil")}
    top = []
    for label, key, claimed in CLAIMS:
        v = ledger.get((key, "2023-24"))
        eff = v["rd_expenditure_effective"] if v else None
        m = matches.get(key, {})
        status = "Not found"
        if eff is not None:
            status = "Confirmed" if abs(eff - claimed) / claimed < 0.006 else "Corrected"
        top.append({"claim": label, "claimed_aud": claimed, "entity": v and v["company_name"], "abn": v and v["abn"],
                    "reported_aud": v and v["rd_expenditure"], "amended_aud": v and v["rd_expenditure_amended"], "effective_aud": eff,
                    "status": status, "asx_code": m.get("asx_code"), "listing_note": m.get("note")})
    return {"label": LABEL, "rand": RAND, "years": years,
            "distinct_entities": {"ours": counts["_all_years"]["distinct_entities"], "rand": RAND["distinct_companies"]},
            "top_claimants_2023_24": top}


if __name__ == "__main__":
    abr = {}
    if "--abr-checked" in sys.argv:
        abr = json.load(open(sys.argv[sys.argv.index("--abr-checked") + 1]))
        abr = {k: v for k, v in abr.items() if not k.startswith("_")}
    counts, listed, matches, ledger = build(sys.argv[1], sys.argv[2], abr)
    with open(os.path.join(OUT, "comparison.json"), "w") as f:
        json.dump(comparison(counts, ledger, matches), f, indent=1)
    with open(os.path.join(OUT, "counts.json"), "w") as f:
        json.dump({"label": LABEL, "counts": counts}, f, indent=1)
    print(json.dumps(counts, indent=1))
