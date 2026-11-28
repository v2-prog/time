import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fetchers.build_index import CATALOGUE, build, write  # noqa: E402


class DataIndexTests(unittest.TestCase):
    def test_frozen_signals_path_and_schema(self):
        gov = next(e for e in CATALOGUE if e["id"] == "gov_signals")
        self.assertEqual(gov["path"], "/data/signals/signals.json")
        self.assertEqual(gov["schema"], "gov.signal.v1")

    def test_required_feeds_are_listed(self):
        ids = {e["id"] for e in CATALOGUE}
        for required in ("gov_signals", "matches", "verification", "rdti_listed_matches",
                         "rdti_ledger_2023_24", "feed_health"):
            self.assertIn(required, ids)
        paths = {e["path"] for e in CATALOGUE}
        for required in ("/data/signals/signals.json", "/data/matches.json",
                         "/data/verification.json", "/data/rdti/listed-matches.json"):
            self.assertIn(required, paths)

    def test_catalogue_files_exist_and_index_builds(self):
        for e in CATALOGUE:
            self.assertTrue((ROOT / e["file"]).exists(), e["file"])
        doc = build(ROOT)
        self.assertEqual(doc["schema"], "time.data-index.v1")
        self.assertEqual(len(doc["feeds"]), len(CATALOGUE))
        gov = next(f for f in doc["feeds"] if f["id"] == "gov_signals")
        self.assertEqual(gov["path"], "/data/signals/signals.json")
        self.assertEqual(gov["schema"], "gov.signal.v1")
        self.assertTrue(gov["updated_at"])

    def test_write_round_trip(self):
        import tempfile, shutil
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "data").mkdir()
            # Builder only needs the catalogue files for timestamps; copy those.
            for e in CATALOGUE:
                dest = tmp / e["file"]
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(ROOT / e["file"], dest)
            out = write(tmp)
            on_disk = json.loads(out.read_text())
            rebuilt = build(tmp)
            self.assertEqual(on_disk["schema"], "time.data-index.v1")
            self.assertEqual(on_disk["feeds"], rebuilt["feeds"])
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
