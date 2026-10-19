"""Read-only Sparta evidence handoffs. No FantasyPros calls or decision writes.

Canonical Yahoo sync is reused only with --refresh-yahoo and explicit API approval.
Without approved API access, consume authenticated snapshots and label gaps.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
from functools import lru_cache
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from jsonschema import Draft202012Validator,FormatChecker
from yahoo_parse import ET_TZ
from sparta_board import STARTER_SLOTS,FLEX_OK
from fp_weekly import current_week

ROOT=Path(__file__).resolve().parents[1]
JOBS=('report_card','waivers','injuries','lineup_check')
SCHEDULES={'0 13,14 * * 2':('report_card',1,9,0),'0 18,19 * * 2':('waivers',1,14,0),
           '0 14,15 * * 6':('injuries',5,10,0),'30 14,15 * * 0':('lineup_check',6,10,30)}


def stamp(value):
    if not isinstance(value,str):raise ValueError('aware source timestamp required')
    d=datetime.fromisoformat(value.replace('Z','+00:00'))
    if d.tzinfo is None:raise ValueError('aware source timestamp required')
    return d


def number(value):
    return value if type(value) in (int,float) and math.isfinite(value) else None


def load(path):
    return json.loads(Path(path).read_text())


def scheduled_job(schedule,now):
    item=SCHEDULES.get(schedule)
    if not item:return None
    job,day,hour,minute=item;local=now.astimezone(ET_TZ)
    # Paired UTC crons: exactly one is in the target ET hour under DST/EST.
    return job if (local.weekday(),local.hour)==(day,hour) and local.minute>=minute else None


def source(root,path,kind,doc):
    raw=(root/path).read_bytes()
    return {'path':path,'kind':kind,'sha256':hashlib.sha256(raw).hexdigest(),
            'observed_at':doc['observed_at'],'week':doc.get('coverage_week',doc.get('current_week',doc.get('week')))}


def section(data=None,src=None,now=None,complete=True,limitations=()):
    limits=list(limitations)
    if data is None or src is None:return {'status':'UNAVAILABLE','source':src,'data':None,'limitations':limits or ['No qualified authenticated source for this section']}
    age=(now-stamp(src['observed_at'])).total_seconds()
    status='STALE' if age>86400 else 'AVAILABLE' if complete else 'PARTIAL'
    if age>86400:limits.append('Source observation is more than24 hours old')
    return {'status':status,'source':src,'data':data,'limitations':limits}


def qualified(doc,now,api=False):
    try:
        if doc.get('completed') is not True or str(doc.get('yahoo_league_id',doc.get('league_id')))!='102586':return False
        if doc.get('league')!='sparta' or doc.get('season',2026)!=2026:return False
        if not isinstance(doc.get('source'),str) or 'yahoo' not in doc['source'].lower():return False
        if (stamp(doc['observed_at'])-now).total_seconds()>300:return False
        if api and (doc.get('team_mapping_complete') is not True or len(doc.get('teams',[]))!=12):return False
        return True
    except (ValueError,TypeError,KeyError):return False


def player(row,week,source_week):
    # Keep identifiers and publication context; no name-based cross-provider join.
    result=dict(row)
    result['slot']=row.get('slot',row.get('selectedPosition'))
    result['position']=row.get('position') or ''
    result['player_id']=row.get('player_id',row.get('playerId'))
    result['points']=number(row.get('points')) if row.get('points_week',source_week)==week else None
    if source_week==week and f'week{week}_points' in row:result['points']=number(row[f'week{week}_points'])
    if source_week==week and result['points'] is None and row.get('status')=='BYE':result['points']=0
    projection=row.get('projected_points') if row.get('projected_week',source_week)==week else None
    if source_week==week and f'week{week}_proj' in row:projection=row[f'week{week}_proj']
    result['projected_points']=number(projection)
    return result


def identity(p):
    value=p.get('player_id') or p.get('player_key') or p.get('playerId')
    return str(value).split('.p.')[-1] if value is not None else 'name:'+str(p.get('name',''))


def valid_matchup(m):
    teams=m.get('teams',[])
    return len(teams)==2 and len({t.get('code') for t in teams if t.get('code')})==2 and all(number(t.get('points')) is not None for t in teams)


def full_scoreboard(matches,codes):
    seen=[t.get('code') for m in matches for t in m.get('teams',[])]
    return len(matches)==6 and all(valid_matchup(m) for m in matches) and len(seen)==len(set(seen))==12 and set(seen)==set(codes)


def lineup_analysis(players,slots=None):
    slots=slots or STARTER_SLOTS
    pool=[p for p in players if not str(p.get('slot') or '').startswith('IR')]
    identities=[identity(p) for p in pool]
    if len(set(identities))!=len(identities):
        return dict(actual_points=None,optimal_points=None,points_left_on_bench=None,optimal_lineup=None,limitations=['Duplicate player identities; exact analysis refused'])
    starters=[p for p in pool if p.get('slot') in slots]
    actual=sum(p['points'] for p in starters) if Counter(p.get('slot') for p in starters)==Counter(slots) and all(number(p.get('points')) is not None for p in starters) else None
    if any(number(p.get('points')) is None for p in pool):
        return {'actual_points':actual,'optimal_points':None,'points_left_on_bench':None,'optimal_lineup':None,'limitations':['Missing actual points: no zero imputation or exact optimal-lineup claim']}
    def eligible(p,slot):
        positions=set(p.get('eligible_positions') or str(p.get('position','')).replace(',', '/').split('/'))
        positions={'DEF' if x in ('DST','D/ST') else x for x in positions}
        return bool(positions & (FLEX_OK if slot=='W/R/T' else {slot}))
    @lru_cache(None)
    def best(index,mask):
        if index==len(slots):return (0,())
        options=[]
        for i,p in enumerate(pool):
            if mask&(1<<i) or not eligible(p,slots[index]):continue
            score,tail=best(index+1,mask|(1<<i))
            if score is not None:options.append((p['points']+score,(i,)+tail))
        return max(options,key=lambda x:x[0]) if options else (None,())
    points,picks=best(0,0)
    return {'actual_points':actual,'optimal_points':points,'points_left_on_bench':round(points-actual,4) if points is not None and actual is not None else None,
            'optimal_lineup':[{'slot':s,'player':pool[i]['name'],'points':pool[i]['points']} for s,i in zip(slots,picks)] if points is not None else None,
            'limitations':[] if points is not None else ['No complete legal lineup exists in supplied historical roster']}


def collect(job,root=ROOT,now=None,week=None,season=2026):
    if job not in JOBS or season!=2026:raise ValueError('unsupported Sparta job/season')
    root=Path(root);now=now or datetime.now(timezone.utc)
    week=week or max(1,current_week(now.astimezone(ET_TZ).date())-(1 if job=='report_card' else 0))
    if type(week) is not int or not 1<=week<=18:raise ValueError('week must be1–18')
    result={'schema_version':1,'kind':'SPARTA_EVIDENCE_HANDOFF','league':'sparta','yahoo_league_id':'102586','season':season,'week':week,'job':job,
            'generated_at_utc':now.astimezone(timezone.utc).isoformat(),'decision_authority':'CLAUDE_SPARTA_BRAIN','status':'PARTIAL','sections':{},'limitations':[]}
    sections=result['sections'];choices=[]
    for path,kind in [('data/yahoo_api/latest.json','YAHOO_API'),('data/yahoo_live_snapshot_latest.json','YAHOO_BROWSER')]:
        try:
            doc=load(root/path)
            if qualified(doc,now,api=kind=='YAHOO_API'):choices.append((stamp(doc['observed_at']),doc,source(root,path,kind,doc)))
            else:result['limitations'].append('Rejected incomplete/unscoped/future Yahoo source: '+path)
        except (OSError,ValueError,TypeError):pass
    for path in sorted((root/'data/yahoo_api/weekly').glob('**/latest.json')):
        try:
            d=load(path)
            if qualified(d,now,api=True) and d.get('coverage_week',d.get('current_week'))==week:
                choices.append((stamp(d['observed_at']),d,source(root,str(path.relative_to(root)),'YAHOO_API',d)))
        except (OSError,ValueError,TypeError):pass
    if job=='report_card':
        matching=[x for x in choices if x[2].get('week')==week]
        choices=matching or choices
    chosen=max(choices,key=lambda x:x[0]) if choices else None
    doc=chosen[1] if chosen else {};src=chosen[2] if chosen else None;teams=doc.get('teams',[]) if isinstance(doc.get('teams'),list) else []
    roster_map={t['code']:[player(p,week,doc.get('coverage_week',doc.get('current_week',doc.get('week')))) for p in t.get('roster',[])] for t in teams if t.get('code')}
    complete_teams=len(roster_map)==12 and all(roster_map.values()) and src.get('week')==week
    sections['rosters']=section(roster_map or None,src,now,complete=complete_teams,limitations=[] if complete_teams else ['Populated requested-week rosters for all12 teams are required'])
    matches=[m for m in doc.get('matchups',[]) if m.get('week')==week]
    if not matches and doc.get('week')==week and isinstance(doc.get(f'week{week}'),dict):matches=[dict(doc[f'week{week}'],week=week,status='UNCONFIRMED_FINAL')]
    sections['matchups']=section(matches or None,src,now,complete=full_scoreboard(matches,roster_map),limitations=[] if full_scoreboard(matches,roster_map) else ['Full six-matchup scoreboard not present'])
    standings=[dict(t['standing'],team_code=t['code']) for t in teams if t.get('standing') and t.get('code')]
    sections['standings']=section(standings or None,src,now,complete=len(standings)==12)
    faab={t['code']:number(t.get('faab_balance')) for t in teams if t.get('code')}
    sections['faab']=section(faab or None,src,now,complete=len(faab)==12 and all(v is not None for v in faab.values()))
    sections['transactions']=section(doc.get('transactions'),src,now)
    # JD-only fallbacks preserve each source and never pretend to contain12 rosters.
    jd_choices=[]
    if 'JD' in roster_map:jd_choices.append((chosen[0],roster_map['JD'],src))
    try:
        r=load(root/'data/current_roster_jd.json')
        if r.get('league')=='sparta' and 'yahoo' in r.get('source','').lower() and (stamp(r['observed_at'])-now).total_seconds()<=300:
            jd_choices.append((stamp(r['observed_at']),[player(p,week,r.get('week')) for p in r['players']],source(root,'data/current_roster_jd.json','YAHOO_SCREENSHOT',r)))
    except (OSError,ValueError,KeyError,TypeError):pass
    connected=[]
    for path in sorted((root/'intelligence/yahoo').glob('*authenticated-readback.json')) if (root/'intelligence/yahoo').exists() else []:
        try:
            r=load(path);r=dict(r,observed_at=r.get('observed_at_utc'))
            if not qualified(r,now):continue
            relative=str(path.relative_to(root));s=source(root,relative,'AUTHENTICATED_YAHOO_CONNECTOR',r)
            connected.append((stamp(r['observed_at']),r,s))
            if r.get('team_code')=='JD' and r.get('team_key','').endswith('.l.102586.t.10'):
                coverage=r.get('roster',{}).get('pointsCoverage',{}).get('week')
                s=dict(s,week=coverage)
                rows=[player(p,week,coverage) for p in r.get('roster',{}).get('players',[])]
                jd_choices.append((stamp(r['observed_at']),rows,s))
        except (OSError,ValueError,KeyError,TypeError):pass
    # Historical report cards must select period-matched rosters, not today's lineup.
    if job=='report_card':jd_choices=[x for x in jd_choices if x[2].get('week')==week]
    jd=max(jd_choices,key=lambda x:x[0]) if jd_choices else None
    sections['jd_roster']=section(jd[1] if jd else None,jd[2] if jd else None,now,complete=bool(jd and jd[1]) and jd[2].get('week')==week)
    for _,r,s in sorted(connected):
        if sections['faab']['data'] is None and number(r.get('current_faab')) is not None:
            sections['faab']=section({'JD':number(r.get('current_faab'))},s,now,complete=False,limitations=['JD-only connected budget; other11 team balances unavailable'])
        if not sections['transactions']['source'] or stamp(s['observed_at'])>stamp(sections['transactions']['source']['observed_at']):
            sections['transactions']=section(r.get('transactions'),s,now,complete=False,limitations=['Bounded JD-only transaction evidence; FAAB null is unknown',json.dumps(r.get('transaction_limitations',{}),sort_keys=True)])
        if sections['standings']['data'] is None and r.get('standings'):
            sections['standings']=section([r.get('standings')],s,now,complete=False,limitations=['JD-only standings'])
    owned={identity(p) for rows in roster_map.values() for p in rows}
    available=None
    if isinstance(doc.get('free_agents'),dict):
        available={}
        fresh=sections['rosters']['status']=='AVAILABLE' and complete_teams and doc.get('current_week',doc.get('week'))==week
        for pos,rows in doc['free_agents'].items():
            safe=[]
            for p in rows:
                if identity(p) in owned:continue
                q=dict(p);q['availability']=({'waivers':'WAIVERS_CONFIRMED','freeagents':'FREE_AGENT_CONFIRMED'}.get(p.get('ownership_type'),'UNKNOWN') if fresh else 'UNKNOWN');safe.append(q)
            available[pos]=safe
    sections['free_agents']=section(available,src,now,complete=complete_teams and set(available or {}) >= {'QB','RB','WR','TE','K','DEF'},limitations=['Rostered percentage is context only; availability comes only from fresh Yahoo ownership'])
    # Stored board is a reference only after explicit hash-bound review, never a live call.
    board_path=f'intelligence/board/{season}-w{week:02d}.json';board=None;board_src=None
    try:
        raw=(root/board_path).read_bytes();b=json.loads(raw);proof=load(root/f'intelligence/board/{season}-w{week:02d}.validation.json')
        if b.get('league')=='sparta' and b.get('season')==season and b.get('week')==week and proof.get('status')=='PASS' and proof.get('board_sha256')==hashlib.sha256(raw).hexdigest():
            board={'path':board_path,'sha256':proof['board_sha256'],'validated':True}
            board_src={'path':board_path,'kind':'VALIDATED_STORED_BOARD','sha256':proof['board_sha256'],'observed_at':b['generated_from']['fantasypros_pulled_at'],'week':week}
    except (OSError,ValueError,KeyError,TypeError):pass
    sections['weekly_board']=section(board,board_src,now,limitations=[] if board else ['No hash-bound validation receipt; existing board excluded'])
    players=jd[1] if jd else [];jd_src=jd[2] if jd else None
    spots={'active_players':sum(not str(p.get('slot') or '').startswith('IR') for p in players),'ir_players':sum(str(p.get('slot') or '').startswith('IR') for p in players)} if jd else None
    if spots:spots['open_active_slots']=max(0,17-spots['active_players']);spots['ir_limit']=1
    sections['roster_spots']=section(spots,jd_src,now)
    flags=[]
    for p in players:
        if p.get('slot') not in STARTER_SLOTS:continue
        if str(p.get('status','')).upper() in ('IR','IR-R','O','OUT','INACTIVE','PUP','SUSP','SUSPENDED'):
            flags.append({'player':p.get('name'),'slot':p['slot'],'type':'STARTER_DESIGNATED_UNAVAILABLE','designation':p['status']})
        if str(p.get('bye_week'))==str(week) or (str(p.get('status')).upper()=='BYE' and jd_src.get('week')==week):
            flags.append({'player':p.get('name'),'slot':p['slot'],'type':'STARTER_BYE'})
    if job=='lineup_check':sections[job]=section({'players':players,'flags':flags} if jd else None,jd_src,now,complete=bool(players) and jd_src.get('week')==week and Counter(p.get('slot') for p in players if p.get('slot') in STARTER_SLOTS)==Counter(STARTER_SLOTS) and all(p.get('projected_points') is not None for p in players if p.get('slot') in STARTER_SLOTS),limitations=['Completeness requires requested-week roster, all10 starter slots and their projections; missing projections remain null'])
    if job=='waivers':sections[job]=section({'roster_spots':spots,'roster_designations':[{'player':p.get('name'),'status':p.get('status'),'bye_week':p.get('bye_week'),'slot':p.get('slot')} for p in players]} if jd else None,jd_src,now,complete=bool(players) and jd_src.get('week')==week)
    if job=='injuries':
        opponent=None
        for m in matches:
            codes=[t.get('code') for t in m.get('teams',[])]
            if 'JD' in codes:opponent=next((x for x in codes if x and x!='JD'),None)
        sections[job]=section({'JD':players,'opponent_code':opponent,'opponent_roster':roster_map.get(opponent),'opponent_source_section':'rosters'} if jd else None,jd_src,now,complete=bool(players) and bool(roster_map.get(opponent)) and src.get('week')==week,limitations=[] if opponent in roster_map else ['Requested-week opponent or opponent roster missing'])
    if job=='report_card':
        exact_roster=jd is not None and jd_src.get('week')==week
        final=[m for m in matches if str(m.get('status','')).lower() in ('postevent','final','completed') and valid_matchup(m)]
        data={'final_matchups':final,'scores_source_section':'matchups','starters':[p for p in players if p.get('slot') in STARTER_SLOTS],'bench':[p for p in players if p.get('slot') in ('BN','IR','IR+')],'lineup_analysis':lineup_analysis(players)} if exact_roster and players and final else None
        sections[job]=section(data,jd_src,now,complete=bool(data) and full_scoreboard(final,roster_map) and data['lineup_analysis']['actual_points'] is not None and data['lineup_analysis']['optimal_points'] is not None,limitations=[] if data else ['Exact-week historical roster and authenticated final scores required; no historical inference from current lineup'])
    required=['rosters','matchups','standings','free_agents','faab','transactions','jd_roster',job]
    result['status']='COMPLETE' if all(sections[k]['status']=='AVAILABLE' for k in required) else 'PARTIAL'
    return result


def validate_handoff(doc,root=ROOT):
    schema=load(Path(root)/'contracts/sparta_handoff.schema.json')
    if next(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(doc),None) is not None:raise ValueError('Sparta handoff contract validation failed')
    stamp(doc['generated_at_utc'])
    for entry in doc['sections'].values():
        if entry['source']:stamp(entry['source']['observed_at'])
    # JSON serialization also rejects any nonfinite observations, including extra fields.
    json.dumps(doc,allow_nan=False)


def publish(doc,root=ROOT):
    root=Path(root);validate_handoff(doc,root)
    directory=root/'intelligence/handoff';directory.mkdir(parents=True,exist_ok=True)
    path=directory/f"{doc['season']}-wk{doc['week']:02d}-{doc['job']}.json"
    body=json.dumps(doc,indent=2,ensure_ascii=False,allow_nan=False)+'\n'
    # Avoid routine commits if input evidence and derived statuses did not change.
    if path.exists():
        old=load(path);old.pop('generated_at_utc',None);current=dict(doc);current.pop('generated_at_utc',None)
        if old==current and path.with_suffix('.md').exists():return path
    temporary=path.with_suffix('.json.tmp');temporary.write_text(body);temporary.replace(path)
    lines=[f"# Sparta evidence — {doc['season']} week{doc['week']} {doc['job']}",'',f"Status: **{doc['status']}**. Generated {doc['generated_at_utc']}. Evidence only; Claude retains decision authority.",'']
    for name,s in doc['sections'].items():
        origin=s['source'];where=(origin['path']+' at '+origin['observed_at']) if origin else 'no qualified source'
        lines.append(f"- {name}: {s['status']} — {where}")
        lines.extend('  '+note for note in s['limitations'])
    job=doc['sections'][doc['job']]
    if job['data'] and doc['job']=='lineup_check':lines.extend('- Evidence flag: '+json.dumps(f) for f in job['data']['flags'])
    if job['data'] and doc['job']=='report_card':lines.append('\nActual/optimal/bench gap: '+json.dumps(job['data']['lineup_analysis'],ensure_ascii=False))
    if job['data'] and doc['job']=='waivers':lines.append('\nRoster space: '+json.dumps(job['data']['roster_spots']))
    if doc['sections']['faab']['data'] is not None:lines.append('\nObserved FAAB (null = unknown): '+json.dumps(doc['sections']['faab']['data'],sort_keys=True))
    path.with_suffix('.md').write_text('\n'.join(lines)+'\n')
    # Safe readback before a workflow may commit the output.
    if load(path)!=doc:raise ValueError('handoff readback mismatch')
    return path


def refresh_yahoo(root,week):
    if os.environ.get('SPARTA_YAHOO_API_APPROVED','').lower()!='true':raise ValueError('Yahoo API approval is not confirmed')
    if not all(os.environ.get(k) for k in ('YAHOO_CLIENT_ID','YAHOO_CLIENT_SECRET','YAHOO_REFRESH_TOKEN')):raise ValueError('Yahoo secrets are not configured')
    from yahoo_client import YahooClient
    import yahoo_sync
    # Existing authority-safe implementation, never apply durable changes.
    return yahoo_sync.run(YahooClient.from_env(),apply=False,root=Path(root),coverage_week=week)


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--job',choices=JOBS);ap.add_argument('--week',type=int);ap.add_argument('--season',type=int,default=2026)
    ap.add_argument('--resolve-schedule');ap.add_argument('--refresh-yahoo',action='store_true');args=ap.parse_args(argv)
    if args.resolve_schedule:
        job=scheduled_job(args.resolve_schedule,datetime.now(timezone.utc));print('run='+str(job is not None).lower());print('job='+(job or ''));return 0
    if not args.job:ap.error('--job required')
    refresh_failed=False
    if args.refresh_yahoo:
        try:refresh_yahoo(ROOT,args.week or max(1,current_week(datetime.now(timezone.utc).astimezone(ET_TZ).date())-(1 if args.job=='report_card' else 0)))
        except Exception:refresh_failed=True # never expose transport/credential exception text
    report=collect(args.job,week=args.week,season=args.season)
    if refresh_failed:report['limitations'].append('Yahoo refresh unavailable; using qualified cached evidence only')
    path=publish(report);print(f"SPARTA HANDOFF {path.relative_to(ROOT)} status={report['status']}");return 0


if __name__=='__main__':raise SystemExit(main())
