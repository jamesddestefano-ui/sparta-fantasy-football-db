"""Full-suite workflows must retain evidence needed by historical audit tests."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WorkflowHistoryTests(unittest.TestCase):
    def test_full_suite_workflows_fetch_historical_evidence(self):
        for path in (ROOT / '.github/workflows').glob('*.yml'):
            text = path.read_text()
            if 'unittest discover -s tests' not in text:
                continue
            with self.subTest(workflow=path.name):
                checkout = text.split('uses: actions/checkout@', 1)[1].split('\n      - ', 1)[0]
                self.assertRegex(checkout, r'(?m)^\s+fetch-depth:\s+0(?:\s|$)',
                                 'The full suite must reproduce the pinned audit from Git history')
