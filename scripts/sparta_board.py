"""Sparta weekly board: JD lineup suggestions and waiver targets from FantasyPros.

Inputs (all from the repository):
  intelligence/fantasypros/weekly/<season>-wNN/players.json   (scripts/fp_weekly.py)
  data/current_roster_jd.json, data/faab.json, ownership reconstruction (sparta_ownership.py)

Outputs:
  intelligence/board/<season>-wNN.json and .md

This is intelligence for the Sparta Brain, not a recorded recommendation
(AGENTS.md rules 16-18, 39). Waiver targets are players NOT owned per the
reconstruction; their availability stays UNKNOWN until Yahoo confirms it
(rule 3), and the board says so on every line.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sparta_names import name_key  # noqa: E402
from sparta_ownership import reconstruct, ownership_status  # noqa: E402
import fp_weekly  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STARTER_SLOTS = ["QB", "RB", "RB", "WR", "WR", "TE", "W/R/T", "W/R/T", "K", "DEF"]
FLEX_OK = {"RB", "WR", "TE"}
OUT_STATUSES = {"O", "OUT", "IR", "IR-R", "PUP", "NA", "SUSP", "D", "DOUBTFUL"}
POSITIONS = ["QB", "RB", "WR", "TE", "K", "DEF"]


def _pos(p: dict) -> str:
    pos = (p.get("position") or "").upper()
    return "DEF" if pos in ("DST", "D/ST", "DEF") else pos


def build_board(week: int, root: Path = ROOT) -> dict:
    fp = json.loads((fp_weekly.week_dir(week, root) / "players.json").read_text())
    by_key = {}
    for p in fp["players"]:
        k = name_key(p["name"], p.get("nfl_team"), _pos(p))
        if k:
            by_key[k] = p
    roster = json.loads((root / "data" / "current_roster_jd.json").read_text())
    faab = json.loads((root / "data" / "faab.json").read_text())
    recon = reconstruct(root / "data")

    # ---- JD players joined with FantasyPros
    mine = []
    for r in roster["players"]:
        pos = _pos(r) or "?"
        k = name_key(r["name"], r.get("nfl_team"), pos)
        f = by_key.get(k, {})
        status = (r.get("status") or f.get("injury_status") or "").upper()
        bye = str(f.get("bye_week") or "") == str(week)
        mine.append({
            "name": r["name"], "position": pos, "nfl_team": r.get("nfl_team"), "current_slot": r.get("slot"),
            "yahoo_status": r.get("status") or "", "fp_injury": f.get("injury_status"),
            "proj_ppr": f.get("proj_ppr"), "ecr_rank": f.get("ecr_rank"), "ros_rank": f.get("ros_rank"),
            "opponent": f.get("opponent"), "matched_fantasypros": bool(f),
            "unavailable": status in OUT_STATUSES or bye or (r.get("slot") or "").startswith("IR"),
            "on_bye": bye,
        })

    def score(p):
        return p["proj_ppr"] if p["proj_ppr"] is not None else -1

    # ---- optimal lineup (greedy is optimal: flex is a superset of RB/WR/TE)
    pool = sorted([p for p in mine if not p["unavailable"]], key=score, reverse=True)
    lineup, used = [], set()
    for slot in STARTER_SLOTS:
        allowed = FLEX_OK if slot == "W/R/T" else {slot}
        pick = next((p for p in pool if p["name"] not in used and p["position"] in allowed), None)
        if pick:
            used.add(pick["name"])
        lineup.append({"slot": slot, "player": pick["name"] if pick else None,
                       "proj_ppr": pick["proj_ppr"] if pick else None})
    current_starters = {p["name"] for p in mine if p["current_slot"] not in ("BN", "IR", "IR+", None)}
    suggested = {s["player"] for s in lineup if s["player"]}
    changes = {
        "start": sorted(suggested - current_starters),
        "bench": sorted(current_starters - suggested),
    }
    proj_current = sum((p["proj_ppr"] or 0) for p in mine if p["name"] in current_starters)
    proj_suggested = sum((s["proj_ppr"] or 0) for s in lineup)

    # ---- waiver targets: not owned on reconstructed rosters, better than JD's weakest at the position
    weakest = {}
    for pos in POSITIONS:
        at = [p for p in mine if p["position"] == pos]
        if at:
            weakest[pos] = min(at, key=lambda p: (p["ros_rank"] is None, -(p["ros_rank"] or 0), score(p)))
    targets = []
    for f in fp["players"]:
        pos = _pos(f)
        if pos not in POSITIONS:
            continue
        own = ownership_status(recon, f["name"], f.get("nfl_team"), pos)
        if own["status"] == "OWNED":
            continue
        w = weakest.get(pos)
        ros_gain = (w["ros_rank"] - f["ros_rank"]) if (w and w.get("ros_rank") and f.get("ros_rank")) else None
        week_gain = (f["proj_ppr"] - (w["proj_ppr"] or 0)) if (w and f.get("proj_ppr") is not None) else None
        if not ((ros_gain and ros_gain > 0) or (week_gain and week_gain > 1.0)):
            continue
        tier = ("HIGH" if (ros_gain or 0) >= 40 or (week_gain or 0) >= 6
                else "MEDIUM" if (ros_gain or 0) >= 15 or (week_gain or 0) >= 3 else "LOW")
        targets.append({
            "name": f["name"], "position": pos, "nfl_team": f.get("nfl_team"),
            "proj_ppr": f.get("proj_ppr"), "ecr_rank": f.get("ecr_rank"), "ros_rank": f.get("ros_rank"),
            "injury": f.get("injury_status"), "replaces": w["name"] if w else None,
            "ros_rank_gain": ros_gain, "week_proj_gain": round(week_gain, 2) if week_gain is not None else None,
            "priority": tier, "availability": own["status"],
            "availability_note": "Verify on Yahoo before claiming (not confirmed available)."
            if own["status"].startswith("UNKNOWN") else own.get("source"),
        })
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    targets.sort(key=lambda t: (order[t["priority"]], t["ros_rank"] or 9999, -(t["proj_ppr"] or 0)))

    jd_faab = next((b["balance"] for b in faab["balances"] if b["team"] == "JD"), None)
    return {
        "league": "sparta", "season": fp["season"], "week": week, "team": "JD",
        "kind": "INTELLIGENCE_BOARD_NOT_A_RECORDED_RECOMMENDATION",
        "generated_from": {"fantasypros_pulled_at": fp.get("pulled_at"),
                           "jd_roster_observed_at": roster.get("observed_at"),
                           "ownership_reconstruction_conflicts": len(recon["conflicts"]),
                           "teams_over_roster_limit": recon.get("over_limit_teams", {})},
        "faab": {"jd_balance": jd_faab, "minimum_bid": 1},
        "lineup": {"suggested": lineup, "changes": changes,
                   "proj_current_starters": round(proj_current, 2), "proj_suggested": round(proj_suggested, 2)},
        "roster": sorted(mine, key=lambda p: (POSITIONS.index(p["position"]) if p["position"] in POSITIONS else 9,
                                              -score(p))),
        "waiver_targets": targets[:25],
        "unmatched_roster_players": [p["name"] for p in mine if not p["matched_fantasypros"]],
    }


def to_markdown(b: dict) -> str:
    L = [f"# Sparta Week {b['week']} board — JD",
         "",
         "_Intelligence for the Brain, not a recorded recommendation. Waiver availability is **unconfirmed** until checked on Yahoo._",
         "",
         f"FAAB: **${b['faab']['jd_balance']}** (min bid $1) · FantasyPros pulled {b['generated_from']['fantasypros_pulled_at']} · roster as of {b['generated_from']['jd_roster_observed_at']}",
         "", "## Lineup", "", "| Slot | Player | Proj (PPR) |", "|---|---|---|"]
    for s in b["lineup"]["suggested"]:
        L.append(f"| {s['slot']} | {s['player'] or '—'} | {s['proj_ppr'] if s['proj_ppr'] is not None else '—'} |")
    ch = b["lineup"]["changes"]
    L += ["", f"Projected: current starters **{b['lineup']['proj_current_starters']}** → suggested **{b['lineup']['proj_suggested']}**"]
    if ch["start"] or ch["bench"]:
        L.append(f"Changes: start {', '.join(ch['start']) or '—'}; bench {', '.join(ch['bench']) or '—'}")
    else:
        L.append("No lineup changes suggested.")
    L += ["", "## Waiver targets", "", "| Pri | Player | Pos | Proj | ROS rank | Replaces | Availability |", "|---|---|---|---|---|---|---|"]
    for t in b["waiver_targets"]:
        L.append(f"| {t['priority']} | {t['name']} ({t['nfl_team'] or ''}) | {t['position']} | {t['proj_ppr'] if t['proj_ppr'] is not None else '—'} | "
                 f"{int(t['ros_rank']) if t['ros_rank'] else '—'} | {t['replaces'] or '—'} | {t['availability']} |")
    if not b["waiver_targets"]:
        L.append("| — | No upgrades found among players not on reconstructed rosters | | | | | |")
    if b["unmatched_roster_players"]:
        L += ["", f"Not matched to FantasyPros: {', '.join(b['unmatched_roster_players'])}"]
    over = b["generated_from"]["teams_over_roster_limit"]
    if over:
        L += ["", f"Note: ownership ledger is missing drops for {over}; some 'owned' players may actually be available."]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", type=int, default=None)
    args = ap.parse_args(argv)
    week = args.week or fp_weekly.current_week()
    b = build_board(week)
    out = ROOT / "intelligence" / "board"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{b['season']}-w{week:02d}.json").write_text(json.dumps(b, indent=1, ensure_ascii=False) + "\n")
    md = to_markdown(b)
    (out / f"{b['season']}-w{week:02d}.md").write_text(md)
    (out / "latest.md").write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
