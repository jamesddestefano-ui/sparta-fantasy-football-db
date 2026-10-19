"""Mutation tests: baseline counts cannot conceal changed evidence or new defects."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class LearningRegressionGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for folder in ('learning','scripts','ci'):
            shutil.copytree(ROOT/folder,self.root/folder)
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        self.commit()

    def commit(self):
        subprocess.run(['git','-C',str(self.root),'add','.'],check=True)
        subprocess.run(['git','-C',str(self.root),'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','trusted previous state'],check=True)
        self.ref=subprocess.check_output(['git','-C',str(self.root),'rev-parse','HEAD'],text=True).strip()

    def gate(self):
        path=ROOT/'scripts/learning_regression_gate.py'
        self.assertTrue(path.exists(),'regression-aware integrity gate is missing')
        spec=importlib.util.spec_from_file_location('gate',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        return m.evaluate(self.root,comparison_ref=self.ref)

    def append(self,obj):
        with (self.root/'learning/decision_ledger.jsonl').open('a') as f:f.write(json.dumps(obj)+'\n')

    def test_baseline_reports_every_historical_error_and_passes_current_rules(self):
        r=self.gate();self.assertTrue(r['passed'],r);self.assertEqual(len(r['historical_errors']),653)
        self.assertEqual(len(r['current_warnings']),4)

    def test_same_error_count_historical_reasoning_edit_fails(self):
        p=self.root/'learning/decision_ledger.jsonl';s=p.read_text();p.write_text(s.replace('recommendation','recommendatioN',1))
        self.assertFalse(self.gate()['passed'])

    def test_historical_truncation_fails(self):
        p=self.root/'learning/decision_ledger.jsonl';p.write_bytes(p.read_bytes()[:-1]);self.assertFalse(self.gate()['passed'])

    def test_new_incomplete_decision_fails(self):
        self.append({'event_type':'DECISION','decision_id':'NEW-BAD','system':'SPARTA_BRAIN_CONTROL_ROOM'})
        self.assertFalse(self.gate()['passed'])

    def test_reusing_grandfathered_id_cannot_hide_new_review_error(self):
        self.append({'event_type':'OUTCOME_REVIEW','decision_id':'SPARTA-2026W4-HALL-Q-TO-D-20260930-1600','system':'SPARTA_LIVE_CHECK','outcome_grade':'Z','process_grade':'B'})
        self.assertFalse(self.gate()['passed'])

    def test_exception_expansion_fails(self):
        p=self.root/'learning/ledger_exceptions.json';v=json.loads(p.read_text());v['grandfathered'].append({'decision_id':'NEW-BAD','reason':'bypass'})
        p.write_text(json.dumps(v));self.assertFalse(self.gate()['passed'])

    def test_baseline_tampering_fails(self):
        p=self.root/'ci/baselines/learning-2026-10-19.json';v=json.loads(p.read_text());v['historical_errors']=[];p.write_text(json.dumps(v))
        self.assertFalse(self.gate()['passed'])

    def test_validator_weakening_fails(self):
        p=self.root/'scripts/validate_learning.py';p.write_text('print("PASS")\n');self.assertFalse(self.gate()['passed'])

    def test_lineage_history_change_fails(self):
        p=self.root/'learning/pulse_decision_lineage.jsonl';p.write_bytes(b'{}\n'+p.read_bytes());self.assertFalse(self.gate()['passed'])

    def test_valid_new_decision_passes_without_historical_outcome_backfill(self):
        self.append({'event_type':'DECISION','decision_id':'NEW-GOOD','system':'SPARTA_BRAIN_CONTROL_ROOM','timestamp_et':'2026-10-20T09:00:00-04:00','week':7,'decision_type':'ADD_DROP','subject':'Example','recommendation':'Hold','confidence':3,'urgency':'MEDIUM','decision_deadline':None,'information_available_at_decision':[],'key_supporting_signals':[],'key_risk_factors':[],'alternative_considered':'Wait'})
        self.assertTrue(self.gate()['passed'])

    def test_new_lineage_defect_fails(self):
        with (self.root/'learning/pulse_decision_lineage.jsonl').open('a') as f:f.write('{}\n')
        self.assertFalse(self.gate()['passed'])

    def test_boolean_confidence_cannot_pass_as_integer(self):
        self.append({'event_type':'DECISION','decision_id':'BOOL-CONFIDENCE','system':'SPARTA_BRAIN_CONTROL_ROOM','timestamp_et':'2026-10-20T09:00:00-04:00','week':7,'decision_type':'ADD_DROP','subject':'Example','recommendation':'Hold','confidence':True,'urgency':'MEDIUM','decision_deadline':None,'information_available_at_decision':[],'key_supporting_signals':[],'key_risk_factors':[],'alternative_considered':'Wait'})
        self.assertFalse(self.gate()['passed'])

    def test_valid_review_of_historical_exception_is_not_blocked(self):
        self.append({'event_type':'OUTCOME_REVIEW','decision_id':'SPARTA-2026W4-HALL-Q-TO-D-20260930-1600','system':'SPARTA_LIVE_CHECK','outcome_grade':'B','process_grade':'B'})
        self.assertTrue(self.gate()['passed'])

    def test_future_merged_event_cannot_be_edited_or_deleted(self):
        original=(self.root/'learning/decision_ledger.jsonl').read_bytes()
        self.append({'type':'PULSE_CONSUME','at_et':'2026-10-20T09:00:00-04:00','summary':'original evidence'})
        self.commit()
        self.assertTrue(self.gate()['passed'])
        p=self.root/'learning/decision_ledger.jsonl';accepted=p.read_bytes()
        p.write_bytes(accepted.replace(b'original evidence',b'changed evidence'))
        self.assertFalse(self.gate()['passed'])
        p.write_bytes(original)
        self.assertFalse(self.gate()['passed'])

    def test_frozen_653_inventory_reproduces_from_original_git_commit(self):
        import io
        import tarfile
        import hashlib
        baseline=json.loads((ROOT/'ci/baselines/learning-2026-10-19.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            raw=subprocess.check_output(['git','archive',baseline['historical_commit'],'learning','scripts/validate_learning.py'],cwd=ROOT)
            with tarfile.open(fileobj=io.BytesIO(raw)) as archive: archive.extractall(tmp,filter='data')
            script=Path(tmp)/'scripts/validate_learning.py'
            self.assertEqual(hashlib.sha256(script.read_bytes()).hexdigest(),baseline['historical_validator_sha256'])
            out=subprocess.run(['python',str(script)],capture_output=True,text=True)
            self.assertEqual(out.returncode,1)
            errors=[s[2:] for s in (out.stdout+out.stderr).splitlines() if s.startswith('- ')]
            self.assertEqual(errors,baseline['historical_errors'])

    def test_current_brain_actor_allowed_by_new_main_governance(self):
        self.append({'event_type':'DECISION','decision_id':'NEW-BRAIN','system':'CLAUDE_SPARTA_BRAIN','timestamp_et':'2026-10-20T09:00:00-04:00','week':7,'decision_type':'ADD_DROP','subject':'Example','recommendation':'Hold','confidence':3,'urgency':'MEDIUM','decision_deadline':None,'information_available_at_decision':[],'key_supporting_signals':[],'key_risk_factors':[],'alternative_considered':'Wait'})
        self.assertTrue(self.gate()['passed'])
