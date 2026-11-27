import copy
import datetime as dt
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "fetchers"))
import signals as S  # noqa: E402

NOW = dt.datetime.fromisoformat("2026-11-28T10:30:00+11:00")
EVENTS = json.loads((ROOT / "data/signals/events.json").read_text())
TICKERS = json.loads((ROOT / "data/signals/tickers.json").read_text())
SW = json.loads((ROOT / "data/signals/sector_watch_join.json").read_text())


def R(m, c, d, s):
    return {k: {"value": v, "basis": "t"} for k, v in zip(("materiality", "certainty", "directness", "source"), (m, c, d, s))}


class Rubric(unittest.TestCase):
    def test_bands_and_caps(self):
        self.assertEqual(S.strength(R(3, 3, 3, 3), "confirmed_primary", True)["value"], 5)
        self.assertEqual(S.strength(R(0, 0, 0, 1), "confirmed_primary", True)["value"], 1)
        self.assertEqual(S.strength(R(3, 3, 3, 3), "secondary_only", True)["value"], 3)
        self.assertEqual(S.strength(R(3, 3, 3, 3), "needs_human_verification", True)["value"], 2)
        st = S.strength(R(3, 3, 3, 3), "confirmed_primary", False)
        self.assertEqual((st["value"], st["uncapped"]), (4, 5))
        self.assertTrue(st["caps_applied"])

    def test_out_of_range_component_refused(self):
        with self.assertRaises(ValueError):
            S.strength(R(4, 0, 0, 1), "confirmed_primary", True)


class Build(unittest.TestCase):
    def setUp(self):
        self.doc = S.build(EVENTS, TICKERS, {}, SW, "cache", NOW)

    def test_all_events_build_with_required_fields(self):
        self.assertEqual(self.doc["problems"], [])
        self.assertEqual(len(self.doc["signals"]), len(EVENTS["events"]))
        for s in self.doc["signals"]:
            self.assertTrue(s["source_url"].startswith("https://"))
            self.assertIn(s["direction"], S.DIRECTIONS)
            self.assertIn(s["verification"]["status"], S.VERIFICATION)
            self.assertIn(s["timeframe"], S.TIMEFRAMES)
            self.assertTrue(s["reasoning"])
            self.assertEqual(s["label"], "General information, not financial or legal advice.")
            for a in s["affected"]:
                self.assertIsNone(a["asx200_member"])

    def test_sorted_by_strength_then_verification(self):
        keys = [(-s["strength"]["value"], S.VERIFICATION.index(s["verification"]["status"])) for s in self.doc["signals"]]
        self.assertEqual(keys, sorted(keys))

    def test_heatmap_join_ticker_and_sector(self):
        by = {s["id"]: s for s in self.doc["signals"]}
        self.assertEqual(by["rhc-ramsay-sante-distribution"]["heatmap"]["level"], "ticker")
        self.assertEqual(by["gas-dgrs-exporters"]["heatmap"]["level"], "sector")  # via XEJ (STO); ORG is Utilities
        self.assertFalse(by["rwc-firb-cleared"]["heatmap"]["intersects"])  # no Industrials row in Sector Watch

    def test_without_sector_watch_awaits_join(self):
        d = S.build(EVENTS, TICKERS, {}, None, None, NOW)
        self.assertTrue(all(s["heatmap"]["status"] == "awaiting_sector_watch" for s in d["signals"]))
        self.assertEqual(S.to_ratio(d)["signals"], [])

    def test_unknown_ticker_is_a_problem_not_a_guess(self):
        ev = copy.deepcopy(EVENTS); ev["events"][0]["tickers"].append({"code": "ZZZ", "role": "x", "exposure_in_source": True})
        d = S.build(ev, TICKERS, {}, SW, "cache", NOW)
        self.assertEqual(d["problems"][0]["id"], ev["events"][0]["id"])

    def test_advice_text_refused(self):
        ev = copy.deepcopy(EVENTS); ev["events"][0]["reasoning"] = "We recommend you buy now."
        with self.assertRaises(ValueError):
            S.build(ev, TICKERS, {}, SW, "cache", NOW)

    def test_ratio_contract(self):
        r = S.to_ratio(self.doc)
        self.assertEqual(r["schema"], "ratio.signal.v1")
        self.assertFalse(r["example"])
        for s in r["signals"]:
            self.assertIn(s["kind"], ("entity", "bracket"))
            self.assertTrue(0 <= s["score"] <= 1)
            self.assertIn(s["confidence"]["tag"], ("low", "medium", "high"))
            self.assertTrue(s["rationale"]["sentence"])
            self.assertTrue(s["gov"]["information_only"])
            if s["kind"] == "entity":
                self.assertTrue(s["instrument"]["symbol"])
            else:
                self.assertIn(s["bracket"], ("Resources", "Financials", "Healthcare", "Industrials", "Energy"))
                self.assertTrue(s["rationale"]["contributing_records"])
            self.assertNotIn("fast_move_candidate", json.dumps(s))

    def test_secondary_or_unverified_is_low_confidence(self):
        for s in self.doc["signals"]:
            if s["verification"]["status"] != "confirmed_primary":
                self.assertEqual(S.confidence_tag(s), "low")


if __name__ == "__main__":
    unittest.main()
