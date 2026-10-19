import json
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fp_weekly  # noqa: E402
import sparta_board  # noqa: E402
from sparta_ownership import reconstruct, ownership_status  # noqa: E402

WEEK = 7


def rank(name, team, pos, ecr, bye=10, opp="vs X"):
    return {"player_id": abs(hash(name)) % 99999, "player_name": name, "player_team_id": team,
            "player_position_id": pos, "rank_ecr": ecr, "player_bye_week": bye, "player_opponent": opp}


def proj(name, team, pos, pts):
    return {"fpid": str(abs(hash(name)) % 99999), "name": name, "team_id": team, "position_id": pos,
            "stats": [{"points": pts - 3, "points_ppr": pts, "points_half": pts - 1.5}]}


class OwnershipTests(unittest.TestCase):
    def test_reconstruction_matches_jd_snapshot_and_has_12_teams(self):
        r = reconstruct()
        jd_snapshot = {p["name"] for p in json.loads((ROOT / "data/current_roster_jd.json").read_text())["players"]}
        self.assertEqual(set(r["rosters"]["JD"]), jd_snapshot)
        self.assertEqual(len(r["rosters"]), 12)

    def test_unlisted_player_is_unknown_never_free_agent(self):
        r = reconstruct()
        self.assertEqual(ownership_status(r, "Totally Made Up Player")["status"], "UNKNOWN_NOT_ON_RECONSTRUCTED_ROSTERS")
        self.assertEqual(ownership_status(r, "Bijan Robinson")["status"], "OWNED")
        # Sep 17 "FA" confirmation is superseded: JU added him Oct 7 and dropped him Oct 12.
        # A drop does not prove free agency (AGENTS.md rule 8), so he is UNKNOWN, not FREE_AGENT_CONFIRMED.
        self.assertEqual(ownership_status(r, "Seth McGowan")["status"], "UNKNOWN_NOT_ON_RECONSTRUCTED_ROSTERS")


class WeekTests(unittest.TestCase):
    def test_week_rolls_over_on_tuesday(self):
        self.assertEqual(fp_weekly.current_week(date(2026, 9, 10)), 1)
        self.assertEqual(fp_weekly.current_week(date(2026, 10, 19)), 6)   # Monday night of week 6
        self.assertEqual(fp_weekly.current_week(date(2026, 10, 20)), 7)


class BoardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(ROOT / "data", self.tmp / "data",
                        ignore=shutil.ignore_patterns("yahoo_live_snapshot_*", "transaction_appends"))
        raw = fp_weekly.week_dir(WEEK, self.tmp) / "raw"
        raw.mkdir(parents=True)
        consensus_flx = {"sport": "NFL", "players": [
            rank("Ja'Marr Chase", "CIN", "WR", 3), rank("Jaxon Smith-Njigba", "SEA", "WR", 8),
            rank("Breece Hall", "NYJ", "RB", 15), rank("Bijan Robinson", "ATL", "RB", 1),
            rank("Tetairoa McMillan", "CAR", "WR", 30), rank("Braelon Allen", "NYJ", "RB", 40),
            rank("Emanuel Wilson", "SEA", "RB", 45), rank("J.K. Dobbins", "DEN", "RB", 50),
            rank("Devaughn Vele", "NO", "WR", 70), rank("Jacob Cowing", "SF", "WR", 90, bye=WEEK),
            rank("Darren Waller", "CAR", "TE", 120), rank("Unrostered Breakout", "ATL", "RB", 35),
            rank("Seth McGowan", "TEN", "RB", 110)]}
        (raw / "consensus_FLX.json").write_text(json.dumps(consensus_flx))
        (raw / "consensus_QB.json").write_text(json.dumps({"players": [
            rank("Jalen Hurts", "PHI", "QB", 5), rank("Kirk Cousins", "LV", "QB", 20)]}))
        ros = {"players": [rank("Unrostered Breakout", "ATL", "RB", 30), rank("Dylan Sampson", "CLE", "RB", 120),
                           rank("J.K. Dobbins", "DEN", "RB", 80), rank("Jaleel McLaughlin", "DEN", "RB", 150),
                           rank("Seth McGowan", "TEN", "RB", 140), rank("Bijan Robinson", "ATL", "RB", 1)]}
        (raw / "ros_FLX.json").write_text(json.dumps(ros))
        projections = {"players": [proj("Ja'Marr Chase", "CIN", "WR", 20.1), proj("Jaxon Smith-Njigba", "SEA", "WR", 17.5),
                                   proj("Tetairoa McMillan", "CAR", "WR", 12.0), proj("Devaughn Vele", "NO", "WR", 9.0),
                                   proj("Jacob Cowing", "SF", "WR", 0.0), proj("Dontayvion Wicks", "GB", "WR", 6.0)]}
        (raw / "projections_WR.json").write_text(json.dumps(projections))
        (raw / "projections_RB.json").write_text(json.dumps({"players": [
            proj("Breece Hall", "NYJ", "RB", 15.0), proj("Braelon Allen", "NYJ", "RB", 11.0),
            proj("Emanuel Wilson", "SEA", "RB", 10.5), proj("J.K. Dobbins", "DEN", "RB", 9.8),
            proj("Unrostered Breakout", "ATL", "RB", 13.0)]}))
        (raw / "projections_QB.json").write_text(json.dumps({"players": [
            proj("Jalen Hurts", "PHI", "QB", 22.0), proj("Kirk Cousins", "LV", "QB", 16.0)]}))
        (raw / "projections_TE.json").write_text(json.dumps({"players": [proj("Darren Waller", "CAR", "TE", 7.5)]}))
        (raw / "projections_K.json").write_text(json.dumps({"players": [proj("Blake Grupe", "LAR", "K", 8.0)]}))
        (raw / "projections_DST.json").write_text(json.dumps({"players": [
            {"name": "Baltimore Ravens", "team_id": "BAL", "position_id": "DST", "stats": [{"points": 7.0}]}]}))
        (raw / "injuries_ALL.json").write_text(json.dumps({"injuries": [
            {"name": "Jalen Hurts", "team_id": "PHI", "injury_status": "Out"}]}))
        self.norm = fp_weekly.run(WEEK, None, out_root=self.tmp, normalize_only=True)
        self.board = sparta_board.build_board(WEEK, root=self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_lenient_normalizer_reads_every_source(self):
        for label, r in self.norm["sources"].items():
            self.assertGreater(r["rows_used"], 0, label)
        ravens = next(p for p in self.norm["players"] if p["name"] == "Baltimore Ravens")
        self.assertEqual(ravens["proj_ppr"], 7.0)

    def test_lineup_benches_out_and_bye_players_and_fills_slots(self):
        slots = {(s["slot"], s["player"]) for s in self.board["lineup"]["suggested"]}
        names = [s["player"] for s in self.board["lineup"]["suggested"]]
        self.assertIn(("QB", "Kirk Cousins"), slots)          # Hurts is Out
        self.assertNotIn("Jacob Cowing", names)               # on bye
        self.assertIn(("DEF", "Ravens"), slots)               # "Baltimore Ravens" DST matched to "Ravens"
        self.assertEqual(len([n for n in names if n]), 10)
        self.assertNotIn("Breece Hall", names)                # Yahoo status D (doubtful)
        self.assertIn("Ja'Marr Chase", self.board["lineup"]["changes"]["start"])  # 20.1 proj, was on bench

    def test_waiver_targets_exclude_owned_and_never_claim_confirmed_availability(self):
        names = {t["name"]: t for t in self.board["waiver_targets"]}
        self.assertIn("Unrostered Breakout", names)
        self.assertNotIn("Bijan Robinson", names)              # owned by TM
        self.assertEqual(names["Unrostered Breakout"]["availability"], "UNKNOWN_NOT_ON_RECONSTRUCTED_ROSTERS")
        self.assertIn("Verify on Yahoo", names["Unrostered Breakout"]["availability_note"])
        self.assertEqual(self.board["kind"], "INTELLIGENCE_BOARD_NOT_A_RECORDED_RECOMMENDATION")

    def test_markdown_renders(self):
        md = sparta_board.to_markdown(self.board)
        self.assertIn("## Lineup", md)
        self.assertIn("unconfirmed", md)


if __name__ == "__main__":
    unittest.main()
