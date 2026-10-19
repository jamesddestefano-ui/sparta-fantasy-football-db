"""Sparta Yahoo Fantasy API sync.

Pulls authenticated, read-only Yahoo state for Sparta (Yahoo league 102586),
writes `data/yahoo_api/latest.json`, appends a one-line summary to
`data/yahoo_api/history.jsonl`, and writes a reconciliation report comparing
Yahoo against the repository's durable state.

Default mode is REPORT-ONLY: durable files under data/ are not modified.
With --apply, Yahoo-confirmed changes are written through the AGENTS.md rules:
  * new successful add / drop / add-drop transactions are appended (never rewritten)
  * FAAB balances, waiver priority and JD's roster are refreshed
  * trades and anything ambiguous are left for review, never auto-applied

Usage:
  python scripts/yahoo_sync.py                 # live pull, report only
  python scripts/yahoo_sync.py --apply         # live pull, apply confirmed changes
  python scripts/yahoo_sync.py --fixture-dir tests/fixtures/yahoo   # offline
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yahoo_parse as yp  # noqa: E402
from sparta_names import defense_abbr, defense_display, name_key, NFL_TEAMS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SPARTA_YAHOO_LEAGUE_ID = "102586"
SPARTA_SEASON = 2026
FA_POSITIONS = {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "K": 1, "DEF": 1}  # pages of 25
SOURCE_LABEL = "Yahoo Fantasy API v2 (OAuth, read-only) via scripts/yahoo_sync.py"


# ------------------------------------------------------------------ io utils

def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text())


def dump_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def now_et() -> datetime:
    return datetime.now(tz=yp.ET_TZ).replace(microsecond=0)


# ------------------------------------------------------------------- fetching

class FixtureClient:
    """Offline stand-in for YahooClient: maps request paths to fixture XML files."""

    def __init__(self, fixture_dir: Path):
        self.dir = Path(fixture_dir)
        self.requests_made = 0
        self.refresh_token_rotated = False

    def get(self, path: str):
        import xml.etree.ElementTree as ET
        from yahoo_client import strip_namespaces
        self.requests_made += 1
        name = fixture_name(path)
        f = self.dir / name
        if not f.exists():
            # Paged endpoints past the last fixture page return an empty collection.
            return ET.fromstring("<fantasy_content/>")
        return strip_namespaces(ET.fromstring(f.read_bytes()))


def fixture_name(path: str) -> str:
    """Stable fixture filename for an API path, e.g. league/K/teams/roster -> teams_roster.xml."""
    p = path.split("?")[0]
    if p.startswith("game/"):
        return "game.xml"
    parts = p.split("/")
    rest = parts[2:] if len(parts) > 2 else []
    if not rest:
        return "league.xml"
    head = rest[0]
    if head.startswith("players;"):
        params = dict(kv.split("=", 1) for kv in head.split(";")[1:] if "=" in kv)
        return f"players_{params.get('position', 'ALL')}_{params.get('start', '0')}.xml"
    if head.startswith("transactions"):
        params = dict(kv.split("=", 1) for kv in head.split(";")[1:] if "=" in kv)
        return f"transactions_{params.get('start', '0')}.xml"
    if head.startswith("scoreboard"):
        return "scoreboard.xml"
    return "_".join(r.split(";")[0] for r in rest) + ".xml"


def fetch_all(client, league_id: str = SPARTA_YAHOO_LEAGUE_ID) -> dict:
    game_key = yp.parse_game_key(client.get("game/nfl"))
    league_key = f"{game_key}.l.{league_id}"
    meta = yp.parse_league_meta(client.get(f"league/{league_key}"))
    if meta.get("league_id") != league_id:
        raise RuntimeError(f"Yahoo returned league {meta.get('league_id')}, expected {league_id}")
    if meta.get("season") != SPARTA_SEASON:
        raise RuntimeError(f"Yahoo returned season {meta.get('season')}, expected {SPARTA_SEASON}")
    week = meta.get("current_week")

    teams = yp.parse_teams(client.get(f"league/{league_key}/teams"))
    rosters = yp.parse_rosters(client.get(f"league/{league_key}/teams/roster"))
    standings = yp.parse_standings(client.get(f"league/{league_key}/standings"))
    scoreboard = yp.parse_scoreboard(client.get(f"league/{league_key}/scoreboard;week={week}"))

    transactions: list[dict] = []
    for page in range(40):
        batch = yp.parse_transactions(
            client.get(f"league/{league_key}/transactions;start={page * 25};count=25"))
        transactions.extend(batch)
        if len(batch) < 25:
            break

    free_agents: dict[str, list[dict]] = {}
    for pos, pages in FA_POSITIONS.items():
        rows: list[dict] = []
        for page in range(pages):
            batch = yp.parse_players(client.get(
                f"league/{league_key}/players;status=A;position={pos};sort=AR;"
                f"start={page * 25};count=25;out=percent_owned,ownership"))
            rows.extend(batch)
            if len(batch) < 25:
                break
        free_agents[pos] = rows

    return {
        "game_key": game_key,
        "league_key": league_key,
        "league": meta,
        "teams": teams,
        "rosters": rosters,
        "standings": standings,
        "scoreboard": scoreboard,
        "transactions": transactions,
        "free_agents": free_agents,
    }


# ------------------------------------------------------------ team mapping

def _norm(s: str | None) -> str:
    return " ".join((s or "").lower().replace("&", "and").split())


def map_teams(yahoo_teams: list[dict], repo_teams: list[dict], pinned: dict | None) -> dict[str, str]:
    """Return {yahoo team_key: repo team code}. Pinned team_id map wins, then name,
    then manager display name, then the authenticated owner (JD)."""
    pinned = pinned or {}
    by_name = {_norm(t["team_name"]): t["code"] for t in repo_teams}
    by_mgr = {_norm(t.get("manager_display")): t["code"] for t in repo_teams}
    mine = next((t["code"] for t in repo_teams if t.get("is_mine")), "JD")
    out: dict[str, str] = {}
    for t in yahoo_teams:
        code = pinned.get(str(t["team_id"]))
        if not code:
            code = by_name.get(_norm(t["name"]))
        if not code:
            for m in t.get("managers", []):
                code = by_mgr.get(_norm(m.get("nickname")))
                if code:
                    break
        if not code and t.get("is_owned_by_current_login"):
            code = mine
        if code:
            out[t["team_key"]] = code
    return out


# --------------------------------------------------- transaction conversion

def display_name(player: dict) -> str:
    abbr = defense_abbr(player.get("name"), player.get("nfl_team"), player.get("position"))
    return defense_display(abbr) if abbr else player.get("name")


def convert_transaction(tx: dict, team_map: dict[str, str], team_names: dict[str, str]) -> dict | None:
    """Yahoo transaction -> repository-style record. Returns None for failed/pending."""
    if tx.get("status") != "successful":
        return None
    ytype = (tx.get("type") or "").lower()
    adds = [p for p in tx["players"] if p.get("type") == "add"]
    drops = [p for p in tx["players"] if p.get("type") == "drop"]
    day = (tx.get("timestamp_et") or "")[:10]
    base = {
        "timestamp_et": (tx.get("timestamp_et") or "").replace("T", " ")[:16],
        "calendar_day_et": day,
        "yahoo_transaction_key": tx.get("transaction_key"),
        "league": SPARTA_YAHOO_LEAGUE_ID,
        "yahoo_league_id": SPARTA_YAHOO_LEAGUE_ID,
    }
    if ytype == "trade":
        sides = {}
        for p in tx["players"]:
            dest = team_map.get(p.get("destination_team_key"), p.get("destination_team_key"))
            sides.setdefault(dest, []).append(display_name(p))
        return {**base, "team": team_map.get(tx.get("trader_team_key"), tx.get("trader_team_key")),
                "action": "TRADE", "received_by_team": sides, "added": None, "dropped": None,
                "faab_bid": None, "via": "trade"}
    if ytype not in ("add", "drop", "add/drop"):
        return None
    add, drop = (adds[0] if adds else None), (drops[0] if drops else None)
    team_key = (add or {}).get("destination_team_key") or (drop or {}).get("source_team_key")
    team = team_map.get(team_key)
    action = {"add": "ADD", "drop": "DROP", "add/drop": "ADD_DROP"}[ytype]
    via = None
    if add:
        via = {"freeagents": "free_agent", "waivers": "waiver"}.get(add.get("source_type"), add.get("source_type"))
    added = display_name(add) if add else None
    dropped = display_name(drop) if drop else None
    faab = tx.get("faab_bid")
    if faab is None and add:
        faab = 0
    rec = {**base, "team": team or team_key, "team_name": team_names.get(team or "", None),
           "action": action, "added": added, "dropped": dropped, "faab_bid": faab, "via": via,
           "_added_key": name_key(add["name"], add.get("nfl_team"), add.get("position")) if add else None,
           "_dropped_key": name_key(drop["name"], drop.get("nfl_team"), drop.get("position")) if drop else None,
           "_team_mapped": team is not None}
    rec["semantic_key"] = f"{SPARTA_YAHOO_LEAGUE_ID}|{rec['team']}|{action}|{added or ''}|{dropped or ''}|{day}"
    return rec


def _repo_day(rec: dict) -> date | None:
    raw = rec.get("calendar_day_et") or (rec.get("timestamp_et") or "")[:10]
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def is_recorded(yrec: dict, repo_txs: list[dict]) -> bool:
    ykey = yrec.get("yahoo_transaction_key")
    yday = _repo_day(yrec)
    for r in repo_txs:
        if ykey and r.get("yahoo_transaction_key") == ykey:
            return True
        if r.get("team") != yrec["team"] or r.get("action") != yrec["action"]:
            continue
        if name_key(r.get("added")) != yrec.get("_added_key"):
            continue
        if name_key(r.get("dropped")) != yrec.get("_dropped_key"):
            continue
        rday = _repo_day(r)
        # Yahoo shows Pacific time in the UI; allow one day of slack for older hand-entered rows.
        if yday is None or rday is None or abs((yday - rday).days) <= 1:
            return True
    return False


# ---------------------------------------------------------------- snapshot

def build_snapshot(raw: dict, repo: dict, observed_at: datetime, requests_made: int) -> dict:
    team_map = map_teams(raw["teams"], repo["teams"], repo.get("pinned_map"))
    code_names = {t["code"]: t["team_name"] for t in repo["teams"]}
    standings = {s["team_key"]: s for s in raw["standings"]}
    teams = []
    for t in raw["teams"]:
        code = team_map.get(t["team_key"])
        roster = raw["rosters"].get(t["team_key"], [])
        teams.append({
            "code": code,
            "team_key": t["team_key"],
            "team_id": t["team_id"],
            "team_name": t["name"],
            "managers": [m["nickname"] for m in t["managers"]],
            "faab_balance": t["faab_balance"],
            "waiver_priority": t["waiver_priority"],
            "number_of_moves": t["number_of_moves"],
            "standing": standings.get(t["team_key"]),
            "roster": roster,
        })
    week = raw["league"]["current_week"]
    matchups = []
    for m in raw["scoreboard"]:
        matchups.append({**m, "teams": [{**tm, "code": team_map.get(tm["team_key"])} for tm in m["teams"]]})
    converted = [c for c in (convert_transaction(tx, team_map, code_names) for tx in raw["transactions"]) if c]
    owned_keys = {p["player_key"] for r in raw["rosters"].values() for p in r}
    free_agents = {
        pos: [p for p in rows if p["player_key"] not in owned_keys]
        for pos, rows in raw["free_agents"].items()
    }
    jd = next((t for t in teams if t["code"] == "JD"), None)
    jd_matchup = next((m for m in matchups if any(tm["code"] == "JD" for tm in m["teams"])), None)
    stamp = observed_at.strftime("%Y%m%d-%H%M")
    return {
        "league": "sparta",
        "league_id": SPARTA_YAHOO_LEAGUE_ID,
        "yahoo_league_id": SPARTA_YAHOO_LEAGUE_ID,
        "yahoo_league_key": raw["league_key"],
        "yahoo_league_name": raw["league"]["name"],
        "season": raw["league"]["season"],
        "current_week": week,
        "check_id": f"sparta-yahoo-api-{stamp}",
        "observed_at": observed_at.isoformat(),
        "completed": True,
        "source": SOURCE_LABEL,
        "mutations": False,
        "api_requests": requests_made,
        "team_mapping_complete": len(team_map) == len(raw["teams"]) == 12,
        "unmapped_teams": [t["name"] for t in raw["teams"] if t["team_key"] not in team_map],
        "jd": {
            "team_key": jd["team_key"] if jd else None,
            "faab_balance": jd["faab_balance"] if jd else None,
            "waiver_priority": jd["waiver_priority"] if jd else None,
            "standing": jd["standing"] if jd else None,
            "matchup": jd_matchup,
        },
        "teams": teams,
        "matchups": matchups,
        "transactions": [{k: v for k, v in c.items() if not k.startswith("_")} for c in converted],
        "free_agents_note": "status=A (free agents + players on waivers), Yahoo actual-rank order; "
                            "ownership_type 'waivers' means a claim is required.",
        "free_agents": free_agents,
        "_converted": converted,
    }


# ----------------------------------------------------------- reconciliation

def reconcile(snap: dict, repo: dict) -> dict:
    repo_txs = repo["transactions"]["transactions"]
    new_tx, review = [], []
    for c in snap["_converted"]:
        if is_recorded(c, repo_txs):
            continue
        clean = {k: v for k, v in c.items() if not k.startswith("_")}
        if c["action"] == "TRADE" or not c.get("_team_mapped"):
            review.append({**clean, "reason": "trade" if c["action"] == "TRADE" else "unmapped team"})
        else:
            new_tx.append(clean)
    new_tx.sort(key=lambda r: r["timestamp_et"])

    repo_faab = {b["team"]: b["balance"] for b in repo["faab"].get("balances", [])}
    faab_diffs = [
        {"team": t["code"], "repo": repo_faab.get(t["code"]), "yahoo": t["faab_balance"]}
        for t in snap["teams"] if t["code"] and t["faab_balance"] is not None
        and repo_faab.get(t["code"]) != t["faab_balance"]
    ]
    repo_prio = {r["team"]: r["priority"] for r in repo["waiver"].get("priority_order", [])}
    waiver_diffs = [
        {"team": t["code"], "repo": repo_prio.get(t["code"]), "yahoo": t["waiver_priority"]}
        for t in snap["teams"] if t["code"] and t["waiver_priority"] is not None
        and repo_prio.get(t["code"]) != t["waiver_priority"]
    ]
    jd = next((t for t in snap["teams"] if t["code"] == "JD"), None)
    roster_diff = None
    if jd:
        repo_names = {name_key(p["name"], p.get("nfl_team"), p.get("position")): p["name"]
                      for p in repo["roster"].get("players", [])}
        y_names = {name_key(p["name"], p.get("nfl_team"), p.get("position")): p["name"] for p in jd["roster"]}
        roster_diff = {
            "on_yahoo_not_repo": sorted(y_names[k] for k in y_names.keys() - repo_names.keys()),
            "on_repo_not_yahoo": sorted(repo_names[k] for k in repo_names.keys() - y_names.keys()),
        }
    in_sync = not (new_tx or review or faab_diffs or waiver_diffs
                   or (roster_diff and (roster_diff["on_yahoo_not_repo"] or roster_diff["on_repo_not_yahoo"])))
    return {
        "league": "sparta",
        "yahoo_league_id": SPARTA_YAHOO_LEAGUE_ID,
        "check_id": snap["check_id"],
        "observed_at": snap["observed_at"],
        "in_sync": in_sync,
        "team_mapping_complete": snap["team_mapping_complete"],
        "unmapped_teams": snap["unmapped_teams"],
        "new_transactions": new_tx,
        "needs_review": review,
        "faab_diffs": faab_diffs,
        "waiver_priority_diffs": waiver_diffs,
        "jd_roster_diff": roster_diff,
        "applied": False,
    }


# ----------------------------------------------------------------- apply

def apply_changes(snap: dict, report: dict, repo: dict) -> dict[str, object]:
    """Return {relative path: new json} for durable files. Caller writes them."""
    if not snap["team_mapping_complete"]:
        raise RuntimeError("refusing --apply: Yahoo teams not fully mapped to repo team codes; "
                           "pin them in data/yahoo_team_map.json")
    writes: dict[str, object] = {}
    obs, check = snap["observed_at"], snap["check_id"]

    if report["new_transactions"]:
        tx = copy.deepcopy(repo["transactions"])
        for rec in report["new_transactions"]:
            tx["transactions"].append({
                **rec,
                "source": f"{SOURCE_LABEL}; check {check}",
                "transaction_fee_usd": 0,
                "total_real_money_cost_usd": rec.get("faab_bid") or 0,
                "check_id": check,
                "live_pull_enriched_at": obs,
            })
        tx["transaction_count"] = len(tx["transactions"])
        tx["source"] = f"Yahoo Sparta league 102586; last ingest {check} ({len(report['new_transactions'])} new txs)"
        writes["data/transactions.json"] = tx

    if report["faab_diffs"]:
        faab = copy.deepcopy(repo["faab"])
        by_code = {t["code"]: t["faab_balance"] for t in snap["teams"]}
        faab["balances"] = [{**b, "balance": by_code.get(b["team"], b["balance"])} for b in faab["balances"]]
        faab["jd_authoritative_balance"] = by_code.get("JD", faab.get("jd_authoritative_balance"))
        faab["source"] = f"{SOURCE_LABEL}; check {check}"
        faab["observed_at"] = obs
        writes["data/faab.json"] = faab

    if report["waiver_priority_diffs"]:
        w = copy.deepcopy(repo["waiver"])
        ordered = sorted((t for t in snap["teams"] if t["waiver_priority"] is not None),
                         key=lambda t: t["waiver_priority"])
        names = {t["code"]: t["team_name"] for t in repo["teams"]}
        w["priority_order"] = [{"priority": t["waiver_priority"], "team": t["code"],
                                "team_name": names.get(t["code"], t["team_name"])} for t in ordered]
        w["source"] = f"{SOURCE_LABEL}; check {check}"
        w["observed_at"] = obs
        writes["data/waiver_state.json"] = w

    rd = report["jd_roster_diff"]
    if rd and (rd["on_yahoo_not_repo"] or rd["on_repo_not_yahoo"]):
        jd = next(t for t in snap["teams"] if t["code"] == "JD")
        roster = copy.deepcopy(repo["roster"])
        players = []
        for p in jd["roster"]:
            abbr = defense_abbr(p["name"], p.get("nfl_team"), p.get("position"))
            players.append({
                "name": NFL_TEAMS[abbr][1] if abbr in NFL_TEAMS else p["name"],
                "slot": p.get("slot"),
                "position": p.get("position"),
                "nfl_team": p.get("nfl_team"),
                "status": p.get("status") or "",
                "yahoo_player_key": p.get("player_key"),
            })
        st = jd.get("standing") or {}
        roster.update({
            "source": f"{SOURCE_LABEL}; check {check}",
            "observed_at": obs,
            "week": snap["current_week"],
            "faab": jd["faab_balance"],
            "ir": f"{sum(1 for p in players if (p['slot'] or '').startswith('IR'))}/1",
            "players": players,
        })
        if st:
            roster["record"] = f"{st.get('wins')}-{st.get('losses')}-{st.get('ties')}"
            roster["standing"] = st.get("rank")
            roster["total_points"] = st.get("points_for")
        writes["data/current_roster_jd.json"] = roster
    return writes


# ------------------------------------------------------------------ main

def load_repo(data: Path = DATA) -> dict:
    return {
        "teams": load_json(data / "teams.json")["teams"],
        "transactions": load_json(data / "transactions.json"),
        "faab": load_json(data / "faab.json"),
        "waiver": load_json(data / "waiver_state.json"),
        "roster": load_json(data / "current_roster_jd.json"),
        "pinned_map": load_json(data / "yahoo_team_map.json", {}).get("team_id_to_code", {}),
    }


def run(client, out_dir: Path | None = None, apply: bool = False,
        observed_at: datetime | None = None, root: Path = ROOT) -> dict:
    out_dir = Path(out_dir) if out_dir else root / "data" / "yahoo_api"
    repo = load_repo(root / "data")
    raw = fetch_all(client)
    snap = build_snapshot(raw, repo, observed_at or now_et(), client.requests_made)
    report = reconcile(snap, repo)
    if apply:
        writes = apply_changes(snap, report, repo)
        for rel, obj in writes.items():
            dump_json(root / rel, obj)
        report["applied"] = True
        report["files_written"] = sorted(writes)
    public = {k: v for k, v in snap.items() if not k.startswith("_")}
    dump_json(out_dir / "latest.json", public)
    dump_json(out_dir / "reconciliation_latest.json", report)
    with open(out_dir / "history.jsonl", "a") as fh:
        fh.write(json.dumps({
            "check_id": snap["check_id"], "observed_at": snap["observed_at"], "week": snap["current_week"],
            "jd_faab": snap["jd"]["faab_balance"], "jd_waiver_priority": snap["jd"]["waiver_priority"],
            "new_transactions": len(report["new_transactions"]), "needs_review": len(report["needs_review"]),
            "in_sync": report["in_sync"], "applied": report["applied"], "api_requests": snap["api_requests"],
        }) + "\n")
    return {"snapshot": public, "report": report,
            "refresh_token_rotated": getattr(client, "refresh_token_rotated", False)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="write Yahoo-confirmed changes to durable data files")
    ap.add_argument("--out-dir", default=None, help="default: data/yahoo_api")
    ap.add_argument("--fixture-dir", help="offline mode: read API responses from fixture XML")
    args = ap.parse_args(argv)

    if args.fixture_dir:
        client = FixtureClient(Path(args.fixture_dir))
    else:
        from yahoo_client import YahooClient
        client = YahooClient.from_env()
    result = run(client, args.out_dir, args.apply or os.environ.get("SPARTA_YAHOO_APPLY") == "true")
    rep, snap = result["report"], result["snapshot"]
    print(f"YAHOO SYNC OK check={snap['check_id']} week={snap['current_week']} requests={snap['api_requests']}")
    print(f"jd_faab={snap['jd']['faab_balance']} jd_waiver_priority={snap['jd']['waiver_priority']} "
          f"teams_mapped={'yes' if snap['team_mapping_complete'] else 'NO ' + str(snap['unmapped_teams'])}")
    print(f"new_transactions={len(rep['new_transactions'])} needs_review={len(rep['needs_review'])} "
          f"faab_diffs={len(rep['faab_diffs'])} waiver_diffs={len(rep['waiver_priority_diffs'])} "
          f"in_sync={rep['in_sync']} applied={rep['applied']}")
    if result["refresh_token_rotated"]:
        print("WARNING: Yahoo issued a new refresh token; update the YAHOO_REFRESH_TOKEN secret.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
