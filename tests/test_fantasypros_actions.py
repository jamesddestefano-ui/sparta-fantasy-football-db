import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))

class ActionsPreflightTests(unittest.TestCase):
    def test_secret_presence_never_implies_quota_or_rotation(self):
        from fantasypros_actions import preflight
        result=preflight('synthetic-secret','0','',False)
        self.assertTrue(result['secret_available'])
        self.assertFalse(result['live_permitted'])
        self.assertNotIn('synthetic-secret',str(result))

    def test_requires_exact_three_budget_evidence_and_rotated_attestation(self):
        from fantasypros_actions import preflight
        for budget,evidence,rotated in [('2','verified',True),('3','',True),('3','verified',False),('bad','verified',True)]:
            with self.subTest(budget=budget,evidence=evidence,rotated=rotated):
                self.assertFalse(preflight('synthetic-secret',budget,evidence,rotated)['live_permitted'])
        self.assertTrue(preflight('synthetic-secret','3','provider dashboard checked',True)['live_permitted'])
        self.assertFalse(preflight('','3','provider dashboard checked',True)['live_permitted'])

if __name__=='__main__': unittest.main()

class ExplicitAuthorizationTests(unittest.TestCase):
    def test_user_authorization_permits_unknown_quota_without_claiming_verified(self):
        from fantasypros_actions import preflight
        result=preflight('synthetic-secret','3','',True,authorized_unknown_quota=True)
        self.assertTrue(result['live_permitted'])
        self.assertFalse(result['quota_confirmed'])
        self.assertTrue(result['user_authorized_unknown_quota'])
        self.assertFalse(preflight('synthetic-secret','0','',True,authorized_unknown_quota=True)['live_permitted'])
