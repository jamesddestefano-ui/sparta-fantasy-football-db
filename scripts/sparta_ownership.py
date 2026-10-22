"""Reconstruct current Sparta ownership for all 12 teams from repository evidence.

Order of application (later wins):
  1. Aug 30 auction (data/draft_2026.json)
  2. ownership overrides / user corrections (data/ownership_overrides.json)
  3. immutable transaction ledger, chronological (data/transactions.json)
  4. JD's current authoritative roster snapshot (data/current_roster_jd.json)

This yields OWNED (team known) evidence only. Per AGENTS.md rule 3, a player
missing from every reconstructed roster is NOT confirmed available: callers
must label such players `UNKNOWN_NOT_ON_RECONSTRUCTED_ROSTERS` unless explicit
Sparta evidence (override availability, Yahoo free-agent data) says otherwise.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sparta_names import name_key  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _load(data: Path, name: str, default=None):
    p = data / name
    return json.loads(p.read_text()) if p.exists() else default


def _split(names: str | None) -> list[str]:
    return [n.strip() for n in (names or "").split(";") if n.strip()]


def reconstruct(data: Path = ROOT / "data") -> dict:
    draft = _load(data, "draft_2026.json")
    overrides = _load(data, "ownership_overrides.json", {"records": []})
    txs = _load(data, "transactions.json")["transactions"]
    jd = _load(data, "current_roster_jd.json")

    owner: dict[str, str] = {}       # name_key -> team code
    display: dict[str, str] = {}     # name_key -> latest display name
    availability: dict[str, dict] = {}
    conflicts: list[str] = []

    def put(name: str, team: str, why: str):
        k = name_key(name)
        if not k:
            return
        display[k] = name
        owner[k] = team
        availability.pop(k, None)

    def drop(name: str, team: str, why: str):
        k = name_key(name)
        if not k:
            return
        display.setdefault(k, name)
        if owner.get(k) == team:
            del owner[k]
        elif k in owner and not str(why).startswith("trade"):
            conflicts.append(f"{why}: {team} dropped {name} but reconstruction had {owner[k]}")

    for team, rows in draft["teams"].items():
        for name, _price in rows:
            put(name, team, "draft")

    for rec in overrides.get("records", []):
        if rec.get("historical_only"):
            continue
        if rec.get("team"):
            put(rec["player"], rec["team"], "override")
        elif rec.get("availability"):
            k = name_key(rec["player"])
            owner.pop(k, None)
            display[k] = rec["player"]
            availability[k] = {"status": rec["availability"], "source": rec.get("source")}

    for tx in sorted(txs, key=lambda t: t.get("timestamp_et") or ""):
        team, action = tx.get("team"), tx.get("action")
        if action in ("ADD", "ADD_DROP"):
            for n in _split(tx.get("dropped")):
                drop(n, team, tx.get("timestamp_et"))
            for n in _split(tx.get("added")):
                put(n, team, tx.get("timestamp_et"))
        elif action == "DROP":
            for n in _split(tx.get("dropped")):
                drop(n, team, tx.get("timestamp_et"))
        elif action == "TRADE":
            for n in _split(tx.get("dropped")):
                drop(n, team, "trade " + str(tx.get("timestamp_et")))
            for n in _split(tx.get("added")):
                put(n, team, "trade " + str(tx.get("timestamp_et")))

    # Observed full rosters of other teams (Yahoo screenshots), newer than the ledger.
    snaps = _load(data, "team_roster_snapshots.json", {"snapshots": []})
    for snap in snaps.get("snapshots", []):
        steam, seen_at = snap["team"], snap.get("observed_at") or ""
        later = any(t.get("team") == steam and str(t.get("timestamp_et") or "") > seen_at[:16].replace("T", " ")
                    for t in txs)
        if later:
            continue  # a newer ledger move for this team wins; refresh the snapshot
        keys = set()
        for name in snap.get("players", []):
            k = name_key(name)
            keys.add(k)
            display[k] = name
            owner[k] = steam
            availability.pop(k, None)
        for k, team in list(owner.items()):
            if team == steam and k not in keys:
                del owner[k]

    # JD's snapshot is newer and authoritative for JD.
    jd_keys = set()
    for p in jd.get("players", []):
        k = name_key(p["name"], p.get("nfl_team"), p.get("position"))
        jd_keys.add(k)
        display[k] = p["name"]
        if owner.get(k) not in (None, "JD"):
            conflicts.append(f"JD snapshot has {p['name']} but reconstruction had {owner[k]}")
        owner[k] = "JD"
        availability.pop(k, None)
    for k, team in list(owner.items()):
        if team == "JD" and k not in jd_keys:
            del owner[k]

    rosters: dict[str, list[str]] = {}
    for k, team in owner.items():
        rosters.setdefault(team, []).append(display[k])
    over_limit = {t: len(v) for t, v in rosters.items() if len(v) > 18}
    return {
        "over_limit_teams": over_limit,
        "owner_by_key": owner,
        "display_by_key": display,
        "rosters": {t: sorted(v) for t, v in sorted(rosters.items())},
        "availability_evidence": availability,
        "conflicts": conflicts,
        "jd_snapshot_observed_at": jd.get("observed_at"),
    }


def ownership_status(recon: dict, name: str, nfl_team: str | None = None, position: str | None = None) -> dict:
    k = name_key(name, nfl_team, position)
    if k in recon["owner_by_key"]:
        return {"status": "OWNED", "team": recon["owner_by_key"][k]}
    if k in recon["availability_evidence"]:
        ev = recon["availability_evidence"][k]
        return {"status": ev["status"], "team": None, "source": ev.get("source")}
    return {"status": "UNKNOWN_NOT_ON_RECONSTRUCTED_ROSTERS", "team": None}


if __name__ == "__main__":
    r = reconstruct()
    for team, players in r["rosters"].items():
        print(f"{team} ({len(players)}): {', '.join(players)}")
    print(f"\nteams over 18 (missing drops in ledger): {r['over_limit_teams']}")
    print(f"conflicts: {len(r['conflicts'])}")
    for c in r["conflicts"][:40]:
        print("  " + c)
