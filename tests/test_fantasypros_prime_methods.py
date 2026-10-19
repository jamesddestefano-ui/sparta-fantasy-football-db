"""Synthetic regressions inspired by reviewed PRIME engineering; no provider calls."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import fantasypros_contract as contract
import fantasypros_ingest as ingest
from fantasypros_fixtures import fixture
from test_fantasypros_ingest import Response

class PrimeMethodsTests(unittest.TestCase):
    def test_overflow_number_in_extra_field_is_rejected_during_decode(self):
        class Raw(Response):
            def read(self,_): return (json.dumps(fixture())[:-1]+',"unused":1e309}').encode()
        with self.assertRaises(ingest.IngestionError):
            ingest.fetch('consensus',2026,6,'synthetic-key',opener=lambda *a,**k:Raw(None))

    def test_pinned_contract_hash_mismatch_is_rejected(self):
        source=contract.ROOT/'contracts'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);shutil.copytree(source,root/'contracts')
            with (root/'contracts/fantasypros_public_v2.openapi.json').open('a') as f:f.write(' ')
            contract.document.cache_clear()
            try:
                with patch.object(contract,'ROOT',root),self.assertRaisesRegex(ValueError,'Pinned contract hash mismatch'):
                    contract.document()
            finally:contract.document.cache_clear()

    def test_receipt_is_measured_before_validation(self):
        first=datetime(2026,10,18,0,0,tzinfo=timezone.utc)
        later=datetime(2026,10,18,0,1,tzinfo=timezone.utc)
        class Clock(datetime):
            current=first
            @classmethod
            def now(cls,tz=None): return cls.current
        real_validate=ingest.validate_payload
        def validate(*args,**kwargs):
            Clock.current=later
            return real_validate(*args,**kwargs)
        with patch.object(ingest,'datetime',Clock),patch.object(ingest,'validate_payload',side_effect=validate):
            result=ingest.fetch('news',2026,6,'synthetic-key',opener=lambda *a,**k:Response(fixture('news')))
        self.assertEqual(result['retrieved_at_utc'],first.isoformat())
        self.assertEqual(result['response_received_at_utc'],result['retrieved_at_utc'])
        self.assertEqual(result['request_started_at_utc'],first.isoformat())

    def test_publication_is_per_item_and_never_inferred_from_receipt(self):
        for stamp,status,published in [('2026-10-17 20:45:47','UNKNOWN_TIMEZONE_OR_UNAVAILABLE',None),
                                       ('2026-10-17','UNKNOWN_TIMEZONE_OR_UNAVAILABLE',None),
                                       ('2026-10-17T20:45:47-04:00','AWARE_PROVIDER_TIMESTAMP','2026-10-18T00:45:47+00:00')]:
            data=fixture('news');data['items'][0]['created']=stamp
            with self.subTest(stamp=stamp):
                result=ingest.fetch('news',2026,6,'synthetic-key',opener=lambda *a,**k:Response(data))
                item=result['normalized_players'][0]
                self.assertEqual(item['provider_timestamps_raw']['created'],stamp)
                self.assertEqual(item['published_at_utc'],published)
                self.assertEqual(item['publication_time_status'],status)
                self.assertIsNone(result['provider_season'])
                self.assertEqual(result['requested_season'],2026)
                self.assertIsNone(result['provider_week'])
                self.assertEqual(result['requested_week'],6)

    def test_publication_conversion_overflow_is_safe_and_keeps_original(self):
        data=fixture('news');data['items'][0]['created']='0001-01-01T00:00:00+14:00'
        result=ingest.fetch('news',2026,6,'synthetic-key',opener=lambda *a,**k:Response(data))
        self.assertIsNone(result['normalized_players'][0]['published_at_utc'])
        self.assertEqual(result['normalized_players'][0]['provider_timestamps_raw']['created'],data['items'][0]['created'])

    def test_aggregate_ranking_update_is_not_player_publication(self):
        result=ingest.fetch('consensus',2026,6,'synthetic-key',opener=lambda *a,**k:Response(fixture()))
        self.assertIsNone(result['normalized_players'][0]['published_at_utc'])
        self.assertNotIn('last_updated_ts',result['normalized_players'][0]['provider_timestamps_raw'])
        self.assertTrue(any(x['field']=='last_updated_ts' for x in result['provider_timestamps']))
