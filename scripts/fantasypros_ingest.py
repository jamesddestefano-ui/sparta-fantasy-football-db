"""Read-only FantasyPros NFL intelligence ingestion for Billy's Sparta league.

Never changes Yahoo, roster, ownership, waivers, FAAB, decision ledgers, or Pulse cursors.
Requires FANTASYPROS_API_KEY from the environment. No automatic scheduling.
"""
from __future__ import annotations

import argparse
import hashlib
import math
from fantasypros_contract import ARRAYS, validate_request, validate_response, document
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
PILOT_KINDS = ("consensus", "projections", "injuries")
ALLOWED_KINDS = PILOT_KINDS + ("news", "compare", "points", "experts", "projections_ros")



class IngestionError(Exception):
    """Safe-to-display error that never includes credentials or response bodies."""


def request_spec(kind: str, season: int, week: int, *, player_ids=None) -> tuple[str, dict[str, str], str]:
    if type(season) is not int or type(week) is not int or season != 2026 or not 1 <= week <= 18:
        raise ValueError("Sparta pilot is restricted to NFL season 2026, weeks 1–18")
    contract_kind = "projections" if kind == "projections_ros" else kind
    if kind == "consensus":
        params = {"position":"FLX", "scoring":"PPR", "week":str(week), "type":"WW"}
    elif kind in ("projections", "projections_ros"):
        params = {"position":"WR", "positions":"WR", "week":str(week)}
        if kind == "projections_ros": params["ros"]="true"
    elif kind == "injuries":
        params = {"year":str(season),"week":str(week),"include_probabilities":"true"}
    elif kind == "news": params = {"limit":"10","order_by":"updated"}
    elif kind == "compare":
        if not isinstance(player_ids,str) or len(player_ids.split(":")) != 2 or not all(p.isdigit() and int(p)>0 for p in player_ids.split(":")) or len(set(player_ids.split(":"))) != 2:
            raise ValueError("Comparison requires two distinct verified FantasyPros IDs")
        params = {"year":str(season),"week":str(week),"players":player_ids,"position":"WR","ranking_type":"weekly","details":"players"}
    elif kind == "points": params = {"start":str(week),"end":str(week),"position":"WR","scoring":"PPR","min":"false"}
    elif kind == "experts": params = {"position":"WR","type":"WW","scoring":"PPR","include_overall":"true"}
    else: raise ValueError("Unsupported FantasyPros endpoint")
    path=validate_request(contract_kind,season,params)
    return path,params,ARRAYS[contract_kind]


class NoRedirect(HTTPRedirectHandler):
    """Do not forward the API key to a redirect target."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def safe_open(request, timeout):
    return build_opener(NoRedirect()).open(request, timeout=timeout)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def validate_payload(payload, kind, season, week, *, now=None, player_ids=None):
    """Validate supplied NFL schema, request scope, identities and PPR semantics."""
    contract_kind="projections" if kind=="projections_ros" else kind
    try: validate_response(contract_kind,payload)
    except ValueError:
        raise IngestionError("FantasyPros: response violates supplied OpenAPI schema") from None
    expected=ARRAYS[contract_kind]
    if payload.get("sport","NFL") != "NFL": raise IngestionError("FantasyPros: returned wrong sport")
    for field,wanted in (("season",season),("year",season),("week",week)):
        if field in payload and str(payload[field])!=str(wanted):
            raise IngestionError(f"FantasyPros {kind}: returned wrong {field}")
    if kind in ("consensus","points") and payload.get("scoring")!="PPR":
        raise IngestionError("FantasyPros: PPR scoring not confirmed")
    if kind=="consensus" and (payload['ranking_type_name']!='WW' or payload['position_id']!='FLX'):
        raise IngestionError("FantasyPros: ranking slice mismatch")
    if kind=="compare" and (payload['ranking_type']!='weekly' or payload['position_id']!='WR'):
        raise IngestionError("FantasyPros: comparison slice mismatch")
    if kind in ("projections","projections_ros") and payload['positions']!='WR':
        raise IngestionError("FantasyPros: projection position slice mismatch")
    if not payload[expected]: raise IngestionError("FantasyPros: empty result; no data accepted")
    flags=[]; stamps=[]; yahoo={}; normalized=[]; unique={}
    if kind in ("news","injuries"): flags.append("PROVIDER_SEASON_WEEK_NOT_IN_SCHEMA_REQUEST_SCOPE_ONLY")
    now=now or datetime.now(timezone.utc)
    def check_time(dt):
        age=(now-dt).total_seconds()
        if age < -300 or age > 172800: raise IngestionError("FantasyPros: stale or future provider timestamp")
    if kind=='consensus':
        try: check_time(datetime.fromtimestamp(payload['last_updated_ts'],timezone.utc))
        except (OverflowError,OSError,ValueError): raise IngestionError("FantasyPros: malformed provider timestamp") from None
        stamps.extend([{'field':'last_updated_ts','value':payload['last_updated_ts']},{'field':'last_updated','value':payload['last_updated']}])
    # Preserve explicit ISO fields when supplied in addition to documented fields.
    for field in ('updated_at','updated_at_utc','timestamp'):
        if payload.get(field) is not None:
            try:
                dt=datetime.fromisoformat(str(payload[field]).replace('Z','+00:00'))
                if dt.tzinfo is None: raise ValueError()
                check_time(dt)
            except (ValueError,TypeError): raise IngestionError("FantasyPros: malformed provider timestamp") from None
            stamps.append({'field':field,'value':payload[field]})
    for field in ('expert_pub',):
        if payload.get(field):
            stamps.append({'field':field,'value':payload[field]})
            flags.append('EXPERT_TIMESTAMP_TIMEZONE_REQUIRES_REVIEW')
    if kind=='compare':
        ranks=payload['rankings'].get('PPR')
        if not isinstance(ranks,dict) or not isinstance(payload.get('players'),dict):
            raise IngestionError('FantasyPros: PPR comparison or player details missing')
        if player_ids is not None and set(ranks)!=set(player_ids.split(':')):
            raise IngestionError('FantasyPros: comparison returned different identities')
        rows=[dict(payload['players'].get(ident,{}),player_id=int(ident)) for ident in ranks if str(ident).isdigit()]
        if len(rows)!=len(ranks): raise IngestionError('FantasyPros: malformed comparison identities')
    else: rows=payload[expected]
    for row in rows:
        ident=row.get('fpid') if contract_kind=='projections' else row.get('expert_id') if kind=='experts' else row.get('player_id')
        if isinstance(ident,bool) or not str(ident).isdigit() or int(ident)<=0:
            raise IngestionError('FantasyPros: invalid player or expert identity')
        ident=str(ident)
        name=row.get('player_name',row.get('name'))
        pos=row.get('player_position_id',row.get('position_id',row.get('player_position')))
        if name is not None and (not isinstance(name,str) or not name.strip()): raise IngestionError('FantasyPros: invalid player name')
        if pos is not None and pos not in document()[0]['components']['schemas']['NFLPositions']['enum']:
            raise IngestionError('FantasyPros: invalid player position')
        if not name and kind!='experts': flags.append('PLAYER_NAME_MISSING')
        if not pos and kind!='experts': flags.append('PLAYER_POSITION_MISSING')
        for field,wanted in (("season",season),("year",season),("week",week),("scoring","PPR")):
            if field in row and str(row[field])!=str(wanted): raise IngestionError('FantasyPros: contradictory record context')
        if kind=='news' and row['sport_id']!='NFL': raise IngestionError('FantasyPros: news sport mismatch')
        key=str(row['id']) if kind=='news' else ident
        if key in unique:
            if canonical(unique[key])!=canonical(row): raise IngestionError('FantasyPros: contradictory duplicate identity')
            continue
        unique[key]=row
        yid=row.get('player_yahoo_id',row.get('yahoo_id'))
        if yid:
            if not str(yid).isdigit() or int(yid)<=0 or (str(yid) in yahoo and yahoo[str(yid)]!=ident):
                raise IngestionError('FantasyPros: conflicting Yahoo identifier')
            yahoo[str(yid)]=ident
        item={'fantasypros_id':ident,'name':name,'position':pos,'yahoo_id':str(yid) if yid else None}
        if contract_kind=='projections':
            values={stat['points_ppr'] for stat in row['stats']}
            if len(values)!=1: raise IngestionError('FantasyPros: ambiguous projection rows')
            value=next(iter(values))
            if not math.isfinite(value) or abs(value)>10000: raise IngestionError('FantasyPros: invalid projection points')
            item['projected_points_ppr']=value
        if kind=='consensus':
            try: rank=float(row['rank_ecr'])
            except (ValueError,TypeError): raise IngestionError('FantasyPros: malformed PPR rank') from None
            if not math.isfinite(rank) or rank<1: raise IngestionError('FantasyPros: invalid PPR rank')
            item['rank_ppr']=rank
        if kind=='points':
            if set(row['weeks'])!={str(week)}: raise IngestionError('FantasyPros: actual scoring week missing or ambiguous')
            item['actual_points_ppr']=row['weeks'][str(week)]
        for field in ('injury_update_date','created'):
            if row.get(field): stamps.append({'field':field,'value':row[field],'player_id':ident})
        normalized.append(item)
    if not stamps: flags.append('PROVIDER_TIMESTAMP_MISSING')
    if not yahoo: flags.append('YAHOO_ID_MAPPING_MISSING')
    clean=dict(payload)
    if kind!='compare': clean[expected]=list(unique.values())
    return clean,sorted(set(flags)),yahoo,stamps,normalized


def validate_output_dir(output_dir):
    """Reject writes into league state before consuming any API credits."""
    root = Path(__file__).resolve().parents[1]
    output_dir = Path(output_dir).resolve()
    allowed = root / "intelligence" / "fantasypros"
    if output_dir == root or (root in output_dir.parents and output_dir != allowed and allowed not in output_dir.parents):
        raise IngestionError("Output must be external or under intelligence/fantasypros")
    return output_dir


def publish_batch(records, output_dir):
    """Publish one complete immutable batch; repeated observations share one file."""
    output_dir = validate_output_dir(output_dir)
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


def contains_secret(value, secret):
    if isinstance(value, str): return secret in value
    if isinstance(value, list): return any(contains_secret(v, secret) for v in value)
    if isinstance(value, dict):
        return any(contains_secret(k, secret) or contains_secret(v, secret) for k,v in value.items())
    return False



def strict_object(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise ValueError('Duplicate JSON member')
        result[key]=value
    return result


def invalid_constant(_):
    raise ValueError('Nonfinite JSON value')


def fetch(kind: str, season: int, week: int, api_key: str, *, opener=safe_open, retries=0, sleep=time.sleep, player_ids=None) -> dict:
    if not api_key.strip():
        raise IngestionError("FANTASYPROS_API_KEY is not configured")
    path, params, expected = request_spec(kind, season, week, player_ids=player_ids)
    url = BASE + path + "?" + urlencode(params)
    request = Request(url, headers={"x-api-key": api_key, "Accept": "application/json"})
    if type(retries) is not int or not 0 <= retries <= 2:
        raise ValueError("Retries must be between 0 and 2")
    for attempt in range(retries + 1):
        try:
            with opener(request, timeout=15) as response:
                if getattr(response, "status", 200) != 200:
                    raise IngestionError("FantasyPros: incomplete HTTP response")
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
        payload = json.loads(raw,object_pairs_hook=strict_object,parse_constant=invalid_constant)
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise IngestionError(f"FantasyPros {kind}: invalid JSON response") from None
    try:
        if contains_secret(payload, api_key):
            raise IngestionError("FantasyPros: credential echoed in response; rejected")
        original_count = len(payload.get(expected, [])) if isinstance(payload, dict) and isinstance(payload.get(expected), list) else 0
        payload, flags, yahoo, stamps, normalized = validate_payload(payload, kind, season, week, player_ids=player_ids)
    except (ValueError, TypeError, RecursionError):
        raise IngestionError("FantasyPros: malformed response values") from None
    return {
        "system": "SPARTA", "league": "sparta", "season": season, "week": week,
        "provider": "FantasyPros Public API v2", "kind": kind,
        "source_url": url, "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "authority": "NFL_INTELLIGENCE_ONLY_NOT_YAHOO_OWNERSHIP",
        "contract_status": "VALIDATED_SUPPLIED_OPENAPI",
        "openapi_sha256": document()[1], "normalized_players": normalized,
        "quality_flags": flags, "provider_timestamps": stamps,
        "yahoo_id_mapping": yahoo, "availability": "UNKNOWN",
        "scoring": "PPR" if kind in ("consensus","projections","projections_ros","points","compare") else "NOT_APPLICABLE",
        "scope": "rest_of_season" if kind == "projections_ros" else "weekly",
        "response_sha256": hashlib.sha256(raw).hexdigest(),
        "received_record_count": original_count,
        "duplicate_count": max(0, original_count - len(normalized)),
        "attempt_count": attempt + 1,
        "status": "unvalidated_for_decisions", "record_count": len(normalized),
        "payload": payload,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--week", type=int, required=True)
    parser.add_argument("--kind", choices=ALLOWED_KINDS + ("all",), default="all")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--player-ids", help="Two verified FantasyPros IDs, colon-delimited, for compare")
    parser.add_argument("--credential-rotated", action="store_true", help="Confirm key was rotated after chat exposure")
    parser.add_argument("--request-budget", type=int, default=0, help="Confirmed quota allowance for this invocation, including retries")
    parser.add_argument("--retries", type=int, choices=range(3), default=0)
    args = parser.parse_args(argv)
    kinds = PILOT_KINDS if args.kind == "all" else (args.kind,)
    key = os.environ.get("FANTASYPROS_API_KEY", "")
    if not key.strip():
        print("FANTASYPROS_API_KEY missing; no requests sent", file=sys.stderr)
        return 2
    if not args.credential_rotated or args.request_budget < len(kinds) * (1 + args.retries):
        print("Rotated credential and sufficient confirmed request budget required; no requests sent", file=sys.stderr)
        return 2
    try:
        validate_output_dir(args.output_dir)
        records = [fetch(kind, args.season, args.week, key, retries=args.retries, player_ids=args.player_ids) for kind in kinds]
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
