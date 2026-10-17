"""Offline analytical artifacts, never a league database or live recommendation."""
from __future__ import annotations
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path


def evaluate(rows):
    """Paired full-PPR errors on a common cohort; values must be pre-aligned.

    This does not establish prediction-time provenance. Callers must preserve
    their input hashes and prove forecasts predate kickoff before interpretation.
    """
    seen = set()
    for row in rows:
        if (row.get('season') != 2026 or type(row.get('week')) is not int
                or not 1 <= row['week'] <= 18 or row.get('scoring') != 'PPR'
                or not isinstance(row.get('player_id'), str) or not row['player_id'].strip()):
            raise ValueError('Invalid full-PPR evaluation cohort')
        ident = (row['season'],row['week'],row['player_id'])
        if ident in seen: raise ValueError('Duplicate evaluation observation')
        seen.add(ident)
        for field in ('fantasypros','sparta','actual','lower','upper'):
            value = row.get(field)
            if type(value) not in (int,float) or not math.isfinite(value) or abs(value) > 1000:
                raise ValueError('Missing, nonfinite or implausible fantasy-point observation')
        if row['lower'] > row['upper']: raise ValueError('Inverted prediction interval')
    n = len(rows)
    result = {'status':'DESCRIPTIVE_ONLY' if n else 'INSUFFICIENT_DATA',
              'sample_size':n,'scoring':'PPR','promote_weights':False,
              'prediction_time_provenance_verified':False}
    for model in ('fantasypros','sparta'):
        errors = [r[model]-r['actual'] for r in rows]
        result[model] = {'mae':sum(abs(e) for e in errors)/n if n else None,
                         'rmse':math.sqrt(sum(e*e for e in errors)/n) if n else None,
                         'bias':sum(errors)/n if n else None}
    result['interval_coverage'] = sum(r['lower'] <= r['actual'] <= r['upper'] for r in rows)/n if n else None
    result['mean_interval_width'] = sum(r['upper']-r['lower'] for r in rows)/n if n else None
    pairs = [(a,b) for a,b in itertools.combinations(rows,2)
             if a['week']==b['week'] and a['actual']!=b['actual']]
    result['pairwise_directional_accuracy'] = (sum((a['fantasypros']-b['fantasypros'])*(a['actual']-b['actual'])>0
        for a,b in pairs)/len(pairs) if pairs else None)
    result['directional_pair_count']=len(pairs)
    return result


def comparison(root):
    path = Path(root)/'learning/decision_ledger.jsonl'
    raw = path.read_bytes()
    lines = raw.decode().splitlines()
    ids = ('SPARTA-2026W6-WICKS-COWING-FRIDAY-20261016-1655',
           'SPARTA-2026W6-WICKS-COWING-USAGE-REASSESS-20261017-0704')
    evidence = []
    for line_number,line in enumerate(lines,1):
        row = json.loads(line)
        if row.get('decision_id') in ids:
            evidence.append({'line':line_number,'decision_id':row['decision_id'],
                'timestamp_et':row['timestamp_et'],'signals':row['key_supporting_signals'],
                'risks':row['key_risk_factors']})
    if len(evidence)!=2: raise ValueError('Decision-time comparison evidence missing')
    return {'system':'SPARTA','season':2026,'week':6,'scoring':'PPR',
        'status':'BLOCKED_FANTASYPROS_DATA_MISSING','authority':'RESEARCH_ONLY',
        'new_recommendation':False,'kickoff_verified':False,
        'timing_note':'Historical decision-evidence comparison only; no fresh prediction or lineup instruction.',
        'source':{'path':'learning/decision_ledger.jsonl','sha256':hashlib.sha256(raw).hexdigest()},
        'decision_evidence':evidence,
        'players':[
            {'name':'Dontayvion Wicks','fantasypros_id':None,'availability':'UNKNOWN',
             'fantasypros_ppr_rank':None,'fantasypros_projection_ppr':None,
             'supporting_signals':['Recorded 17% target share with Smith healthy in Weeks 1–3; 8 Week 5 targets.',
                                   'Recorded full practice clearance before Sunday.'],
             'risks':['Smith return and McKee replacing Hurts weaken volume extrapolation.'],
             'uncertainty':'No verified forecast interval or FantasyPros data.'},
            {'name':'Jacob Cowing','fantasypros_id':None,'availability':'UNKNOWN',
             'fantasypros_ppr_rank':None,'fantasypros_projection_ppr':None,
             'supporting_signals':['Recorded SF receiver injuries could expand opportunity.'],
             'risks':['Recorded Week 5: 2 targets, 50% route participation; fragile role.',
                      'Monday injury/activation uncertainty arrives after Sunday fallback locks.'],
             'uncertainty':'No verified forecast interval or FantasyPros data.'}],
        'evidence_limit':'Signals reproduce repository decision assertions, not freshly verified underlying NFL sources.',
        'accounting_conflict':{'current_directive':'$1 per completed pickup plus applicable FAAB',
             'older_rules':'AGENTS.md rules 14/50 and learning_rules_v3: winning FAAB only',
             'historical_accounting_changed':False},
        'missing':['Authoritative OpenAPI specification','Rotated API key and quota confirmation',
                   'FantasyPros rankings/projections','Independent route/target/injury verification',
                   'Matched actual full-PPR outcomes and pre-kickoff forecasts']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rows',type=Path)
    parser.add_argument('--comparison',action='store_true')
    args=parser.parse_args(argv)
    if args.comparison:
        result=comparison(Path(__file__).resolve().parents[1])
    elif args.rows:
        raw=args.rows.read_bytes()
        result=evaluate(json.loads(raw))
        result['input_sha256']=hashlib.sha256(raw).hexdigest()
    else: parser.error('Provide --comparison or --rows')
    print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False))
    return 0

if __name__=='__main__': raise SystemExit(main())
