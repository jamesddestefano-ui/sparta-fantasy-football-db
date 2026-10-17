"""Offline analytical checks; synthetic values are never live projections."""
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))

class EvaluationTests(unittest.TestCase):
    def row(self, **changes):
        return dict(dict(player_id='1',season=2026,week=6,scoring='PPR',fantasypros=10,
                         sparta=12,actual=14,lower=8,upper=16), **changes)

    def test_paired_metrics(self):
        from fantasypros_evaluate import evaluate
        result=evaluate([self.row(),self.row(player_id='2',fantasypros=8,sparta=6,actual=4,lower=5,upper=9)])
        self.assertEqual(result['sample_size'],2)
        self.assertEqual(result['fantasypros']['mae'],4)
        self.assertEqual(result['sparta']['mae'],2)
        self.assertEqual(result['interval_coverage'],0.5)
        self.assertEqual(result['pairwise_directional_accuracy'],1)
        self.assertFalse(result['promote_weights'])

    def test_reject_invalid_cohort(self):
        from fantasypros_evaluate import evaluate
        for changes in ({'scoring':'HALF'},{'fantasypros':None},{'actual':math.nan},{'week':19},{'lower':20},{'sparta':True}):
            with self.subTest(changes=changes),self.assertRaises(ValueError): evaluate([self.row(**changes)])
        with self.assertRaises(ValueError): evaluate([self.row(),self.row()])

    def test_empty_not_measurable(self):
        from fantasypros_evaluate import evaluate
        result=evaluate([])
        self.assertEqual(result['status'],'INSUFFICIENT_DATA')
        self.assertIsNone(result['fantasypros']['mae'])

    def test_comparison_preserves_provenance_and_missing_values(self):
        from fantasypros_evaluate import comparison
        root=Path(__file__).resolve().parents[1]
        result=comparison(root)
        self.assertEqual(result['status'],'BLOCKED_FANTASYPROS_DATA_MISSING')
        self.assertEqual(len(result['players']),2)
        self.assertTrue(result['source']['sha256'])
        self.assertIsNone(result['players'][0]['fantasypros_projection_ppr'])
        self.assertEqual(result['new_recommendation'],False)

if __name__=='__main__': unittest.main()
