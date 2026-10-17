"""Offline contract tests; no FantasyPros requests or credentials required."""
import io
import json
from pathlib import Path
import sys
import unittest
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from fantasypros_ingest import fetch, request_spec, IngestionError


class Response:
    def __init__(self, data):
        self.data = data
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def read(self, _max):
        return json.dumps(self.data).encode()


class ContractTests(unittest.TestCase):
    def test_sparta_scope_and_endpoint(self):
        for kind in ("consensus", "projections", "injuries"):
            path, params, expected = request_spec(kind, 2026, 6)
            self.assertTrue(path.startswith("/nfl/"))
            self.assertEqual(params["week"], "6")
            self.assertIn(expected, ("players", "injuries"))
        with self.assertRaises(ValueError):
            request_spec("unknown", 2026, 6)
        with self.assertRaises(ValueError):
            request_spec("consensus", 2025, 6)

    def test_valid_consensus_is_intelligence_only(self):
        def opener(req, timeout):
            self.assertEqual(req.get_header("X-api-key"), "dummy-secret")
            self.assertEqual(timeout, 15)
            return Response({"sport": "NFL", "season": "2026", "week": "6", "players": [{"player_name": "Test"}]})
        out = fetch("consensus", 2026, 6, "dummy-secret", opener=opener)
        self.assertEqual(out["record_count"], 1)
        self.assertEqual(out["authority"], "NFL_INTELLIGENCE_ONLY_NOT_YAHOO_OWNERSHIP")
        self.assertNotIn("dummy-secret", json.dumps(out))

    def test_reject_wrong_week(self):
        with self.assertRaisesRegex(IngestionError, "wrong week"):
            fetch("projections", 2026, 6, "secret", opener=lambda *_args, **_kw: Response({"sport":"NFL", "season":"2026", "week":"5", "players":[]}))

    def test_reject_wrong_sport_and_missing_list(self):
        for data in ({"sport":"NBA", "injuries":[]}, {"sport":"NFL", "injuries":{}}):
            with self.assertRaises(IngestionError):
                fetch("injuries", 2026, 6, "secret", opener=lambda *_args, **_kw: Response(data))

    def test_http_error_is_redacted(self):
        def opener(*_args, **_kwargs):
            raise HTTPError("https://api.fantasypros.com/", 401, "denied", {}, io.BytesIO(b"secret"))
        with self.assertRaises(IngestionError) as ctx:
            fetch("injuries", 2026, 6, "secret", opener=opener)
        self.assertIn("401", str(ctx.exception))
        self.assertNotIn("secret", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
