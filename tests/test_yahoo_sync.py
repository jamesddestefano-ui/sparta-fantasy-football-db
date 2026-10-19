import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from sparta_names import name_key, defense_abbr  # noqa: E402
from yahoo_fixtures import write_fixtures  # noqa: E402
import yahoo_sync  # noqa: E402

OBSERVED = datetime(2026, 10, 21, 8, 0, tzinfo=yahoo_sync.yp.ET_TZ)


class NameKeyTests(unittest.TestCase):
    def test_defense_spellings_collapse(self):
        keys = {name_key("Ravens D/ST"), name_key("Ravens"), name_key("Baltimore Ravens DEF"),
                name_key("Baltimore", "Bal", "DEF")}
        self.assertEqual(keys, {"def:BAL"})

    def test_suffix_and_punctuation(self):
        self.assertEqual(name_key("Mike Washington Jr."), name_key("Mike Washington"))
        self.assertEqual(name_key("Ja'Marr Chase"), name_key("JaMarr Chase"))
        self.assertEqual(name_key("J.K. Dobbins"), name_key("JK Dobbins"))

    def test_player_named_like_a_city_is_not_a_defense(self):
        self.assertIsNone(defense_abbr("Bijan Robinson"))
        self.assertIsNone(defense_abbr("Jaguars Fan Club Member Extra"))


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(ROOT / "data", self.tmp / "data",
                        ignore=shutil.ignore_patterns("yahoo_live_snapshot_*", "transaction_appends", "yahoo_api"))
        self.fx = write_fixtures(self.tmp / "fixtures")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_sync(self, apply=False):
        client = yahoo_sync.FixtureClient(self.fx)
        return yahoo_sync.run(client, apply=apply, observed_at=OBSERVED, root=self.tmp)

    def test_report_only_mode_leaves_durable_files_untouched(self):
        before = {p.name: p.read_text() for p in (self.tmp / "data").glob("*.json")}
        result = self.run_sync()
        after = {p.name: p.read_text() for p in (self.tmp / "data").glob("*.json")}
        self.assertEqual(before, after)
        self.assertFalse(result["report"]["applied"])
        self.assertTrue((self.tmp / "data/yahoo_api/latest.json").exists())
        self.assertTrue((self.tmp / "data/yahoo_api/reconciliation_latest.json").exists())

    def test_team_mapping_uses_pin_name_and_manager(self):
        snap = self.run_sync()["snapshot"]
        self.assertTrue(snap["team_mapping_complete"])
        codes = {t["team_id"]: t["code"] for t in snap["teams"]}
        self.assertEqual(codes[10], "JD")   # pinned
        self.assertEqual(codes[4], "TM")    # renamed, matched by manager
        self.assertEqual(codes[11], "JU")   # matched by name
        self.assertEqual(snap["jd"]["faab_balance"], 28)
        self.assertEqual(snap["current_week"], 7)

    def test_reconciliation_detects_only_genuinely_new_moves(self):
        rep = self.run_sync()["report"]
        new = {(t["team"], t["added"], t["dropped"]) for t in rep["new_transactions"]}
        self.assertEqual(new, {("JD", "Kyle Monangai", "Dylan Sampson"), ("VV", "Broncos D/ST", None)})
        jd = next(t for t in rep["new_transactions"] if t["team"] == "JD")
        self.assertEqual((jd["faab_bid"], jd["via"], jd["action"]), (5, "waiver", "ADD_DROP"))
        self.assertEqual([r["reason"] for r in rep["needs_review"]], ["trade"])
        self.assertIn({"team": "JD", "repo": 33, "yahoo": 28}, rep["faab_diffs"])
        self.assertEqual(rep["jd_roster_diff"], {"on_yahoo_not_repo": ["Kyle Monangai"],
                                                 "on_repo_not_yahoo": ["Dylan Sampson"]})
        self.assertFalse(rep["in_sync"])

    def test_free_agents_exclude_rostered_players(self):
        snap = self.run_sync()["snapshot"]
        rb = [p["name"] for p in snap["free_agents"]["RB"]]
        self.assertNotIn("Kyle Monangai", rb)
        self.assertEqual(rb, ["Waiver Back", "Free Back"])

    def test_apply_is_valid_and_idempotent(self):
        before = json.loads((self.tmp / "data/transactions.json").read_text())
        res = self.run_sync(apply=True)
        self.assertTrue(res["report"]["applied"])
        tx = json.loads((self.tmp / "data/transactions.json").read_text())
        self.assertEqual(len(tx["transactions"]), len(before["transactions"]) + 2)
        self.assertEqual(tx["transaction_count"], len(tx["transactions"]))
        self.assertEqual(tx["transactions"][:len(before["transactions"])], before["transactions"])
        faab = json.loads((self.tmp / "data/faab.json").read_text())
        self.assertEqual(faab["jd_authoritative_balance"], 28)
        out = subprocess.run([sys.executable, str(ROOT / "scripts/validate_sparta.py"), str(self.tmp / "data")],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("jd_faab=28 waiver_priority=1", out.stdout)

        second = self.run_sync(apply=True)["report"]
        self.assertEqual(second["new_transactions"], [])
        self.assertEqual(second["faab_diffs"], [])
        self.assertEqual(second["jd_roster_diff"], {"on_yahoo_not_repo": [], "on_repo_not_yahoo": []})
        self.assertEqual(len(second["needs_review"]), 1)  # trades always stay for review

    def test_apply_refused_when_teams_unmapped(self):
        (self.tmp / "data/yahoo_team_map.json").write_text(json.dumps({"team_id_to_code": {}}))
        teams = json.loads((self.tmp / "data/teams.json").read_text())
        teams["teams"][3]["manager_display"] = "someone else"  # break TM's manager match
        (self.tmp / "data/teams.json").write_text(json.dumps(teams))
        with self.assertRaises(RuntimeError):
            self.run_sync(apply=True)


if __name__ == "__main__":
    unittest.main()
