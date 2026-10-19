"""Pure parsers for Yahoo Fantasy API v2 XML (namespaces already stripped).

Every function takes an ElementTree element and returns plain dicts/lists, so
they can be unit-tested offline against fixture XML.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo
from xml.etree.ElementTree import Element


class _USEastern(tzinfo):
    """US Eastern time (current DST rules) for systems without a tz database,
    e.g. Windows Python without the tzdata package."""

    @staticmethod
    def _dst_bounds_utc(year: int) -> tuple[datetime, datetime]:
        mar1 = datetime(year, 3, 1)
        second_sun_mar = mar1 + timedelta(days=(6 - mar1.weekday()) % 7 + 7)
        nov1 = datetime(year, 11, 1)
        first_sun_nov = nov1 + timedelta(days=(6 - nov1.weekday()) % 7)
        # 2:00 local -> 07:00 UTC (EST) and 06:00 UTC (EDT)
        return second_sun_mar.replace(hour=7), first_sun_nov.replace(hour=6)

    def utcoffset(self, dt):
        return timedelta(hours=-4) if self.dst(dt) else timedelta(hours=-5)

    def dst(self, dt):
        if dt is None:
            return timedelta(0)
        start, end = self._dst_bounds_utc(dt.year)
        local = dt.replace(tzinfo=None)
        if not (local + timedelta(hours=5) >= start):          # before spring-forward
            return timedelta(0)
        if local + timedelta(hours=4) < end:                    # clearly in DST
            return timedelta(0) if (local + timedelta(hours=5) >= end and dt.fold) else timedelta(hours=1)
        return timedelta(0)

    def fromutc(self, dt):
        start, end = self._dst_bounds_utc(dt.year)
        naive = dt.replace(tzinfo=None)
        in_dst = start <= naive < end
        local = naive + (timedelta(hours=-4) if in_dst else timedelta(hours=-5))
        # second pass through the repeated 1:00-2:00 hour on fall-back day
        fold = int(not in_dst and end <= naive < end + timedelta(hours=1))
        return local.replace(tzinfo=self, fold=fold)

    def tzname(self, dt):
        return "EDT" if self.dst(dt) else "EST"


try:
    from zoneinfo import ZoneInfo
    ET_TZ = ZoneInfo("America/New_York")
except Exception:  # ZoneInfoNotFoundError on Windows without tzdata
    ET_TZ = _USEastern()


def _t(el: Element | None, path: str, default=None):
    if el is None:
        return default
    found = el.find(path)
    if found is None or found.text is None:
        return default
    return found.text.strip()


def _num(value, cast=float):
    if value in (None, "", "-"):
        return None
    try:
        return cast(value)
    except (TypeError, ValueError):
        return None


def unix_to_et(ts) -> str | None:
    n = _num(ts, int)
    if n is None:
        return None
    return datetime.fromtimestamp(n, tz=timezone.utc).astimezone(ET_TZ).isoformat(timespec="seconds")


# ---------------------------------------------------------------- game/league

def parse_game_key(root: Element) -> str:
    key = _t(root, ".//game/game_key")
    if not key:
        raise ValueError("no game_key in response")
    return key


def parse_league_meta(root: Element) -> dict:
    lg = root.find(".//league")
    return {
        "league_key": _t(lg, "league_key"),
        "league_id": _t(lg, "league_id"),
        "name": _t(lg, "name"),
        "num_teams": _num(_t(lg, "num_teams"), int),
        "current_week": _num(_t(lg, "current_week"), int),
        "start_week": _num(_t(lg, "start_week"), int),
        "end_week": _num(_t(lg, "end_week"), int),
        "season": _num(_t(lg, "season"), int),
        "scoring_type": _t(lg, "scoring_type"),
        "is_finished": _t(lg, "is_finished") == "1",
    }


# ---------------------------------------------------------------------- teams

def parse_team(team: Element) -> dict:
    managers = [
        {
            "nickname": _t(m, "nickname"),
            "is_current_login": _t(m, "is_current_login") == "1",
        }
        for m in team.findall("managers/manager")
    ]
    return {
        "team_key": _t(team, "team_key"),
        "team_id": _num(_t(team, "team_id"), int),
        "name": _t(team, "name"),
        "managers": managers,
        "is_owned_by_current_login": _t(team, "is_owned_by_current_login") == "1"
        or any(m["is_current_login"] for m in managers),
        "waiver_priority": _num(_t(team, "waiver_priority"), int),
        "faab_balance": _num(_t(team, "faab_balance"), int),
        "number_of_moves": _num(_t(team, "number_of_moves"), int),
        "number_of_trades": _num(_t(team, "number_of_trades"), int),
    }


def parse_teams(root: Element) -> list[dict]:
    return [parse_team(t) for t in root.iter("team")]


# -------------------------------------------------------------------- players

def parse_player(p: Element) -> dict:
    return {
        "player_key": _t(p, "player_key"),
        "player_id": _num(_t(p, "player_id"), int),
        "name": _t(p, "name/full"),
        "nfl_team": _t(p, "editorial_team_abbr"),
        "position": _t(p, "display_position"),
        "eligible_positions": [e.text for e in p.findall("eligible_positions/position") if e.text],
        "status": _t(p, "status", ""),
        "status_full": _t(p, "status_full"),
        "injury_note": _t(p, "injury_note"),
        "bye_week": _num(_t(p, "bye_weeks/week"), int),
        "slot": _t(p, "selected_position/position"),
        "percent_owned": _num(_t(p, "percent_owned/value")),
        "ownership_type": _t(p, "ownership/ownership_type"),
        "owner_team_key": _t(p, "ownership/owner_team_key"),
        "waiver_date": _t(p, "ownership/waiver_date"),
    }


def parse_rosters(root: Element) -> dict[str, list[dict]]:
    """League teams/roster response -> {team_key: [player, ...]}."""
    out: dict[str, list[dict]] = {}
    for team in root.iter("team"):
        key = _t(team, "team_key")
        out[key] = [parse_player(p) for p in team.findall("roster/players/player")]
    return out


def parse_players(root: Element) -> list[dict]:
    return [parse_player(p) for p in root.iter("player")]


# --------------------------------------------------------------- transactions

def parse_transactions(root: Element) -> list[dict]:
    out = []
    for tx in root.iter("transaction"):
        moves = []
        for p in tx.findall("players/player"):
            d = p.find("transaction_data")
            moves.append({
                "player_key": _t(p, "player_key"),
                "name": _t(p, "name/full"),
                "nfl_team": _t(p, "editorial_team_abbr"),
                "position": _t(p, "display_position"),
                "type": _t(d, "type"),
                "source_type": _t(d, "source_type"),
                "source_team_key": _t(d, "source_team_key"),
                "destination_type": _t(d, "destination_type"),
                "destination_team_key": _t(d, "destination_team_key"),
            })
        out.append({
            "transaction_key": _t(tx, "transaction_key"),
            "transaction_id": _num(_t(tx, "transaction_id"), int),
            "type": _t(tx, "type"),
            "status": _t(tx, "status"),
            "timestamp": _num(_t(tx, "timestamp"), int),
            "timestamp_et": unix_to_et(_t(tx, "timestamp")),
            "faab_bid": _num(_t(tx, "faab_bid"), int),
            "trader_team_key": _t(tx, "trader_team_key"),
            "tradee_team_key": _t(tx, "tradee_team_key"),
            "players": moves,
        })
    return out


# ----------------------------------------------------------- standings/scores

def parse_standings(root: Element) -> list[dict]:
    out = []
    for team in root.iter("team"):
        s = team.find("team_standings")
        out.append({
            "team_key": _t(team, "team_key"),
            "name": _t(team, "name"),
            "rank": _num(_t(s, "rank"), int),
            "wins": _num(_t(s, "outcome_totals/wins"), int),
            "losses": _num(_t(s, "outcome_totals/losses"), int),
            "ties": _num(_t(s, "outcome_totals/ties"), int),
            "points_for": _num(_t(s, "points_for")),
            "points_against": _num(_t(s, "points_against")),
            "streak": (f"{_t(s, 'streak/type', '')[:1].upper()}-{_t(s, 'streak/value', '')}"
                       if s is not None and s.find("streak") is not None else None),
        })
    return out


def parse_scoreboard(root: Element) -> list[dict]:
    out = []
    for m in root.iter("matchup"):
        teams = [{
            "team_key": _t(t, "team_key"),
            "name": _t(t, "name"),
            "points": _num(_t(t, "team_points/total")),
            "projected_points": _num(_t(t, "team_projected_points/total")),
            "win_probability": _num(_t(t, "win_probability")),
        } for t in m.findall("teams/team")]
        out.append({
            "week": _num(_t(m, "week"), int),
            "status": _t(m, "status"),
            "is_playoffs": _t(m, "is_playoffs") == "1",
            "winner_team_key": _t(m, "winner_team_key"),
            "teams": teams,
        })
    return out
