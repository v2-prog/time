"""Skeleton live fetcher for ASX price-sensitive announcements.

Priority companies: BHP, RIO, FMG, NTU, WHC, etc.
This is a starting point; implement actual HTTP calls, parsing, and NormalisedRecord emission.
Respect rate limits and robots.txt. Output to correlator_core format.
"""

import datetime
from typing import List, Dict

# Placeholder: replace with real ASX endpoint or RSS when available.
ASX_BASE = "https://www.asx.com.au"

def fetch_announcements(codes: List[str], since: datetime.date) -> List[Dict]:
    """Return list of raw announcement dicts. Implement scraping or API here."""
    # TODO: implement
    # Example structure:
    # {"code": "BHP", "date": "2026-04-22", "title": "...", "url": "...", "body": "..."}
    return []

def normalise(raw: Dict) -> Dict:
    """Convert to NormalisedRecord shape used by correlator_core."""
    return {
        "entity": raw.get("code"),
        "occurred_at": raw.get("date"),
        "type": "announcement",
        "title": raw.get("title"),
        "source_url": raw.get("url"),
        "raw_confidence": 0.9,
        "needs_verification": True,
    }

if __name__ == "__main__":
    print("ASX fetcher skeleton ready. Implement fetch_announcements.")
