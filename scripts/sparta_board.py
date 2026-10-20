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
from datetime import datetime, timezone
import hashlib
import subprocess
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
        status = (r.get("status") or "").upper()
        if status == "BYE":
            status = ""          # snapshot is from a prior week; FantasyPros bye_week decides this week
        status = status or (f.get("injury_status") or "").upper()
        bye = str(f.get("bye_week") or "") == str(week)
        mine.append({
            "name": r["name"], "position": pos, "nfl_team": r.get("nfl_team"), "current_slot": r.get("slot"),
            "yahoo_status": r.get("status") or "", "fp_injury": f.get("injury_status"),
            "proj_ppr": f.get("proj_ppr"), "ecr_rank": f.get("ecr_rank"), "ros_rank": f.get("ros_rank"),
            "opponent": f.get("opponent"), "matched_fantasypros": bool(f),
            "yahoo_rostered_pct": f.get("yahoo_rostered_pct"),
            "unavailable": status in OUT_STATUSES or bye or (r.get("slot") or "").startswith("IR"),
            "on_bye": bye,
        })

    def score(p):
        """Projected PPR points; falls back to a rank-based estimate when projections are missing."""
        if p.get("proj_ppr") is not None:
            return p["proj_ppr"]
        if p.get("ecr_rank"):
            return max(0.0, 20.0 - p["ecr_rank"] / 8.0)   # coarse: rank 1 ~ 20 pts, rank 120 ~ 5 pts
        return -1

    # ---- optimal lineup (greedy is optimal: flex is a superset of RB/WR/TE)
    pool = sorted([p for p in mine if not p["unavailable"]], key=score, reverse=True)
    lineup, used = [], set()
    for slot in STARTER_SLOTS:
        allowed = FLEX_OK if slot == "W/R/T" else {slot}
        pick = next((p for p in pool if p["name"] not in used and p["position"] in allowed), None)
        if pick:
            used.add(pick["name"])
        lineup.append({"slot": slot, "player": pick["name"] if pick else None,
                       "proj_ppr": pick["proj_ppr"] if pick else None,
                       "ecr_rank": pick["ecr_rank"] if pick else None,
                       "basis": ("projection" if pick and pick["proj_ppr"] is not None
                                 else "ranking" if pick and pick["ecr_rank"] else "none")})
    current_starters = {p["name"] for p in mine if p["current_slot"] not in ("BN", "IR", "IR+", None)}
    suggested = {s["player"] for s in lineup if s["player"]}
    changes = {
        "start": sorted(suggested - current_starters),
        "bench": sorted(current_starters - suggested),
    }
    by_name = {p["name"]: p for p in mine}
    proj_current = sum(max(score(p), 0) for p in mine if p["name"] in current_starters)
    proj_suggested = sum(max(score(by_name[s["player"]]), 0) for s in lineup if s["player"])

    # ---- waiver targets: not owned on reconstructed rosters, better than JD's weakest at the position
    starter_proj = {}
    for slot in lineup:
        if slot["slot"] in POSITIONS and slot["player"]:
            sp = by_name[slot["player"]]
            starter_proj[slot["slot"]] = min(starter_proj.get(slot["slot"], 1e9), score(sp))
    weakest = {}
    active = [p for p in mine if not (p["current_slot"] or "").startswith("IR")]   # IR slot doesn't use a roster spot
    open_spots = max(0, 17 - len(active))
    for pos in POSITIONS:
        at = [p for p in active if p["position"] == pos]
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
        # weekly upgrade is measured against the player who would actually start for JD at that position
        week_gain = (f["proj_ppr"] - starter_proj.get(pos, 0.0)) if f.get("proj_ppr") is not None else None
        wr = f.get("waiver_rank")
        flex_list = (f.get("waiver_list") or "FLX") == "FLX"
        if not ((ros_gain and ros_gain > 0) or (week_gain and week_gain > 1.0) or (wr and wr <= 15)):
            continue
        if not flex_list and not (week_gain and week_gain > 0):
            # QB/K/DEF waiver lists are short weekly streaming lists; rank 1-5 there is not a priority add
            tier = "STREAM"
        else:
            tier = ("HIGH" if (ros_gain or 0) >= 40 or (week_gain or 0) >= 6 or (flex_list and wr and wr <= 5)
                    else "MEDIUM" if (ros_gain or 0) >= 15 or (week_gain or 0) >= 3 or (flex_list and wr and wr <= 12)
                    else "LOW")
        pct = f.get("yahoo_rostered_pct")
        targets.append({
            "name": f["name"], "position": pos, "nfl_team": f.get("nfl_team"),
            "proj_ppr": f.get("proj_ppr"), "ecr_rank": f.get("ecr_rank"), "ros_rank": f.get("ros_rank"),
            "injury": f.get("injury_status"), "replaces": w["name"] if w else None,
            "ros_rank_gain": ros_gain, "week_proj_gain": round(week_gain, 2) if week_gain is not None else None,
            "priority": tier, "availability": own["status"],
            "fp_waiver_rank": wr, "yahoo_rostered_pct": pct, "fp_waiver_note": f.get("waiver_note"),
            "availability_note": (("Likely available: rostered in only %d%% of Yahoo leagues. " % pct if pct is not None and pct < 30 else "")
                                  + "Verify on Yahoo before claiming (not confirmed available).")
            if own["status"].startswith("UNKNOWN") else own.get("source"),
        })
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "STREAM": 3}
    targets.sort(key=lambda t: (order[t["priority"]], t["fp_waiver_rank"] or 999, t["ros_rank"] or 9999,
                                -(t["proj_ppr"] or 0)))

    notes = []
    if open_spots:
        notes.append(f"{open_spots} open roster spot(s) ({len(active)}/17 active): your top waiver target can be "
                     f"added without dropping anyone.")
    ir_used = [p for p in mine if (p["current_slot"] or "").startswith("IR")]
    ir_eligible = [p for p in mine if not (p["current_slot"] or "").startswith("IR") and
                   ((p["yahoo_status"] or "").upper().startswith("IR") or (p["fp_injury"] or "").upper() in ("IR", "PUP"))]
    if ir_eligible and not ir_used:
        notes.append("IR slot is empty; IR-eligible on bench: " + ", ".join(
            f"{p['name']} ({p['fp_injury'] or p['yahoo_status']})" for p in ir_eligible)
                     + ". Moving one to IR frees a bench spot (only 1 IR slot).")
    for p in mine:
        ys = (p["yahoo_status"] or "").upper()
        if ys in ("D", "DOUBTFUL", "O", "OUT") and not p["fp_injury"] and (p["proj_ppr"] or 0) > 5:
            notes.append(f"{p['name']}: Yahoo shows '{p['yahoo_status']}' (roster snapshot), but FantasyPros lists no injury "
                         f"for this week and projects {p['proj_ppr']}. Check his practice reports before locking the lineup; "
                         f"he is kept out of the suggested lineup until Yahoo clears him.")
        if ys == "BYE":
            notes.append(f"{p['name']}: snapshot shows BYE (last week); treated as available this week.")
    jd_faab = next((b["balance"] for b in faab["balances"] if b["team"] == "JD"), None)
    return {
        "league": "sparta", "season": fp["season"], "week": week, "team": "JD",
        "kind": "INTELLIGENCE_BOARD_NOT_A_RECORDED_RECOMMENDATION",
        "generated_from": {"fantasypros_pulled_at": fp.get("pulled_at"),
                           "jd_roster_observed_at": roster.get("observed_at"),
                           "ownership_reconstruction_conflicts": len(recon["conflicts"]),
                           "teams_over_roster_limit": recon.get("over_limit_teams", {})},
        "faab": {"jd_balance": jd_faab, "minimum_bid": 1},
        "open_roster_spots": open_spots,
        "lineup": {"suggested": lineup, "changes": changes,
                   "proj_current_starters": round(proj_current, 2), "proj_suggested": round(proj_suggested, 2)},
        "roster": sorted(mine, key=lambda p: (POSITIONS.index(p["position"]) if p["position"] in POSITIONS else 9,
                                              -score(p))),
        "waiver_targets": targets[:25],
        "unmatched_roster_players": [p["name"] for p in mine if not p["matched_fantasypros"]],
        "roster_notes": notes,
    }


def to_markdown(b: dict) -> str:
    L = [f"# Sparta Week {b['week']} board — JD",
         "",
         "_Intelligence for the Brain, not a recorded recommendation. Waiver availability is **unconfirmed** until checked on Yahoo._",
         "",
         f"FAAB: **${b['faab']['jd_balance']}** (min bid $1) · FantasyPros pulled {b['generated_from']['fantasypros_pulled_at']} · roster as of {b['generated_from']['jd_roster_observed_at']}",
         "", "## Lineup", "", "| Slot | Player | Proj (PPR) | Week rank |", "|---|---|---|---|"]
    for s in b["lineup"]["suggested"]:
        L.append(f"| {s['slot']} | {s['player'] or '—'} | {s['proj_ppr'] if s['proj_ppr'] is not None else '—'} | "
                 f"{int(s['ecr_rank']) if s.get('ecr_rank') else '—'} |")
    ch = b["lineup"]["changes"]
    basis = {s.get("basis") for s in b["lineup"]["suggested"]}
    L += ["", f"Projected: current starters **{b['lineup']['proj_current_starters']}** → suggested **{b['lineup']['proj_suggested']}**"
          + (" (some values estimated from rankings; projections unavailable)" if "ranking" in basis else "")]
    if ch["start"] or ch["bench"]:
        L.append(f"Changes: start {', '.join(ch['start']) or '—'}; bench {', '.join(ch['bench']) or '—'}")
    else:
        L.append("No lineup changes suggested.")
    L += ["", "## Waiver targets", "", "| Pri | Player | Pos | FP waiver # | ROS rank | Yahoo % | Replaces | In Sparta |",
          "|---|---|---|---|---|---|---|---|"]
    for t in b["waiver_targets"]:
        avail = "verify (likely free)" if (t["availability"].startswith("UNKNOWN") and (t["yahoo_rostered_pct"] or 100) < 30) \
            else "verify" if t["availability"].startswith("UNKNOWN") else t["availability"]
        L.append(f"| {t['priority']} | {t['name']} ({t['nfl_team'] or ''}) | {t['position']} | {int(t['fp_waiver_rank']) if t['fp_waiver_rank'] else '—'} | "
                 f"{int(t['ros_rank']) if t['ros_rank'] else '—'} | {('%d%%' % t['yahoo_rostered_pct']) if t['yahoo_rostered_pct'] is not None else '—'} | "
                 f"{t['replaces'] or '—'} | {avail} |")
    if not b["waiver_targets"]:
        L.append("| — | No upgrades found among players not on reconstructed rosters | | | | | |")
    if b.get("roster_notes"):
        L += ["", "## Roster notes", ""] + [f"- {n}" for n in b["roster_notes"]]
    if b["unmatched_roster_players"]:
        L += ["", f"Not matched to FantasyPros: {', '.join(b['unmatched_roster_players'])}"]
    over = b["generated_from"]["teams_over_roster_limit"]
    if over:
        L += ["", f"Note: ownership ledger is missing drops for {over}; some 'owned' players may actually be available."]
    return "\n".join(L) + "\n"


def write_validation_receipt(week: int, root: Path = ROOT) -> dict:
    """Attest existing Sparta validation and exact offline builder read-back.

    This is not validation of the unresolved FantasyPros provider contract.
    A failure replaces any previous PASS receipt and fails the workflow.
    """
    root = Path(root)
    path = root / 'intelligence' / 'board' / f'{fp_weekly.SEASON}-w{week:02d}.json'
    proof_path = path.with_suffix('.validation.json')
    raw = path.read_bytes()
    proof = {
        'status': 'FAIL',
        'board_sha256': hashlib.sha256(raw).hexdigest(),
        'league': 'sparta', 'season': fp_weekly.SEASON, 'week': week,
        'validated_at_utc': datetime.now(timezone.utc).isoformat(),
        'validation_scope': 'EXISTING_SPARTA_VALIDATOR_AND_OFFLINE_BOARD_REBUILD',
        'provider_contract_validated': False,
    }
    try:
        checked = subprocess.run(
            [sys.executable, str(ROOT / 'scripts' / 'validate_sparta.py'), str(root / 'data')],
            capture_output=True, text=True, check=False)
        proof['sparta_validator_exit_code'] = checked.returncode
        if checked.returncode != 0:
            raise ValueError('Existing Sparta validation failed')
        board = json.loads(raw)
        # Reuse the existing builder rather than inventing a second board schema.
        expected = build_board(week, root=root)
        json.dumps(board, allow_nan=False)
        if board != expected or path.read_bytes() != raw:
            raise ValueError('Written board does not match its current offline inputs')
        proof['status'] = 'PASS'
    except (OSError, ValueError, KeyError, TypeError):
        proof['status'] = 'FAIL'
    temporary = proof_path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(proof, indent=2, allow_nan=False) + '\n')
    temporary.replace(proof_path)
    if json.loads(proof_path.read_text()) != proof:
        raise ValueError('Board receipt read-back failed')
    if proof['status'] != 'PASS':
        raise ValueError('Board validation failed; no PASS receipt issued')
    return proof


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", type=int, default=None)
    ap.add_argument("--validate-only", action="store_true", help="Validate existing board offline and write hash-bound receipt")
    args = ap.parse_args(argv)
    week = args.week or fp_weekly.current_week()
    if args.validate_only:
        try:
            proof = write_validation_receipt(week)
        except (OSError, ValueError):
            print("Board validation failed; no PASS receipt issued", file=sys.stderr)
            return 1
        print(f"BOARD VALIDATION {proof['status']} week={week} sha256={proof['board_sha256']}")
        return 0
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
