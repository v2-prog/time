import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fetchers.correlator import score_pair, bracket_activity  # noqa: E402
from fetchers.topics import topics_for  # noqa: E402

POLICY = {"id": "ntu-firb-2026", "date": "2026-06-18", "date_kind": "effective", "title": "NTU orders commence",
          "commodity": ["rare_earths"], "volatility": "medium", "verify": True, "boundary_class": True,
          "entities": ["NTU"], "topics": ["firb"], "direction_for_resources": "mixed"}


def rec(**kw):
    r = {"record_id": "r1", "feed": "asx_announcements", "entity": "NTU", "entity_name": "Northern Minerals Limited",
         "event_type": "asx_announcement", "occurred_at": "2026-06-25T09:00:00+10:00", "title": "NTU announcement: headline on ASX",
         "source_url": "https://www.asx.com.au/x", "commodity": ["rare_earths"], "raw_confidence": 0.9,
         "price_sensitive": True, "needs_verification": True, "extra": {"topics": ["firb"], "headline_withheld": True}}
    r.update(kw)
    return r


class EngineTests(unittest.TestCase):
    def test_named_entity_match_is_explained(self):
        m = score_pair(rec(), POLICY, fresh=1.0)
        self.assertIsNotNone(m)
        self.assertEqual(m["lag_days"], 7)
        self.assertEqual(m["window_days"], 7)
        self.assertEqual(m["parts"]["entity"], 1.0)
        self.assertIn("policy_verify", m["flags"])
        self.assertIn("matched_on_metadata_and_tags", m["flags"])
        self.assertIn("7 days after", m["rationale"])
        self.assertEqual(m["origin"], "engine")
        self.assertEqual(m["confidence"], 0.4)  # fresh feed, but policy and record both unverified

    def test_score_formula(self):
        m = score_pair(rec(), POLICY, fresh=1.0)
        base = 0.30 * (1 - 7 / 31) + 0.30 * 1.0 + 0.25 * 1.0 + 0.15 * 0.9
        self.assertAlmostEqual(m["score"], round(base * 0.9 * 0.85, 3))

    def test_outside_window(self):
        self.assertIsNone(score_pair(rec(occurred_at="2026-08-01T09:00:00+10:00"), POLICY))

    def test_routine_only_is_dropped(self):
        self.assertIsNone(score_pair(rec(extra={"topics": ["routine"]}), POLICY))

    def test_commodity_only_overlap_is_dropped(self):
        self.assertIsNone(score_pair(rec(extra={"topics": []}), POLICY))

    def test_unrelated_entity(self):
        self.assertIsNone(score_pair(rec(entity="BHP", commodity=["iron_ore"]), POLICY))

    def test_shared_commodity_entity_scores_lower(self):
        named = score_pair(rec(), POLICY)
        other = score_pair(rec(entity="LYC"), POLICY)
        self.assertTrue(other is None or other["score"] < named["score"])

    def test_tenement_grant_is_binary(self):
        p = dict(POLICY, entities=["FMG"], commodity=["iron_ore"], topics=["china_trade"], verify=False)
        r = rec(entity="FMG", feed="wa_dmpe_tenements", event_type="mining_lease_granted", raw_confidence=0.95,
                commodity=["iron_ore"], extra={"topics": ["approval", "mining_lease"]}, occurred_at="2026-06-18")
        self.assertIsNotNone(score_pair(r, p))

    def test_rationale_never_contains_withheld_headline(self):
        m = score_pair(rec(), POLICY)
        self.assertNotIn("Treasurer makes further", m["rationale"])

    def test_lead_before_scheduled_event(self):
        p = dict(POLICY, date="2026-07-01", date_kind="scheduled")
        m = score_pair(rec(), p)
        self.assertEqual(m["lag_days"], -6)
        self.assertIn("scheduled_future_event", m["flags"])

    def test_bracket_activity_windows(self):
        ms = [{"bracket": "Resources", "record": {"date": d}} for d in ("2026-01-01", "2026-01-15", "2026-03-10")]
        a = bracket_activity(ms, 30)["Resources"]
        self.assertEqual(a["counts"], [2, 0, 1])

    def test_topics(self):
        self.assertEqual(topics_for("Treasurer makes further disposal orders"), ["firb"])
        self.assertIn("routine", topics_for("Change of Director's Interest Notice"))


if __name__ == "__main__":
    unittest.main()
