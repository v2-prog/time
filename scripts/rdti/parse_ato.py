"""Parse ATO R&D Tax Incentive transparency reports (data.gov.au, CC BY 2.5 AU) into one ledger.

Each yearly report holds that income year plus late lodgements and company-initiated
amendments for earlier years. Rows are keyed by (entity key, income_year), entity key = ACN (direct or embedded in the ABN) else ABN; a later
report supersedes an earlier one for the same key. Figures are the ATO's, unchanged.
"""
from __future__ import annotations

import json
import os
import re
import sys


REPORTS = {
    # report year -> (resource id, url, local file)
    "2021-22": ("72efe86d-3ae9-4f84-8446-1a98fed4a8be",
                "https://data.gov.au/data/dataset/7c356598-b048-4c1e-862f-c936041e3d81/resource/72efe86d-3ae9-4f84-8446-1a98fed4a8be/download/report-of-information-about-research-and-development-tax-incentive-entities.xlsx"),
    "2022-23": ("e9c059c8-a801-4068-844e-9d4ee84a1d81",
                "https://data.gov.au/data/dataset/7c356598-b048-4c1e-862f-c936041e3d81/resource/e9c059c8-a801-4068-844e-9d4ee84a1d81/download/report-of-information-about-research-and-development-tax-incentive-entities.xlsx"),
    "2023-24": ("5f7d5cac-cfa8-4500-8468-1c396f3a08d1",
                "https://data.gov.au/data/dataset/7c356598-b048-4c1e-862f-c936041e3d81/resource/5f7d5cac-cfa8-4500-8468-1c396f3a08d1/download/report-of-information-about-research-and-development-tax-incentive-entities-2023-24.xlsx"),
}
YEARS = ["2021-22", "2022-23", "2023-24"]
ABN_W = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]


def abn_valid(abn: str) -> bool:
    if not re.fullmatch(r"\d{11}", abn or ""):
        return False
    d = [int(c) for c in abn]
    d[0] -= 1
    return sum(w * x for w, x in zip(ABN_W, d)) % 89 == 0


def acn_valid(acn: str) -> bool:
    if not re.fullmatch(r"\d{9}", acn or ""):
        return False
    d = [int(c) for c in acn]
    rem = sum(w * x for w, x in zip(range(8, 0, -1), d[:8])) % 10
    return (10 - rem) % 10 == d[8]


def classify_id(raw):
    """Return (abn, acn, id_type, id_valid). ACN is also derived from an ABN when its last 9 digits form a valid ACN."""
    s = re.sub(r"\D", "", str(raw if raw is not None else ""))
    if len(s) == 11:
        acn = s[2:] if acn_valid(s[2:]) else None
        return s, acn, "ABN", abn_valid(s)
    if 0 < len(s) <= 9:
        s = s.zfill(9)
        return None, s, "ACN", acn_valid(s)
    return None, None, "unknown", False


def money(v):
    if v is None or v == "":
        return None
    try:
        return int(round(float(str(v).replace(",", "").replace("$", ""))))
    except ValueError:
        return None


def parse(raw_dir: str):
    import openpyxl  # only needed to build; tests import the validators without it

    ledger = {}
    stats = {}
    for rep in YEARS:
        path = os.path.join(raw_dir, f"rdti-{rep}.xlsx")
        wb = openpyxl.load_workbook(path, read_only=True)
        ws = [w for w in wb.worksheets if w.title.lower() != "information"][0]
        rows = ws.iter_rows(values_only=True)
        header = next(rows)
        n = 0
        for r in rows:
            if not r or not r[0]:
                continue
            name, ident, total, amended, iy = (list(r) + [None] * 5)[:5]
            abn, acn, typ, ok = classify_id(ident)
            iy = str(iy).strip()
            # Entity key: ACN (direct, or embedded in the ABN) else ABN, so an entity listed by ABN in one
            # report and by ACN in another is one entity. A later report supersedes an earlier one.
            key = (acn or abn or f"name:{str(name).strip().upper()}", iy)
            ledger[key] = {
                "company_name": str(name).strip(), "abn": abn, "acn": acn, "id_type": typ, "id_checksum_valid": ok,
                "income_year": iy, "rd_expenditure": money(total), "rd_expenditure_amended": money(amended),
                "source_report": rep,
            }
            n += 1
        stats[rep] = {"rows": n, "sheet": ws.title, "header": [str(h) for h in header]}
    for v in ledger.values():
        v["rd_expenditure_effective"] = v["rd_expenditure_amended"] if v["rd_expenditure_amended"] is not None else v["rd_expenditure"]
    return ledger, stats


if __name__ == "__main__":
    led, st = parse(sys.argv[1])
    print(json.dumps(st, indent=1))
    from collections import Counter
    print(Counter(v["income_year"] for v in led.values()))
