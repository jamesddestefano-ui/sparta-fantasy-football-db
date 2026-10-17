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
            return Response({"sport": "NFL", "season": "2026", "week": "6", "scoring": "PPR", "players": [{"player_id": "1", "player_name": "Test", "player_position": "WR"}]})
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


class SafetyTests(unittest.TestCase):
    def payload(self):
        return {"season":2026,"week":6,"scoring":"PPR","players":[
            {"player_id":"1","player_name":"Test","player_position":"WR"}]}

    def get(self, data, **kwargs):
        return fetch("consensus",2026,6,"dummy-secret",opener=lambda *a, **k: Response(data), **kwargs)

    def test_reject_invalid_records(self):
        for rows in ([], [None], [{}], [{"player_id":"1","player_name":"Test","player_position":"BOGUS"}]):
            with self.subTest(rows=rows), self.assertRaises(IngestionError):
                self.get(dict(self.payload(), players=rows))

    def test_reject_wrong_or_missing_scoring(self):
        for scoring in (None,"HALF","STD"):
            with self.subTest(scoring=scoring), self.assertRaises(IngestionError):
                self.get(dict(self.payload(),scoring=scoring))

    def test_deduplicate_and_reject_conflicting_identity(self):
        data=self.payload(); data["players"] *= 2
        self.assertEqual(self.get(data)["record_count"],1)
        data["players"][1]=dict(data["players"][0], player_name="Other")
        with self.assertRaises(IngestionError): self.get(data)

    def test_reject_record_scope_conflicts(self):
        for fields in ({"week":5},{"season":2025},{"scoring":"STD"}):
            data=self.payload(); data["players"][0].update(fields)
            with self.subTest(fields=fields), self.assertRaises(IngestionError): self.get(data)

    def test_reject_credential_echo(self):
        data=self.payload(); data["message"]="dummy-secret"
        with self.assertRaises(IngestionError) as ctx: self.get(data)
        self.assertNotIn("dummy-secret",str(ctx.exception))

    def test_missing_timestamps_and_contract_are_explicit(self):
        out=self.get(self.payload())
        self.assertIn("PROVIDER_TIMESTAMP_MISSING",out["quality_flags"])
        self.assertEqual(out["contract_status"],"UNVERIFIED_OPENAPI_NOT_SUPPLIED")
        self.assertEqual(out["availability"],"UNKNOWN")

    def test_bounded_retry_and_no_auth_retry(self):
        calls=[]; sleeps=[]
        def opener(*a,**k):
            calls.append(1)
            if len(calls)==1: raise HTTPError("url",429,"limited",{"Retry-After":"2"},None)
            return Response(self.payload())
        out=fetch("consensus",2026,6,"dummy-secret",opener=opener,retries=1,sleep=sleeps.append)
        self.assertEqual(out["attempt_count"],2); self.assertEqual(sleeps,[2])
        calls.clear()
        def denied(*a,**k):
            calls.append(1); raise HTTPError("url",401,"secret",{},None)
        with self.assertRaises(IngestionError): fetch("consensus",2026,6,"dummy-secret",opener=denied,retries=2,sleep=sleeps.append)
        self.assertEqual(len(calls),1)

    def test_timestamp_invalid_stale_future(self):
        for stamp in ("nonsense","2000-01-01T00:00:00Z","2099-01-01T00:00:00Z"):
            with self.subTest(stamp=stamp), self.assertRaises(IngestionError):
                self.get(dict(self.payload(),updated_at=stamp))

    def test_publish_immutable_deduplicated_batch_and_isolation(self):
        import tempfile
        from fantasypros_ingest import publish_batch
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            record=self.get(self.payload())
            path=publish_batch([record],root)
            self.assertEqual(path,publish_batch([record],root))
            self.assertEqual(len(list(root.glob("*.json"))),1)
            self.assertEqual(json.loads(path.read_text())["records"][0]["record_count"],1)
        with self.assertRaises(IngestionError): publish_batch([record],Path(__file__).resolve().parents[1]/"data")


class PipelineTests(unittest.TestCase):
    def test_partial_batch_never_publishes(self):
        import tempfile
        from unittest.mock import patch
        import fantasypros_ingest as module
        with tempfile.TemporaryDirectory() as tmp, patch.dict(module.os.environ, {"FANTASYPROS_API_KEY":"synthetic-key"}), patch.object(module,"fetch",side_effect=[{"kind":"consensus"},IngestionError("failed")]):
            self.assertEqual(module.main(["--week","6","--output-dir",tmp]),1)
            self.assertEqual(list(Path(tmp).iterdir()),[])

    def test_reject_output_before_spending_requests(self):
        from unittest.mock import patch
        import fantasypros_ingest as module
        with patch.dict(module.os.environ,{"FANTASYPROS_API_KEY":"synthetic-key"}), patch.object(module,"fetch") as fetched:
            self.assertEqual(module.main(["--week","6","--output-dir",str(Path(module.__file__).resolve().parents[1]/"data")]),1)
            fetched.assert_not_called()

    def test_redirects_refused(self):
        from fantasypros_ingest import NoRedirect
        self.assertIsNone(NoRedirect().redirect_request(None,None,302,"redirect",{},"https://other.invalid"))

    def test_deep_json_is_safe_error(self):
        class RawResponse(Response):
            def read(self,_max): return b"["*1500+b"0"+b"]"*1500
        with self.assertRaises(IngestionError):
            fetch("consensus",2026,6,"dummy-key",opener=lambda *a,**k:RawResponse(None))


if __name__ == "__main__":
    unittest.main()
