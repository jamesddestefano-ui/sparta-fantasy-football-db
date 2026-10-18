"""Pinned, local-only FantasyPros OpenAPI contracts. Never resolves remote refs."""
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1]
PATHS={
 'consensus':'/{sport}/{season}/consensus-rankings',
 'projections':'/nfl/{season}/projections',
 'injuries':'/{sport}/injuries',
 'news':'/{sport}/news',
 'compare':'/{sport}/compare-players',
 'points':'/nfl/{season}/player-points',
 'experts':'/{sport}/{season}/rankings/experts',
}
RESPONSES={'consensus':'NFLRankingsResponse','injuries':'NFLInjuryResponse',
           'compare':'NFLComparePlayersResponse','experts':'NFLExpertsResponse'}
ARRAYS={'consensus':'players','projections':'players','injuries':'injuries',
        'news':'items','compare':'rankings','points':'players','experts':'experts'}

@lru_cache(maxsize=1)
def document():
    raw=(ROOT/'contracts/fantasypros_public_v2.openapi.json').read_bytes()
    manifest=json.loads((ROOT/'contracts/fantasypros_source.json').read_bytes())
    if hashlib.sha256(raw).hexdigest()!=manifest['json_sha256']:
        raise ValueError('Pinned contract hash mismatch')
    doc=json.loads(raw)
    # The supplied YAML uses null (not "null") in JSON Schema type arrays.
    # Also honor OpenAPI's nullable extension where present. Original is retained.
    def normalize(value):
        if isinstance(value,list): return [normalize(x) for x in value]
        if not isinstance(value,dict): return value
        out={k:normalize(v) for k,v in value.items()}
        if isinstance(out.get('type'),list): out['type']=['null' if x is None else x for x in out['type']]
        if out.get('nullable') and isinstance(out.get('type'),str): out['type']=[out['type'],'null']
        if '$ref' in out and not out['$ref'].startswith('#/'): raise ValueError('Nonlocal schema reference forbidden')
        return out
    return normalize(doc),hashlib.sha256(raw).hexdigest()


def resolve(ref):
    node=document()[0]
    for part in ref.removeprefix('#/').split('/'): node=node[part]
    return node


def validator(schema):
    root=deepcopy(schema)
    root['components']=document()[0]['components']
    Draft202012Validator.check_schema(root)
    return Draft202012Validator(root)


class ResponseSchemaError(ValueError):
    def __init__(self, diagnostics):
        super().__init__('FantasyPros response violates supplied OpenAPI schema')
        self.diagnostics = diagnostics


def validate_response(kind,payload):
    doc,digest=document()
    schema=({'$ref':'#/components/schemas/'+RESPONSES[kind]} if kind in RESPONSES else
            doc['paths'][PATHS[kind]]['get']['responses']['200']['content']['application/json']['schema'])
    # Do not stringify errors: they contain provider values, potentially secrets.
    diagnostics=[]
    for error in validator(schema).iter_errors(payload):
        # Schema paths come from the pinned local contract, never provider keys.
        # Do not include error.message, instance, or absolute_path.
        diagnostic={'validator':error.validator,'schema_path':list(error.absolute_schema_path)}
        if error.validator=='required' and isinstance(error.instance,dict):
            diagnostic['missing_fields']=[key for key in error.validator_value if key not in error.instance]
        diagnostics.append(diagnostic)
        if len(diagnostics)>=12: break
    if diagnostics:
        raise ResponseSchemaError(diagnostics)
    return digest


def validate_request(kind,season,params):
    doc,_=document()
    op=doc['paths'][PATHS[kind]]['get']
    if op.get('security') != [{'api_key':[]}]: raise ValueError('API header authentication contract changed')
    parameters=[resolve(p['$ref']) if '$ref' in p else p for p in op.get('parameters',[])]
    supported={p['name']:p for p in parameters if p['in']=='query'}
    if set(params)-set(supported): raise ValueError('Unsupported FantasyPros query parameter')
    for name,p in supported.items():
        if p.get('required') and name not in params: raise ValueError('Required FantasyPros query parameter missing')
        if name not in params: continue
        schema=p['schema']; ref=schema.get('$ref','')
        # Generic SPORT oneOf enums overlap (NFL/NCAAF, etc.); specialize NFL.
        mapping={'SPORTPositions':'NFLPositions','SPORTScoringTypes':'NFLScoringTypes','SPORTRankingTypes':'NFLRankingTypes'}
        if ref.split('/')[-1] in mapping: schema={'$ref':'#/components/schemas/'+mapping[ref.split('/')[-1]]}
        actual=resolve(schema['$ref']) if '$ref' in schema else schema
        value=params[name]
        if actual.get('type')=='integer':
            try: value=int(value)
            except (ValueError,TypeError): raise ValueError('Invalid integer query parameter') from None
        elif actual.get('type')=='boolean':
            if value not in ('true','false'): raise ValueError('Invalid boolean query parameter')
            value=value=='true'
        if next(validator(schema).iter_errors(value),None) is not None: raise ValueError('Query parameter violates OpenAPI')
    return PATHS[kind].replace('{sport}','nfl').replace('{season}',str(season))
