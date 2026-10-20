"""Offline checks for the actual-points backfill (fp_weekly.pull_results)."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fp_weekly  # noqa: E402


class ResultsBackfillTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.calls = []
        self._sleep, fp_weekly.time.sleep = fp_weekly.time.sleep, lambda s: None

    def tearDown(self):
        fp_weekly.time.sleep = self._sleep
        shutil.rmtree(self.tmp)

    def fetcher(self, path, params, key):
        self.calls.append((path, dict(params)))
        pos = params["position"]
        if pos == "TE":
            raise RuntimeError("HTTP 500")
        return {"players": [{"name": f"Synthetic {pos}", "team_id": "AAA", "position_id": pos,
                             "points": {params["start"]: 12.5}}]}

    def test_requests_the_given_week_and_writes_results(self):
        errors = fp_weekly.pull_results(4, "k", self.tmp, self.fetcher)
        self.assertTrue(all(p["start"] == "4" and p["end"] == "4" for _, p in self.calls))
        self.assertEqual(len(self.calls), 6)
        self.assertEqual(len(errors), 1)                     # TE failure reported, not fatal
        out = json.loads((fp_weekly.week_dir(4, self.tmp) / "results.json").read_text())
        self.assertEqual(out["week"], 4)
        pts = {p["name"]: p["points"] for p in out["players"].values()}
        self.assertEqual(pts["Synthetic WR"], 12.5)
        self.assertNotIn("Synthetic TE", pts)

    def test_rerun_only_fills_gaps(self):
        fp_weekly.pull_results(4, "k", self.tmp, self.fetcher)
        self.calls.clear()
        fp_weekly.pull_results(4, "k", self.tmp, self.fetcher)
        self.assertEqual([p["position"] for _, p in self.calls], ["TE"])


if __name__ == "__main__":
    unittest.main()
