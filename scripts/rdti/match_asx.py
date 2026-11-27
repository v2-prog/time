"""Match R&DTI entities to ASX-listed companies (listed companies only).

Inputs: the ASX "listed companies" CSV (company name, code, GICS industry group) and the ledger.
The ASX list has no ABN/ACN, so matching is by legal name, then adjusted by manual overrides
(data/rdti/asx_overrides.json) that a human has checked. Every match carries a confidence and
reasons; anything other than an exact public-company name match is flagged for verification.

Confidence:
  high    exact normalised legal-name match, entity is a public company (LIMITED/LTD, not PTY)
  medium  match after dropping generic words (GROUP, HOLDINGS, AUSTRALIA, ...) or a reviewed override
  low     ledger name is a PTY subsidiary whose name starts with the listed company's name
"""
from __future__ import annotations

import csv
import io
import re

GENERIC = {"GROUP", "HOLDINGS", "HOLDING", "AUSTRALIA", "AUSTRALIAN", "AUST", "CORPORATION", "CORP", "INTERNATIONAL",
           "GLOBAL", "THE", "AND", "CO", "COMPANY", "LIMITED", "LTD", "NL", "INC", "PLC"}


def norm(name: str) -> str:
    s = (name or "").upper().replace("&", " AND ")
    s = re.sub(r"\bPROPRIETARY\b", "PTY", s)
    s = re.sub(r"\bLIMITED\b", "LTD", s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\bTHE\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def core(name: str) -> str:
    toks = [t for t in norm(name).split() if t not in GENERIC and t != "PTY"]
    return " ".join(toks)


def is_pty(name: str) -> bool:
    return bool(re.search(r"\bPTY\b", norm(name)))


def load_asx(csv_text: str):
    lines = csv_text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("Company name"))
    rows = list(csv.DictReader(io.StringIO("\n".join(lines[start:]))))
    return [{"name": r["Company name"].strip(), "code": r["ASX code"].strip(), "gics_group": r["GICS industry group"].strip()} for r in rows]


def match(entities, asx, overrides=None):
    """entities: {entity_key: latest_name}. Returns {entity_key: match dict}."""
    overrides = overrides or {}
    by_norm, by_core = {}, {}
    for a in asx:
        by_norm.setdefault(norm(a["name"]), []).append(a)
        c = core(a["name"])
        if len(c) >= 4:
            by_core.setdefault(c, []).append(a)
    out = {}
    for key, name in entities.items():
        if key in overrides:
            o = overrides[key]
            out[key] = dict(o, method="override")
            continue
        n = norm(name)
        hit = by_norm.get(n)
        if hit and len(hit) == 1 and not is_pty(name):
            out[key] = {"asx_code": hit[0]["code"], "asx_name": hit[0]["name"], "gics_group": hit[0]["gics_group"],
                        "confidence": "high", "method": "exact_name", "flags": ["abn_not_cross_checked"]}
            continue
        c = core(name)
        hit = by_core.get(c)
        if hit and len(hit) == 1 and len(c.split()) >= 1 and len(c) >= 4:
            flags = ["name_only_match", "abn_not_cross_checked"]
            conf = "medium"
            if is_pty(name):
                conf = "low"
                flags.append("possible_subsidiary")
            out[key] = {"asx_code": hit[0]["code"], "asx_name": hit[0]["name"], "gics_group": hit[0]["gics_group"],
                        "confidence": conf, "method": "core_name", "flags": flags}
            continue
        if is_pty(name):
            # Subsidiary whose name starts with a listed company's core name (e.g. "XYZ OPERATIONS PTY LTD")
            ctoks = c.split()
            for k in (3, 2):
                if len(ctoks) > k:
                    pre = " ".join(ctoks[:k])
                    hit = by_core.get(pre)
                    if hit and len(hit) == 1 and len(pre) >= 6:
                        out[key] = {"asx_code": hit[0]["code"], "asx_name": hit[0]["name"], "gics_group": hit[0]["gics_group"],
                                    "confidence": "low", "method": "subsidiary_prefix",
                                    "flags": ["possible_subsidiary", "name_only_match", "abn_not_cross_checked"]}
                        break
    return out
