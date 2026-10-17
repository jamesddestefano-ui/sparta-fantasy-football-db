"""Read-only FantasyPros NFL intelligence ingestion for Billy's Sparta league.

Never changes Yahoo, roster, ownership, waivers, FAAB, decision ledgers, or Pulse cursors.
Requires FANTASYPROS_API_KEY from the environment. No automatic scheduling.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://api.fantasypros.com/public/v2/json"
ALLOWED_KINDS = ("consensus", "projections", "injuries")


class IngestionError(Exception):
    """Safe-to-display error that never includes credentials or response bodies."""


def request_spec(kind: str, season: int, week: int) -> tuple[str, dict[str, str], str]:
    if season != 2026 or not 1 <= week <= 18:
        raise ValueError("Sparta pilot is restricted to NFL season 2026, weeks 1–18")
    if kind == "consensus":
        return (f"/nfl/{season}/consensus-rankings",
                {"position": "FLX", "scoring": "PPR", "week": str(week)}, "players")
    if kind == "projections":
        return (f"/nfl/{season}/projections",
                {"positions": "QB:RB:WR:TE:K:DST", "week": str(week)}, "players")
    if kind == "injuries":
        return ("/nfl/injuries", {"year": str(season), "week": str(week),
                                 "include_probabilities": "true"}, "injuries")
    raise ValueError("Unsupported FantasyPros endpoint")


def fetch(kind: str, season: int, week: int, api_key: str, *, opener=urlopen) -> dict:
    if not api_key.strip():
        raise IngestionError("FANTASYPROS_API_KEY is not configured")
    path, params, expected = request_spec(kind, season, week)
    url = BASE + path + "?" + urlencode(params)
    request = Request(url, headers={"x-api-key": api_key, "Accept": "application/json"})
    try:
        with opener(request, timeout=15) as response:
            raw = response.read(5_000_001)
    except HTTPError as exc:
        raise IngestionError(f"FantasyPros {kind}: HTTP {exc.code}; no data accepted") from None
    except (URLError, TimeoutError, OSError):
        raise IngestionError(f"FantasyPros {kind}: network unavailable; no data accepted") from None
    if len(raw) > 5_000_000:
        raise IngestionError(f"FantasyPros {kind}: response too large")
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise IngestionError(f"FantasyPros {kind}: invalid JSON response") from None
    if not isinstance(payload, dict) or not isinstance(payload.get(expected), list):
        raise IngestionError(f"FantasyPros {kind}: missing {expected} array")
    if kind != "injuries":
        if str(payload.get("week")) != str(week):
            raise IngestionError(f"FantasyPros {kind}: returned wrong week")
        if str(payload.get("season", payload.get("year"))) != str(season):
            raise IngestionError(f"FantasyPros {kind}: returned wrong season")
    if str(payload.get("sport", "NFL")).upper() != "NFL":
        raise IngestionError(f"FantasyPros {kind}: returned wrong sport")
    return {
        "system": "SPARTA", "league": "sparta", "season": season, "week": week,
        "provider": "FantasyPros Public API v2", "kind": kind,
        "source_url": url, "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "authority": "NFL_INTELLIGENCE_ONLY_NOT_YAHOO_OWNERSHIP",
        "status": "unvalidated_for_decisions", "record_count": len(payload[expected]),
        "payload": payload,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--week", type=int, required=True)
    parser.add_argument("--kind", choices=ALLOWED_KINDS + ("all",), default="all")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    kinds = ALLOWED_KINDS if args.kind == "all" else (args.kind,)
    key = os.environ.get("FANTASYPROS_API_KEY", "")
    if not key.strip():
        print("FANTASYPROS_API_KEY missing; no requests sent", file=sys.stderr)
        return 2
    try:
        records = [fetch(kind, args.season, args.week, key) for kind in kinds]
    except (IngestionError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for record in records:
        path = args.output_dir / f"fantasypros_nfl_{args.season}_w{args.week:02d}_{record['kind']}.json"
        path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {path.name}: {record['record_count']} records (intelligence only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
