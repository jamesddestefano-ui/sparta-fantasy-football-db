"""Read-only FantasyPros NFL intelligence ingestion for Billy's Sparta league.

Never changes Yahoo, roster, ownership, waivers, FAAB, decision ledgers, or Pulse cursors.
Requires FANTASYPROS_API_KEY from the environment. No automatic scheduling.
"""
from __future__ import annotations

import argparse
import hashlib
import tempfile
import time
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler

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


class NoRedirect(HTTPRedirectHandler):
    """Do not forward the API key to a redirect target."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def safe_open(request, timeout):
    return build_opener(NoRedirect()).open(request, timeout=timeout)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def validate_payload(payload, kind, season, week, *, now=None):
    """Conservative local safety checks; not an OpenAPI contract validator."""
    expected = "injuries" if kind == "injuries" else "players"
    if not isinstance(payload, dict) or not isinstance(payload.get(expected), list):
        raise IngestionError(f"FantasyPros {kind}: missing {expected} array")
    if str(payload.get("sport", "NFL")).upper() != "NFL":
        raise IngestionError(f"FantasyPros {kind}: returned wrong sport")
    # Global injury reports cannot be asserted to describe a historical week.
    for field, wanted in (("season", season), ("year", season), ("week", week)):
        if field in payload and str(payload[field]) != str(wanted):
            raise IngestionError(f"FantasyPros {kind}: returned wrong {field}")
    if kind != "injuries":
        if str(payload.get("week")) != str(week):
            raise IngestionError(f"FantasyPros {kind}: returned wrong week")
        if str(payload.get("season", payload.get("year"))) != str(season):
            raise IngestionError(f"FantasyPros {kind}: returned wrong season")
    if kind == "consensus" and payload.get("scoring") != "PPR":
        raise IngestionError("FantasyPros consensus: PPR scoring not confirmed")
    if not payload[expected]:
        raise IngestionError(f"FantasyPros {kind}: empty result; no data accepted")
    flags = ["OPENAPI_CONTRACT_UNVERIFIED"]
    if kind == "projections" and payload.get("scoring") != "PPR":
        flags.append("PPR_PROJECTION_POINTS_UNVERIFIED")
    if kind == "injuries":
        flags.append("INJURY_WEEK_SCOPE_UNVERIFIED")
    now = now or datetime.now(timezone.utc)
    stamps = []
    def timestamp(value):
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if dt.tzinfo is None: raise ValueError()
        except (ValueError, TypeError):
            raise IngestionError("FantasyPros: malformed provider timestamp") from None
        age = (now - dt).total_seconds()
        if age < -300 or age > 172800:
            raise IngestionError("FantasyPros: stale or future provider timestamp")
        stamps.append(value)
    for field in ("updated_at", "updated_at_utc", "last_updated", "timestamp"):
        if payload.get(field) is not None: timestamp(payload[field])
    unique = {}; yahoo = {}
    for row in payload[expected]:
        if not isinstance(row, dict):
            raise IngestionError("FantasyPros: malformed player record")
        player_id = row.get("player_id")
        name = row.get("player_name")
        pos = row.get("player_position", row.get("position"))
        if (isinstance(player_id, bool) or not isinstance(player_id, (str, int))
                or not str(player_id).strip() or not isinstance(name, str) or not name.strip()
                or pos not in {"QB", "RB", "WR", "TE", "K", "DST", "DST/DEF", "DEF"}):
            raise IngestionError("FantasyPros: invalid player identity or position")
        for field, wanted in (("season", season), ("year", season), ("week", week), ("scoring", "PPR")):
            if field in row and str(row[field]) != str(wanted):
                raise IngestionError("FantasyPros: contradictory record context")
        for field in ("updated_at", "updated_at_utc", "last_updated", "timestamp"):
            if row.get(field) is not None: timestamp(row[field])
        ident = str(player_id)
        if ident in unique and canonical(unique[ident]) != canonical(row):
            raise IngestionError("FantasyPros: contradictory duplicate player identity")
        yahoo_id = row.get("yahoo_id", row.get("player_yahoo_id"))
        if yahoo_id is not None:
            if isinstance(yahoo_id, bool) or not str(yahoo_id).isdigit():
                raise IngestionError("FantasyPros: invalid Yahoo identifier")
            if str(yahoo_id) in yahoo and yahoo[str(yahoo_id)] != ident:
                raise IngestionError("FantasyPros: conflicting Yahoo identifiers")
            yahoo[str(yahoo_id)] = ident
        unique[ident] = row
    if not stamps: flags.append("PROVIDER_TIMESTAMP_MISSING")
    if not yahoo: flags.append("YAHOO_ID_MAPPING_MISSING")
    clean = dict(payload, **{expected: list(unique.values())})
    return clean, flags, yahoo, stamps


def publish_batch(records, output_dir):
    """Publish one complete immutable batch; repeated observations share one file."""
    root = Path(__file__).resolve().parents[1]
    output_dir = Path(output_dir).resolve()
    allowed = root / "intelligence" / "fantasypros"
    if output_dir == root or (root in output_dir.parents and output_dir != allowed and allowed not in output_dir.parents):
        raise IngestionError("Output must be external or under intelligence/fantasypros")
    if not records or any(r.get("system") != "SPARTA" or r.get("status") != "unvalidated_for_decisions" for r in records):
        raise IngestionError("Invalid or partial batch")
    # Retrieval times differ on a repeat; provider content determines identity.
    identity = [{k: r[k] for k in ("kind", "season", "week", "payload")} for r in records]
    digest = hashlib.sha256(canonical(identity).encode()).hexdigest()
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"fantasypros_batch_{digest}.json"
    body = canonical({"batch_id":digest, "records":records}) + "\n"
    # Hard-link publication is atomic, no-clobber, including concurrent writers.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output_dir, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(body); handle.flush(); os.fsync(handle.fileno())
        try: os.link(temporary, path)
        except FileExistsError:
            prior = json.loads(path.read_text(encoding="utf-8"))
            prior_identity = [{k:r[k] for k in ("kind","season","week","payload")} for r in prior["records"]]
            if canonical(prior_identity) != canonical(identity):
                raise IngestionError("Existing batch identity mismatch")
    except (OSError, ValueError, KeyError, TypeError):
        raise IngestionError("Unable to publish intelligence batch safely") from None
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)
    return path


def fetch(kind: str, season: int, week: int, api_key: str, *, opener=safe_open, retries=0, sleep=time.sleep) -> dict:
    if not api_key.strip():
        raise IngestionError("FANTASYPROS_API_KEY is not configured")
    path, params, expected = request_spec(kind, season, week)
    url = BASE + path + "?" + urlencode(params)
    request = Request(url, headers={"x-api-key": api_key, "Accept": "application/json"})
    if type(retries) is not int or not 0 <= retries <= 2:
        raise ValueError("Retries must be between 0 and 2")
    for attempt in range(retries + 1):
        try:
            with opener(request, timeout=15) as response:
                raw = response.read(5_000_001)
            break
        except HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries:
                retry_after = exc.headers.get("Retry-After", "") if exc.headers else ""
                delay = int(retry_after) if retry_after.isdigit() else 2 ** attempt
                if delay > 30:
                    raise IngestionError("FantasyPros: rate limit requires deferred retry") from None
                sleep(max(1, delay)); continue
            raise IngestionError(f"FantasyPros {kind}: HTTP {exc.code}; no data accepted") from None
        except (URLError, TimeoutError, OSError, ValueError):
            if attempt < retries:
                sleep(2 ** attempt); continue
            raise IngestionError(f"FantasyPros {kind}: network unavailable; no data accepted") from None
    if len(raw) > 5_000_000:
        raise IngestionError(f"FantasyPros {kind}: response too large")
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise IngestionError(f"FantasyPros {kind}: invalid JSON response") from None
    try:
        if api_key in canonical(payload):
            raise IngestionError("FantasyPros: credential echoed in response; rejected")
        payload, flags, yahoo, stamps = validate_payload(payload, kind, season, week)
    except (ValueError, TypeError, RecursionError):
        raise IngestionError("FantasyPros: malformed response values") from None
    return {
        "system": "SPARTA", "league": "sparta", "season": season, "week": week,
        "provider": "FantasyPros Public API v2", "kind": kind,
        "source_url": url, "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "authority": "NFL_INTELLIGENCE_ONLY_NOT_YAHOO_OWNERSHIP",
        "contract_status": "UNVERIFIED_OPENAPI_NOT_SUPPLIED",
        "quality_flags": flags, "provider_timestamps": stamps,
        "yahoo_id_mapping": yahoo, "availability": "UNKNOWN",
        "scoring": "PPR" if kind == "consensus" else "UNVERIFIED",
        "attempt_count": attempt + 1,
        "status": "unvalidated_for_decisions", "record_count": len(payload[expected]),
        "payload": payload,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--week", type=int, required=True)
    parser.add_argument("--kind", choices=ALLOWED_KINDS + ("all",), default="all")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--retries", type=int, choices=range(3), default=0)
    args = parser.parse_args(argv)
    kinds = ALLOWED_KINDS if args.kind == "all" else (args.kind,)
    key = os.environ.get("FANTASYPROS_API_KEY", "")
    if not key.strip():
        print("FANTASYPROS_API_KEY missing; no requests sent", file=sys.stderr)
        return 2
    try:
        records = [fetch(kind, args.season, args.week, key, retries=args.retries) for kind in kinds]
    except (IngestionError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    try:
        path = publish_batch(records, args.output_dir)
    except IngestionError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Published {path.name} (unvalidated intelligence only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
