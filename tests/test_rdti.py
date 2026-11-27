import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "rdti"))
from parse_ato import abn_valid, acn_valid, classify_id, money  # noqa: E402
from match_asx import match, norm, core  # noqa: E402
from build_ledger import cagr, yoy  # noqa: E402


class TestIds(unittest.TestCase):
    def test_abn(self):
        self.assertTrue(abn_valid("51824753556"))  # ATO worked example
        self.assertTrue(abn_valid("99051588348"))  # CSL Limited
        self.assertFalse(abn_valid("51824753557"))
        self.assertFalse(abn_valid("1234"))

    def test_acn(self):
        self.assertTrue(acn_valid("000000019"))  # ASIC worked example
        self.assertTrue(acn_valid("051588348"))
        self.assertFalse(acn_valid("051588349"))

    def test_classify(self):
        self.assertEqual(classify_id(99051588348), ("99051588348", "051588348", "ABN", True))
        self.assertEqual(classify_id(19), (None, "000000019", "ACN", True))
        self.assertEqual(classify_id(None)[2], "unknown")

    def test_money(self):
        self.assertEqual(money("1,234"), 1234)
        self.assertIsNone(money(None))


class TestMatch(unittest.TestCase):
    ASX = [{"name": "CSL LIMITED", "code": "CSL", "gics_group": "x"},
           {"name": "XERO LIMITED", "code": "XRO", "gics_group": "x"},
           {"name": "TRANSURBAN GROUP", "code": "TCL", "gics_group": "x"}]

    def test_norm(self):
        self.assertEqual(norm("The Foo & Bar Proprietary Limited"), "FOO AND BAR PTY LTD")
        self.assertEqual(core("XERO AUSTRALIA PTY LIMITED"), "XERO")

    def test_tiers(self):
        m = match({"a": "CSL LIMITED", "b": "XERO AUSTRALIA PTY LIMITED", "c": "TRANSURBAN HOLDINGS LIMITED", "d": "NOBODY PTY LTD"}, self.ASX)
        self.assertEqual(m["a"]["confidence"], "high")
        self.assertEqual(m["b"]["confidence"], "low")
        self.assertIn("possible_subsidiary", m["b"]["flags"])
        self.assertEqual(m["c"]["confidence"], "medium")
        self.assertNotIn("d", m)

    def test_override_wins(self):
        m = match({"a": "CSL LIMITED"}, self.ASX, {"a": {"asx_code": None, "confidence": "none", "flags": []}})
        self.assertEqual(m["a"]["method"], "override")


class TestTrend(unittest.TestCase):
    def test_yoy(self):
        self.assertEqual(yoy(100, 150), (50.0, None))
        self.assertEqual(yoy(0, 5)[0], None)
        self.assertEqual(yoy(None, 5)[1], "missing year")

    def test_cagr(self):
        self.assertEqual(cagr(100, 121, 2), (10.0, None))
        self.assertIsNone(cagr(0, 121, 2)[0])


if __name__ == "__main__":
    unittest.main()
