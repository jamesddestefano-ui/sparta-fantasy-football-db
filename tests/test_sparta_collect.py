"""Offline collector behavior and integrity tests; no provider calls."""
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
NOW=datetime(2026,10,20,13,0,tzinfo=timezone.utc)

class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        (self.root/'data').mkdir();(self.root/'contracts').mkdir()
        if (ROOT/'contracts/sparta_handoff.schema.json').exists():shutil.copy(ROOT/'contracts/sparta_handoff.schema.json',self.root/'contracts')
    def mod(self):
        path=ROOT/'scripts/sparta_collect.py';self.assertTrue(path.exists(),'collector entrypoint missing')
        spec=importlib.util.spec_from_file_location('sparta_collect_test',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    def save(self,name,value):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value));return path
    def api(self,**extra):
        teams=[{'code':code,'team_key':f'470.l.102586.t.{i+1}','roster':[],'faab_balance':33 if code=='JD' else 50,'standing':{'rank':i+1}} for i,code in enumerate(['BE','MC','VV','TM','SR','MN','ANT','MM','ME','JD','JU','JP'])]
        data={'league':'sparta','yahoo_league_id':'102586','season':2026,'current_week':7,'completed':True,'team_mapping_complete':True,'source':'Authenticated Yahoo Fantasy Sports API v2','observed_at':'2026-10-20T08:00:00-04:00','teams':teams,'free_agents':{'WR':[]},'transactions':[],'matchups':[]};data.update(extra);return data
    def test_newer_qualified_api_wins_over_browser(self):
        self.save('data/yahoo_api/latest.json',self.api());self.save('data/yahoo_live_snapshot_latest.json',dict(self.api(),observed_at='2026-10-19T08:00:00-04:00',source='Authenticated Yahoo browser'))
        r=self.mod().collect('waivers',root=self.root,now=NOW,week=7)
        self.assertEqual(r['sections']['rosters']['source']['kind'],'YAHOO_API')
        self.assertEqual(r['sections']['faab']['data']['JD'],33)
    def test_newer_browser_wins_and_incomplete_or_wrong_api_never_used(self):
        self.save('data/yahoo_api/latest.json',self.api(yahoo_league_id='OTHER'))
        self.save('data/yahoo_live_snapshot_latest.json',dict(self.api(),source='Authenticated Yahoo browser'))
        r=self.mod().collect('waivers',root=self.root,now=NOW,week=7)
        self.assertEqual(r['sections']['rosters']['source']['kind'],'YAHOO_BROWSER')
    def test_stale_availability_is_unknown_not_free_agent(self):
        data=self.api(observed_at='2026-10-15T08:00:00-04:00',free_agents={'WR':[{'player_id':1,'name':'Test','ownership_type':'freeagents','percent_owned':2}]})
        self.save('data/yahoo_api/latest.json',data);r=self.mod().collect('waivers',root=self.root,now=NOW,week=7)
        self.assertEqual(r['sections']['free_agents']['status'],'STALE')
        self.assertEqual(r['sections']['free_agents']['data']['WR'][0]['availability'],'UNKNOWN')
    def test_owned_player_never_becomes_free_agent(self):
        d=self.api(free_agents={'WR':[{'player_id':1,'name':'Test','ownership_type':'freeagents'}]});d['teams'][0]['roster']=[{'player_id':1,'name':'Test'}]
        self.save('data/yahoo_api/latest.json',d);r=self.mod().collect('waivers',root=self.root,now=NOW,week=7)
        self.assertEqual(r['sections']['free_agents']['data']['WR'],[])
    def test_missing_data_and_unknown_faab_are_explicit(self):
        r=self.mod().collect('waivers',root=self.root,now=NOW,week=7)
        self.assertEqual(r['sections']['faab']['status'],'UNAVAILABLE');self.assertIsNone(r['sections']['faab']['data'])
        self.assertEqual(r['status'],'PARTIAL')
    def test_exact_optimizer_handles_multi_position_and_excludes_ir(self):
        rows=[{'name':'dual','position':'QB/TE','eligible_positions':['QB','TE'],'slot':'QB','points':30}, {'name':'qb','position':'QB','slot':'BN','points':29},{'name':'te','position':'TE','slot':'TE','points':0},{'name':'ir','position':'TE','slot':'IR','points':99}]
        r=self.mod().lineup_analysis(rows,slots=['QB','TE'])
        self.assertEqual(r['actual_points'],30);self.assertEqual(r['optimal_points'],59);self.assertEqual(r['points_left_on_bench'],29)
    def test_missing_points_does_not_become_zero(self):
        r=self.mod().lineup_analysis([{'name':'qb','position':'QB','slot':'QB','points':None}],slots=['QB'])
        self.assertIsNone(r['actual_points']);self.assertIsNone(r['optimal_points'])
    def test_wrong_week_cannot_supply_final_report_card(self):
        self.save('data/yahoo_api/latest.json',self.api(matchups=[{'week':7,'status':'postevent','teams':[]}]))
        r=self.mod().collect('report_card',root=self.root,now=NOW,week=6)
        self.assertEqual(r['sections']['report_card']['status'],'UNAVAILABLE')
    def test_starter_ir_and_bye_flags_are_evidence_only(self):
        d=self.api();d['teams'][9]['roster']=[{'name':'K','position':'K','slot':'K','status':'IR'},{'name':'W','position':'WR','slot':'WR','bye_week':7}]
        self.save('data/yahoo_api/latest.json',d);r=self.mod().collect('lineup_check',root=self.root,now=NOW,week=7)
        alerts=r['sections']['lineup_check']['data']['flags'];self.assertEqual(len(alerts),2)
        self.assertNotIn('recommendation',json.dumps(r))
    def test_unvalidated_board_excluded(self):
        self.save('intelligence/board/2026-w07.json',{'league':'sparta','season':2026,'week':7,'suggested':['Do something']})
        r=self.mod().collect('waivers',root=self.root,now=NOW,week=7)
        self.assertEqual(r['sections']['weekly_board']['status'],'UNAVAILABLE')
    def test_contract_validation_and_only_handoff_writes(self):
        self.save('data/yahoo_api/latest.json',self.api());m=self.mod();r=m.collect('waivers',root=self.root,now=NOW,week=7)
        before=(self.root/'data/yahoo_api/latest.json').read_bytes();p=m.publish(r,root=self.root)
        self.assertEqual(p.name,'2026-wk07-waivers.json');self.assertEqual(before,(self.root/'data/yahoo_api/latest.json').read_bytes());self.assertTrue(p.with_suffix('.md').exists())
        bad=dict(r,league='mongo')
        with self.assertRaises(ValueError):m.validate_handoff(bad,root=self.root)
    def test_dst_scheduler_runs_once_at_requested_et_time(self):
        m=self.mod()
        self.assertEqual(m.scheduled_job('0 13,14 * * 2',datetime(2026,10,20,13,5,tzinfo=timezone.utc)),'report_card')
        self.assertIsNone(m.scheduled_job('0 13,14 * * 2',datetime(2026,10,20,14,5,tzinfo=timezone.utc)))
        self.assertEqual(m.scheduled_job('0 13,14 * * 2',datetime(2026,11,10,14,5,tzinfo=timezone.utc)),'report_card')
        self.assertEqual(m.scheduled_job('30 14,15 * * 0',datetime(2026,11,8,15,35,tzinfo=timezone.utc)),'lineup_check')
    def test_empty_rosters_and_empty_final_scores_cannot_be_complete(self):
        d=self.api(matchups=[{'week':7,'status':'postevent','teams':[]} for _ in range(6)])
        self.save('data/yahoo_api/latest.json',d);m=self.mod()
        for job in ('report_card','lineup_check','waivers'):
            r=m.collect(job,root=self.root,now=NOW,week=7)
            self.assertEqual(r['status'],'PARTIAL');self.assertNotEqual(r['sections'][job]['status'],'AVAILABLE')
            self.assertNotEqual(r['sections']['rosters']['status'],'AVAILABLE')
    def test_optimizer_rejects_duplicate_identity_and_invalid_actual_slots(self):
        m=self.mod();p={'name':'same','player_id':'1','position':'WR','slot':'WR','points':30}
        r=m.lineup_analysis([p,dict(p,player_id='470.p.1')],slots=['WR','WR'])
        self.assertIsNone(r['optimal_points'])
        r=m.lineup_analysis([dict(p,player_id=1),dict(p,name='other',player_id=2)],slots=['WR','TE'])
        self.assertIsNone(r['actual_points'])
    def test_wrong_week_waiver_roster_is_partial(self):
        d=self.api(current_week=6);d['teams'][9]['roster']=[{'name':'test','slot':'BN'}]
        self.save('data/yahoo_api/latest.json',d)
        r=self.mod().collect('waivers',root=self.root,now=NOW,week=7)
        self.assertNotEqual(r['sections']['waivers']['status'],'AVAILABLE')
    def test_player_key_and_player_id_match_for_owned_filter(self):
        d=self.api(free_agents={'WR':[{'player_key':'470.p.1','name':'test','ownership_type':'freeagents'}]})
        d['teams'][0]['roster']=[{'player_id':1,'name':'test'}];self.save('data/yahoo_api/latest.json',d)
        self.assertEqual(self.mod().collect('waivers',root=self.root,now=NOW,week=7)['sections']['free_agents']['data']['WR'],[])
    def test_report_card_selects_historical_snapshot(self):
        self.save('data/yahoo_api/latest.json',self.api())
        old=self.api(current_week=6,observed_at='2026-10-19T08:00:00-04:00')
        self.save('data/yahoo_api/weekly/2026-w06/latest.json',old)
        r=self.mod().collect('report_card',root=self.root,now=NOW,week=6)
        self.assertEqual(r['sections']['rosters']['source']['week'],6)
    def test_weekly_parser_preserves_coverage_and_does_not_treat_season_total_as_week(self):
        import yahoo_parse
        from xml.etree.ElementTree import fromstring
        p=yahoo_parse.parse_player(fromstring('<player><player_id>1</player_id><player_points><coverage_type>week</coverage_type><week>6</week><total>12.5</total></player_points></player>'))
        self.assertEqual(p['points'],12.5);self.assertEqual(p['points_week'],6)
        p=yahoo_parse.parse_player(fromstring('<player><player_points><coverage_type>season</coverage_type><total>100</total></player_points></player>'))
        self.assertIsNone(p['points']);self.assertIsNone(p['points_week'])
    def test_contract_rejects_forged_complete_and_bad_timestamp(self):
        m=self.mod();r=m.collect('waivers',root=self.root,now=NOW,week=7)
        with self.assertRaises(ValueError):m.validate_handoff(dict(r,status='COMPLETE'),root=self.root)
        with self.assertRaises(ValueError):m.validate_handoff(dict(r,generated_at_utc='yesterday'),root=self.root)
    def test_weekly_sync_uses_documented_week_and_cannot_apply(self):
        import yahoo_sync
        from unittest.mock import patch
        fake=type('Client',(),{'requests_made':0})()
        with patch.object(yahoo_sync,'load_repo',return_value={}):
            with self.assertRaises(ValueError):yahoo_sync.run(fake,root=self.root,coverage_week=6,apply=True)
        from yahoo_fixtures import write_fixtures
        fx=write_fixtures(self.root/'fixtures');client=yahoo_sync.FixtureClient(fx)
        calls=[];original=client.get
        def get(path):calls.append(path);return original(path)
        client.get=get
        raw=yahoo_sync.fetch_all(client,coverage_week=6)
        self.assertEqual(raw['coverage_week'],6)
        self.assertTrue(any('/roster;week=6/players/stats;type=week;week=6' in x for x in calls))
        self.assertTrue(any('/scoreboard;week=6' in x for x in calls))
    def test_missing_summary_is_repaired_and_repeat_evidence_is_noop(self):
        m=self.mod();r=m.collect('waivers',root=self.root,now=NOW,week=7);p=m.publish(r,root=self.root)
        before=p.read_bytes();p.with_suffix('.md').unlink();m.publish(r,root=self.root)
        self.assertTrue(p.with_suffix('.md').exists());m.publish(r,root=self.root);self.assertEqual(p.read_bytes(),before)
    def test_repeated_matchups_are_not_full_scoreboard(self):
        m=self.mod();match={'teams':[{'code':'JD','points':120},{'code':'JU','points':152}]}
        self.assertFalse(m.full_scoreboard([match]*6,['BE','MC','VV','TM','SR','MN','ANT','MM','ME','JD','JU','JP']))
    def test_connected_jd_budget_does_not_replace_complete_league_budgets(self):
        self.save('data/yahoo_api/latest.json',self.api())
        self.save('intelligence/yahoo/test-authenticated-readback.json',{'league':'sparta','yahoo_league_id':'102586','season':2026,'completed':True,'source':'Authenticated Yahoo connector','observed_at_utc':'2026-10-20T12:30:00Z','current_faab':None})
        r=self.mod().collect('waivers',root=self.root,now=NOW,week=7)
        self.assertEqual(len(r['sections']['faab']['data']),12);self.assertEqual(r['sections']['faab']['data']['JD'],33)
    def test_weekly_sync_keeps_canonical_and_authoritative_files_unchanged(self):
        import yahoo_sync
        from yahoo_fixtures import write_fixtures
        shutil.copytree(ROOT/'data',self.root/'data',dirs_exist_ok=True)
        fx=write_fixtures(self.root/'fixtures')
        shutil.copy(fx/'teams_roster.xml',fx/'teams_roster_players_stats.xml')
        canonical=self.save('data/yahoo_api/latest.json',{'sentinel':'current feed'})
        protected=['transactions.json','current_roster_jd.json','faab.json','waiver_state.json']
        before={p:(self.root/'data'/p).read_bytes() for p in protected}
        result=yahoo_sync.run(yahoo_sync.FixtureClient(fx),root=self.root,coverage_week=6)
        self.assertEqual(result['snapshot']['coverage_week'],6)
        self.assertEqual(json.loads(canonical.read_text()),{'sentinel':'current feed'})
        self.assertTrue((self.root/'data/yahoo_api/weekly/2026-w06/latest.json').exists())
        for p,raw in before.items():self.assertEqual((self.root/'data'/p).read_bytes(),raw)
