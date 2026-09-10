from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load(name: str):
    return json.loads((DATA / name).read_text())


def main() -> None:
    league = load("league.json")
    teams = load("teams.json")["teams"]
    draft = load("draft_2026.json")
    roster = load("current_roster_jd.json")
    tx = load("transactions.json")
    faab = load("faab.json")
    waiver = load("waiver_state.json")

    errors: list[str] = []

    if league.get("league_id") != "sparta":
        errors.append("league_id must be sparta")
    if league.get("teams") != 12:
        errors.append("league must contain 12 teams")
    if len(teams) != 12 or len({t["code"] for t in teams}) != 12:
        errors.append("teams.json must contain 12 unique team codes")

    draft_teams = draft.get("teams", {})
    if len(draft_teams) != 12:
        errors.append("draft must contain 12 teams")
    if any(len(rows) != 17 for rows in draft_teams.values()):
        errors.append("every draft team must contain 17 players")
    draft_players = [name for rows in draft_teams.values() for name, _ in rows]
    if len(draft_players) != 204:
        errors.append(f"draft has {len(draft_players)} records; expected 204")
    if len(set(draft_players)) != len(draft_players):
        errors.append("duplicate player appears in auction draft")

    if roster.get("team_code") != "JD":
        errors.append("current roster must be JD")
    if len(roster.get("players", [])) != 17:
        errors.append("JD current roster must contain 17 players")
    if len({p["name"] for p in roster.get("players", [])}) != 17:
        errors.append("JD current roster contains duplicates")

    if tx.get("transaction_count") != len(tx.get("transactions", [])):
        errors.append("transaction_count does not match transaction ledger")

    if faab.get("starting_budget") != 100 or not faab.get("real_money"):
        errors.append("Sparta FAAB rules incorrect")
    balances = {r["team"]: r["balance"] for r in faab.get("balances", [])}
    if len(balances) != 12 or balances.get("JD") != 100:
        errors.append("FAAB balance snapshot incomplete or JD balance incorrect")

    priorities = sorted(r["priority"] for r in waiver.get("priority_order", []))
    if priorities != list(range(1, 13)):
        errors.append("waiver priorities must be exactly 1 through 12")

    # Hard league-isolation check: no Mongo league markers in core JSON state.
    for path in DATA.glob("*.json"):
        text = path.read_text().lower()
        if '"league":"mongo"' in text or '"league_id":"mongo"' in text:
            errors.append(f"Mongo league state detected in {path.name}")

    if errors:
        raise SystemExit("SPARTA VALIDATION FAILED:\n- " + "\n- ".join(errors))

    print("SPARTA VALIDATION PASSED")
    print("teams=12 draft_records=204 current_roster=17 transactions=" + str(len(tx["transactions"])))
    print("jd_faab=" + str(balances["JD"]) + " waiver_priority=" + str(next(r["priority"] for r in waiver["priority_order"] if r["team"] == "JD")))


if __name__ == "__main__":
    main()
