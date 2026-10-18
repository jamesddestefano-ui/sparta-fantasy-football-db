import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from fantasypros_contract import validate_request,validate_response,PATHS
from fantasypros_fixtures import fixture
from fantasypros_ingest import fetch,request_spec,IngestionError
from test_fantasypros_ingest import Response

class SuppliedContractTests(unittest.TestCase):
    def test_all_seven_response_contracts_and_missing_required_fields(self):
        for kind in PATHS:
            with self.subTest(kind=kind):
                data=fixture(kind); validate_response(kind,data)
                required=next(iter(data));del data[required]
                with self.assertRaises(ValueError): validate_response(kind,data)

    def test_projection_request_includes_required_position(self):
        path,params,_=request_spec('projections',2026,6)
        self.assertEqual(params['position'],'WR')
        validate_request('projections',2026,params)

    def test_documented_projection_ppr_selected_from_stats_not_std_points(self):
        out=fetch('projections',2026,6,'synthetic-api-key',opener=lambda *a,**k:Response(fixture('projections')))
        self.assertEqual(out['normalized_players'][0]['projected_points_ppr'],12)
        self.assertEqual(out['normalized_players'][0]['fantasypros_id'],'1')
        self.assertEqual(out['scoring'],'PPR')
        self.assertEqual(out['contract_status'],'VALIDATED_SUPPLIED_OPENAPI')

    def test_documented_ranking_identity_and_epoch_timestamp(self):
        out=fetch('consensus',2026,6,'synthetic-api-key',opener=lambda *a,**k:Response(fixture()))
        self.assertEqual(out['yahoo_id_mapping'],{'10':'1'})
        self.assertEqual(out['normalized_players'][0]['position'],'WR')
        self.assertTrue(out['provider_timestamps'])

    def test_all_endpoint_requests_and_ingestion_adapters(self):
        for kind in PATHS:
            with self.subTest(kind=kind):
                kw={'player_ids':'1:2'} if kind=='compare' else {}
                path,params,expected=request_spec(kind,2026,6,**kw)
                self.assertEqual(path,validate_request(kind,2026,params))
                out=fetch(kind,2026,6,'synthetic-api-key',opener=lambda *a,**k:Response(fixture(kind)),**kw)
                self.assertGreater(out['record_count'],0)
                self.assertEqual(out['contract_status'],'VALIDATED_SUPPLIED_OPENAPI')

    def test_ros_uses_documented_boolean_parameter(self):
        _,params,_=request_spec('projections_ros',2026,6)
        self.assertEqual(params['ros'],'true')
        out=fetch('projections_ros',2026,6,'synthetic-api-key',opener=lambda *a,**k:Response(fixture('projections')))
        self.assertEqual(out['scope'],'rest_of_season')

    def test_projection_rejects_missing_or_ambiguous_ppr_values(self):
        for mutation in ('missing','ambiguous'):
            data=fixture('projections')
            if mutation=='missing': del data['players'][0]['stats'][0]['points_ppr']
            else:
                other=dict(data['players'][0]['stats'][0],points_ppr=99)
                data['players'][0]['stats'].append(other)
            with self.subTest(mutation=mutation),self.assertRaises(IngestionError):
                fetch('projections',2026,6,'synthetic-api-key',opener=lambda *a,**k:Response(data))

    def test_unknown_parameter_rejected(self):
        with self.assertRaises(ValueError): validate_request('news',2026,{'week':'6'})

if __name__=='__main__':unittest.main()
