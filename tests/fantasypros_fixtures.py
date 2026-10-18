"""Synthetic contract fixtures, never provider observations or live player IDs."""
from datetime import datetime,timezone
from fantasypros_contract import document,resolve,PATHS,RESPONSES


def build(schema):
    if '$ref' in schema: return build(resolve(schema['$ref']))
    if 'allOf' in schema:
        out={}
        for sub in schema['allOf']: out.update(build(sub))
        return out
    if 'oneOf' in schema: return build(schema['oneOf'][0])
    if 'enum' in schema: return next((x for x in schema['enum'] if x is not None),None)
    typ=schema.get('type')
    if isinstance(typ,list): typ=next(x for x in typ if x not in (None,'null'))
    if typ=='object': return {name:build(schema.get('properties',{}).get(name,{})) for name in schema.get('required',[])}
    if typ=='array': return [build(schema['items'])] if 'items' in schema else []
    if typ=='integer': return 1
    if typ=='number': return 1.0
    if typ=='boolean': return False
    return 'Test'


def fixture(kind='consensus'):
    doc,_=document()
    schema=({'$ref':'#/components/schemas/'+RESPONSES[kind]} if kind in RESPONSES else
        doc['paths'][PATHS[kind]]['get']['responses']['200']['content']['application/json']['schema'])
    out=build(schema)
    out.update(sport='NFL') if kind!='projections' else None
    if kind in ('consensus','compare'): out.update(year='2026',week='6')
    if kind in ('projections','points','experts'): out['season']='2026'
    if kind in ('projections','experts'): out['week']='6'
    if kind in ('consensus','points'): out['scoring']='PPR'
    if kind=='consensus':
        out.update(position_id='FLX',ranking_type_name='WW',last_updated='10/17',last_updated_ts=int(datetime.now(timezone.utc).timestamp()),count=1)
        row=build({'$ref':'#/components/schemas/NFLRankingPlayer'})
        row.update(player_id=1,player_name='Test',player_position_id='WR',player_yahoo_id='10',rank_ecr=50)
        out['players']=[row]
    if kind=='projections':
        out.update(scoring='STD',positions='WR',count='1',experts=[1])
        row=out['players'][0]
        row.update(fpid='1',name='Test',position_id='WR')
        stats=build({'$ref':'#/components/schemas/NFLRBWRTEPlayerProjections'})
        stats.update(points=7.0,points_ppr=12.0,rec_rec=5.0)
        row['stats']=[stats]
    if kind=='injuries':
        row=build(doc['components']['schemas']['NFLInjuryResponse']['allOf'][1]['properties']['injuries']['items']);out['injuries']=[row];row.update(player_id=1,name='Test',yahoo_id='10',injury_update_date='2026-10-17')
    if kind=='experts': out['experts']=[build(doc['components']['schemas']['NFLExpertsResponse']['allOf'][1]['properties']['experts']['items'])]
    if kind=='news': out['items'][0].update(player_id=1,sport_id='NFL')
    if kind=='points': out['players'][0].update(player_id=1,player_name='Test',position_id='WR',weeks={'6':12.0})
    if kind=='compare':
        out.update(position_id='WR',ranking_type='weekly',rankings={'PPR':{'1':[{'expert_id':'1','rank':'1'}],'2':[{'expert_id':'1','rank':'2'}]}},players={'1':{'player_name':'Test','player_team_id':'TST','player_position_id':'WR','player_page_url':'https://example.invalid/1'},'2':{'player_name':'Other','player_team_id':'TST','player_position_id':'WR','player_page_url':'https://example.invalid/2'}})
    return out
