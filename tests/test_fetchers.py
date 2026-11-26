import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fetchers import asx_announcements as asx, wa_dmpe  # noqa: E402
from fetchers.schema import resolve_entity  # noqa: E402

HTML_ROW = """<table><tr><td>23/11/2026<br><span class="dates-time">8:24 am</span></td>
<td class="pricesens"><img src="x.svg" class="pricesens" alt="asterix" title="price sensitive"></td>
<td><a href="/asx/v2/statistics/displayAnnouncement.do?display=pdf&amp;idsId=03168852">BHP Copper South Australia Investor Site Tour<br>
<img src="pdf.png"><span class="page">86 pages</span></a></td></tr></table>"""


class AsxTests(unittest.TestCase):
    def test_html_row(self):
        r = asx.parse_html_list("BHP", HTML_ROW)[0]
        self.assertEqual(r.title, "BHP Copper South Australia Investor Site Tour")
        self.assertTrue(r.price_sensitive)
        self.assertTrue(r.source_url.endswith("idsId=03168852"))
        self.assertEqual(r.occurred_at, "2026-11-23T08:24:00+11:00")  # AEDT

    def test_markit_never_builds_document_link(self):
        r = asx.normalise_markit("BHP", {"date": "2026-04-21T22:30:00.000Z", "documentKey": "2924-03084954-X",
                                         "headline": "Q", "announcementType": "PERIODIC REPORTS", "isPriceSensitive": True})
        self.assertNotIn("idsId", r.source_url)
        self.assertEqual(r.occurred_at, "2026-04-22T08:30:00+10:00")  # AEST
        self.assertEqual(r.event_subtype, "periodic_reports")


class DmpeTests(unittest.TestCase):
    def test_individuals_dropped(self):
        self.assertIsNone(wa_dmpe.normalise_tenement({"holder1": "SMITH, JANE", "grantdate": 1763510400000, "type": "MINING LEASE"}))

    def test_pending_sentinel_dropped(self):
        self.assertIsNone(wa_dmpe.normalise_tenement({"holder1": "X PTY LTD", "grantdate": 32503593600000, "type": "MINING LEASE"}))

    def test_company_grant(self):
        r = wa_dmpe.normalise_tenement({"holder1": "FMG PILBARA PTY LTD", "holder2": "DOE, JOHN", "grantdate": 1763510400000,
                                        "type": "RETENTION LICENCE", "fmt_tenid": "R 47/23"})
        self.assertEqual(r.entity, "FMG")
        self.assertEqual(r.extra["holders"], ["FMG PILBARA PTY LTD"])  # personal name not kept

    def test_announcement_parse(self):
        page = '<meta property="og:title" content="DMPE marks first year"><meta property="og:description" content="d"><time datetime="2026-11-23T16:09:48+08:00">'
        r = wa_dmpe.parse_announcement("https://www.wa.gov.au/government/announcements/x", page)
        self.assertEqual(r.occurred_at, "2026-11-23T16:09:48+08:00")


class EntityTests(unittest.TestCase):
    def test_billiton_alone_is_not_bhp(self):
        self.assertIsNone(resolve_entity("比利顿"))

    def test_chinese_name(self):
        self.assertEqual(resolve_entity("必和必拓 铁矿石"), "BHP")


if __name__ == "__main__":
    unittest.main()
