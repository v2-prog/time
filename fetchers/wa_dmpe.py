"""Skeleton live fetcher for WA Department of Mines, Petroleum and Exploration (DMPE).

Replaces old DMIRS/DEMIRS references. Focus on mining tenure grants, environmental approvals.
Implement actual scraping of public registers.
"""

import datetime
from typing import List, Dict

DMPE_BASE = "https://www.wa.gov.au/organisation/department-of-mines-petroleum-and-exploration"

def fetch_tenures(since: datetime.date) -> List[Dict]:
    """Return list of raw tenure/approval records."""
    # TODO: implement against public DMPE registers
    return []

def normalise(raw: Dict) -> Dict:
    return {
        "entity": raw.get("holder"),
        "occurred_at": raw.get("decision_date"),
        "type": "mining_lease_granted" if "lease" in raw.get("type", "").lower() else "approval",
        "title": raw.get("title"),
        "source_url": raw.get("url"),
        "raw_confidence": 0.95,
        "needs_verification": True,
        "jurisdiction": "AU-WA",
    }

if __name__ == "__main__":
    print("WA DMPE fetcher skeleton ready.")
