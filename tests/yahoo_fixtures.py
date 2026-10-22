"""Synthetic Yahoo Fantasy API v2 XML fixtures for offline Sparta sync tests.

Shapes follow Yahoo's documented XML resources (namespaced fantasy_content
root). Values are synthetic except team names/managers, which mirror
data/teams.json so team mapping is exercised realistically.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from yahoo_parse import ET_TZ  # noqa: E402

NS = 'xmlns="http://fantasysports.yahooapis.com/fantasy/v2/base.rng"'
LK = "461.l.102586"
ET = ET_TZ

TEAMS = [  # team_id, name, manager nickname, faab, waiver priority
    (1, "SHOWSTOPPERS", "the_showstoppers", 100, 12),
    (2, "CLIN-TON POR-TIS", "Michael Capone", 100, 11),
    (3, "FOCUS", "Vinny", 97, 10),
    (4, "Renamed Ladd Team", "tony", 100, 9),  # renamed on Yahoo: must map by manager
    (5, "King Kong", "SteveR", 100, 8),
    (6, "MattyBAD", "Phenom", 100, 7),
    (7, "AMON A ROLL", "anthony mangarelli", 100, 6),
    (8, "Pablo Pledgescobars", "Matt M", 100, 5),
    (9, "Brown Rice & Kraft", "Mike", 100, 4),
    (10, "Yahoo Display Name For JD", "James", 28, 1),  # pinned team_id 10 -> JD
    (11, "The U", "Joseph", 100, 2),
    (12, "X-Factor", "letspartyitup.com", 100, 3),
]

# JD's Yahoo roster: the frozen 2026-10-19 JD roster (tests/fixtures/sparta_data_20261019)
# with Dylan Sampson dropped for Kyle Monangai (the new waiver claim in the fixture
# transactions). Reads the same frozen copy the sync tests use, so live roster moves
# (e.g. the Week 7 waivers and Bijan trade) can't break CI.
def _jd_roster():
    import json as _json
    repo = _json.loads((Path(__file__).resolve().parent / "fixtures" / "sparta_data_20261019" / "current_roster_jd.json").read_text())
    rows = []
    for p in repo["players"]:
        if p["name"] == "Dylan Sampson":
            continue
        name, pos = p["name"], p.get("position") or "WR"
        if pos == "DEF":
            name = "Baltimore" if name == "Ravens" else name
        slot = "IR" if (p.get("slot") or "").startswith("IR") else p.get("slot")
        rows.append((name, p.get("nfl_team") or "FA", pos, slot))
    rows.append(("Kyle Monangai", "Chi", "RB", "BN"))
    return rows


JD_ROSTER = _jd_roster()


def ts(local: str) -> int:
    return int(datetime.strptime(local, "%Y-%m-%d %H:%M").replace(tzinfo=ET).timestamp())


def wrap(inner: str) -> str:
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<fantasy_content {NS}>{inner}</fantasy_content>'


def player(pid, name, team, pos, slot=None, own=None, pct=None):
    sel = f"<selected_position><position>{slot}</position></selected_position>" if slot else ""
    o = (f"<ownership><ownership_type>{own}</ownership_type></ownership>" if own else "")
    p = f"<percent_owned><value>{pct}</value></percent_owned>" if pct is not None else ""
    return (f"<player><player_key>461.p.{pid}</player_key><player_id>{pid}</player_id>"
            f"<name><full>{escape(name)}</full></name><editorial_team_abbr>{team}</editorial_team_abbr>"
            f"<display_position>{pos}</display_position><eligible_positions><position>{pos}</position>"
            f"</eligible_positions>{sel}{o}{p}</player>")


def team_xml(tid, name, mgr, faab, prio, extra=""):
    login = "1" if tid == 10 else "0"
    return (f"<team><team_key>{LK}.t.{tid}</team_key><team_id>{tid}</team_id><name>{escape(name)}</name>"
            f"<is_owned_by_current_login>{login}</is_owned_by_current_login>"
            f"<waiver_priority>{prio}</waiver_priority><faab_balance>{faab}</faab_balance>"
            f"<number_of_moves>3</number_of_moves><number_of_trades>0</number_of_trades>"
            f"<managers><manager><nickname>{escape(mgr)}</nickname><is_current_login>{login}</is_current_login>"
            f"</manager></managers>{extra}</team>")


def tx(key, ttype, when, players, faab=None, status="successful", extra=""):
    f = f"<faab_bid>{faab}</faab_bid>" if faab is not None else ""
    return (f"<transaction><transaction_key>{key}</transaction_key><transaction_id>{key.split('.')[-1]}"
            f"</transaction_id><type>{ttype}</type><status>{status}</status><timestamp>{ts(when)}</timestamp>"
            f"{f}{extra}<players count=\"{len(players)}\">{''.join(players)}</players></transaction>")


def move(pid, name, team, pos, mtype, src, dest_team=None, src_team=None):
    d = f"<destination_team_key>{LK}.t.{dest_team}</destination_team_key>" if dest_team else ""
    s = f"<source_team_key>{LK}.t.{src_team}</source_team_key>" if src_team else ""
    dest_type = "team" if mtype == "add" else "waivers"
    return (f"<player><player_key>461.p.{pid}</player_key><name><full>{name}</full></name>"
            f"<editorial_team_abbr>{team}</editorial_team_abbr><display_position>{pos}</display_position>"
            f"<transaction_data><type>{mtype}</type><source_type>{src}</source_type>{s}"
            f"<destination_type>{dest_type}</destination_type>{d}</transaction_data></player>")


def write_fixtures(target: Path) -> Path:
    target.mkdir(parents=True, exist_ok=True)
    files = {}
    files["game.xml"] = wrap("<game><game_key>461</game_key><code>nfl</code><season>2026</season></game>")
    files["league.xml"] = wrap(
        f"<league><league_key>{LK}</league_key><league_id>102586</league_id>"
        "<name>Sparta</name><num_teams>12</num_teams><current_week>7</current_week>"
        "<start_week>1</start_week><end_week>17</end_week><season>2026</season>"
        "<scoring_type>head</scoring_type><is_finished>0</is_finished></league>")
    files["teams.xml"] = wrap(f"<league><league_key>{LK}</league_key><teams count=\"12\">"
                              + "".join(team_xml(*t) for t in TEAMS) + "</teams></league>")
    rosters = []
    pid = 1000
    for t in TEAMS:
        if t[0] == 10:
            ps = "".join(player(9000 + i, n, tm, pos, slot) for i, (n, tm, pos, slot) in enumerate(JD_ROSTER))
        else:
            ps = "".join(player(pid + i, f"Other Player {t[0]}-{i}", "KC", "WR", "BN") for i in range(3))
            pid += 10
        rosters.append(team_xml(*t, extra=f"<roster><players>{ps}</players></roster>"))
    files["teams_roster.xml"] = wrap(f"<league><teams count=\"12\">{''.join(rosters)}</teams></league>")
    stand = "".join(
        f"<team><team_key>{LK}.t.{t[0]}</team_key><name>{escape(t[1])}</name><team_standings>"
        f"<rank>{12 if t[0] == 10 else t[0]}</rank><outcome_totals><wins>{1 if t[0] == 10 else 3}</wins>"
        f"<losses>{5 if t[0] == 10 else 3}</losses><ties>0</ties></outcome_totals>"
        f"<streak><type>loss</type><value>3</value></streak>"
        f"<points_for>790.5</points_for><points_against>901.2</points_against></team_standings></team>"
        for t in TEAMS)
    files["standings.xml"] = wrap(f"<league><standings><teams>{stand}</teams></standings></league>")
    files["scoreboard.xml"] = wrap(
        "<league><scoreboard><week>7</week><matchups><matchup><week>7</week><status>preevent</status>"
        "<is_playoffs>0</is_playoffs><teams>"
        f"<team><team_key>{LK}.t.10</team_key><name>JD</name><win_probability>0.44</win_probability>"
        "<team_points><total>0.00</total></team_points><team_projected_points><total>121.4</total>"
        "</team_projected_points></team>"
        f"<team><team_key>{LK}.t.6</team_key><name>MattyBAD</name><win_probability>0.56</win_probability>"
        "<team_points><total>0.00</total></team_points><team_projected_points><total>128.9</total>"
        "</team_projected_points></team></teams></matchup></matchups></scoreboard></league>")
    txs = [
        # Already recorded in data/transactions.json (Oct 15, 19:02 ET) -> must not be new.
        tx(f"{LK}.tr.900", "add/drop", "2026-10-15 19:02", [
            move(9007, "Jacob Cowing", "SF", "WR", "add", "freeagents", dest_team=10),
            move(5555, "Audric Estime", "Cle", "RB", "drop", "team", src_team=10)]),
        # New JD waiver claim.
        tx(f"{LK}.tr.910", "add/drop", "2026-10-21 03:10", [
            move(9016, "Kyle Monangai", "Chi", "RB", "add", "waivers", dest_team=10),
            move(5556, "Dylan Sampson", "Cle", "RB", "drop", "team", src_team=10)], faab=5),
        # New defense add by Vinny, Yahoo city naming.
        tx(f"{LK}.tr.911", "add", "2026-10-21 03:10", [
            move(100030, "Denver", "Den", "DEF", "add", "waivers", dest_team=3)], faab=3),
        # Failed claim -> ignored.
        tx(f"{LK}.tr.912", "add", "2026-10-21 03:10", [
            move(7777, "Somebody Else", "Mia", "WR", "add", "waivers", dest_team=5)], faab=1, status="failed"),
        # Trade -> review only.
        tx(f"{LK}.tr.913", "trade", "2026-10-20 12:00", [
            move(8001, "Trade Guy A", "Det", "RB", "trade", "team", dest_team=1, src_team=2),
            move(8002, "Trade Guy B", "Det", "WR", "trade", "team", dest_team=2, src_team=1)],
           extra=f"<trader_team_key>{LK}.t.1</trader_team_key><tradee_team_key>{LK}.t.2</tradee_team_key>"),
    ]
    files["transactions_0.xml"] = wrap(f"<league><transactions count=\"{len(txs)}\">{''.join(txs)}</transactions></league>")
    files["players_RB_0.xml"] = wrap(
        "<league><players count=\"3\">"
        + player(9016, "Kyle Monangai", "Chi", "RB", own="team", pct=40)  # owned by JD: must be filtered
        + player(6001, "Waiver Back", "Atl", "RB", own="waivers", pct=22)
        + player(6002, "Free Back", "Ten", "RB", own="freeagents", pct=9)
        + "</players></league>")
    files["players_WR_0.xml"] = wrap(
        "<league><players count=\"1\">" + player(6101, "Free Wideout", "Hou", "WR", own="freeagents", pct=15)
        + "</players></league>")
    for name, body in files.items():
        (target / name).write_text(body)
    return target
