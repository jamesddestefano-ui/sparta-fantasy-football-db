import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_learning.py"


class LearningValidatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(ROOT / "learning", self.tmp / "learning")
        self.ledger = self.tmp / "learning" / "decision_ledger.jsonl"

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_validator(self):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.tmp / "learning")],
                              capture_output=True, text=True)

    def append(self, obj):
        with open(self.ledger, "a") as fh:
            fh.write(json.dumps(obj) + "\n")

    def test_current_ledger_passes_with_grandfathered_warnings(self):
        out = self.run_validator()
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("grandfathered_warnings=4", out.stdout)

    def test_new_incomplete_decision_fails(self):
        self.append({"event_type": "DECISION", "decision_id": "NEW-BAD-1",
                     "system": "SPARTA_BRAIN_CONTROL_ROOM", "recommendation": "add X"})
        out = self.run_validator()
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("NEW-BAD-1", out.stdout + out.stderr)

    def test_complete_new_decision_passes_without_outcome_fields(self):
        self.append({"event_type": "DECISION", "decision_id": "NEW-GOOD-1",
                     "system": "SPARTA_BRAIN_CONTROL_ROOM", "timestamp_et": "2026-10-20T09:00:00-04:00",
                     "week": 7, "decision_type": "ADD_DROP", "subject": "Example", "recommendation": "Add",
                     "confidence": 3, "urgency": "MEDIUM", "decision_deadline": "2026-10-21T03:00:00-04:00",
                     "information_available_at_decision": [], "key_supporting_signals": [],
                     "key_risk_factors": [], "alternative_considered": "Hold"})
        out = self.run_validator()
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_review_before_decision_and_bad_grade_fail(self):
        self.append({"event_type": "OUTCOME_REVIEW", "decision_id": "NOPE", "system": "PRIME_SPARTA_FANTASY_WATCH",
                     "outcome_grade": "Z", "process_grade": "B"})
        out = self.run_validator()
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("precedes its DECISION", out.stdout + out.stderr)
        self.assertIn("invalid grade", out.stdout + out.stderr)

    def test_unknown_system_fails(self):
        self.append({"event_type": "DECISION", "decision_id": "MONGO-1", "system": "MONGO_BOT"})
        out = self.run_validator()
        self.assertIn("unknown system", out.stdout + out.stderr)


if __name__ == "__main__":
    unittest.main()
