"""Offline regressions for safe diagnostics and HTTP200 provider failure stops."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import fantasypros_ingest as ingest
from fantasypros_contract import validate_response
from fantasypros_fixtures import fixture
from test_fantasypros_ingest import Response

class DiagnosticsTests(unittest.TestCase):
    def test_schema_failure_reports_schema_path_without_values(self):
        data=fixture(); data['players'][0]['rank_ecr']={'private-key':'private-value'}
        with self.assertRaises(ValueError) as caught: validate_response('consensus',data)
        diagnostics=getattr(caught.exception,'diagnostics',[])
        self.assertTrue(diagnostics)
        text=json.dumps(diagnostics)
        self.assertIn('rank_ecr',text)
        self.assertNotIn('private-key',text)
        self.assertNotIn('private-value',text)
        self.assertIn('type',text)

    def test_credential_echo_has_no_schema_diagnostics(self):
        data=fixture(); data['players'][0]['rank_ecr']='private-api-key'
        with self.assertRaises(ingest.IngestionError) as caught:
            ingest.fetch('consensus',2026,6,'private-api-key',opener=lambda *a,**k:Response(data))
        self.assertEqual(getattr(caught.exception,'diagnostics',[]),[])
        self.assertTrue(getattr(caught.exception,'stop_pilot',False))

    def test_error_envelopes_stop_after_one_request_and_preserve_safe_audit(self):
        for body in ({'error':'quota exceeded private-text'}, {'message':'Invalid API key'},
                     {'status':'error','message':'Subscription does not include this endpoint'},
                     {'status':False,'errors':['not entitled']}, {'code':429,'message':'limit reached'}, {'status':429}, {'status':403},
                     {'code':200,'status_code':401}, {'code':200,'status':429}):
            calls=[]
            def opener(*a,**k): calls.append(1); return Response(body)
            real_fetch=ingest.fetch
            def fetched(*a,**k): return real_fetch(*a,**k,opener=opener)
            with self.subTest(body=body), tempfile.TemporaryDirectory() as tmp, patch.dict(ingest.os.environ,{'FANTASYPROS_API_KEY':'synthetic-key'}), patch.object(ingest,'fetch',side_effect=fetched), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                audit=Path(tmp)/'audit.json'
                result=ingest.main(['--week','6','--output-dir',tmp,'--audit-summary',str(audit),'--credential-rotated','--request-budget','3'])
                self.assertEqual(result,1)
                self.assertEqual(len(calls),1)
                report=json.loads(audit.read_text())
                self.assertEqual(report['endpoints'][0]['http_status'],200)
                self.assertEqual(report['endpoints'][0]['failure_category'],'PROVIDER_ERROR_ENVELOPE')
                self.assertEqual(report['endpoints'][0]['schema_validation'],'NOT_REACHED')
                self.assertIn(report['endpoints'][0]['diagnostics'][0]['provider_error_type'], ['QUOTA_OR_RATE_LIMIT','AUTHENTICATION','ENTITLEMENT'])
                self.assertEqual(report['endpoints'][1]['status'],'NOT_REQUESTED')
                self.assertNotIn('private-text',audit.read_text())
                self.assertFalse(list(Path(tmp).glob('fantasypros_batch_*')))

    def test_schema_failure_retains_diagnostics_through_fetch(self):
        data=fixture(); data['players'][0]['rank_ecr']={}
        with self.assertRaises(ingest.IngestionError) as caught:
            ingest.fetch('consensus',2026,6,'synthetic-key',opener=lambda *a,**k:Response(data))
        self.assertEqual(getattr(caught.exception,'failure_category',None),'OPENAPI_SCHEMA_MISMATCH')
        self.assertTrue(getattr(caught.exception,'diagnostics',[]))
        self.assertFalse(getattr(caught.exception,'stop_pilot',True))
