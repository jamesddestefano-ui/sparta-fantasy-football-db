import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import pulse_guard as pg  # noqa: E402


def p(ts, n=0):
    return json.dumps({"product": "LOCK Pulse", "completedAt": ts, "itemCount": n})


class PulseGuardTests(unittest.TestCase):
    def test_stale_latest_is_restored(self):
        base, stale = p("2026-10-22T13:29:47.000Z"), p("2026-10-19T13:09:52.250Z")
        self.assertEqual(pg.repair_latest(base, stale), base)

    def test_newer_latest_is_kept(self):
        base, newer = p("2026-10-22T12:18:02.000Z"), p("2026-10-22T13:29:47.000Z")
        self.assertIsNone(pg.repair_latest(base, newer))

    def test_append_only_history_untouched(self):
        base = "\n".join([p("a"), p("b")]) + "\n"
        cur = base + p("c") + "\n"
        self.assertIsNone(pg.repair_history(base, cur))

    def test_wiped_history_is_rebuilt_without_duplicates(self):
        base = "\n".join([p("2026-10-19T13:09:52.250Z"), p("2026-10-22T13:29:47.000Z")]) + "\n"
        wiped = p("2026-10-19T13:09:52.250Z", 14) + "\n"  # mirror rewrote file to its one stale pass
        out = pg.repair_history(base, wiped)
        self.assertEqual(out, base)

    def test_new_pass_in_wiped_file_is_appended(self):
        base = p("a") + "\n"
        cur = p("b") + "\n"
        self.assertEqual(pg.repair_history(base, cur), p("a") + "\n" + p("b") + "\n")

    def test_restored_history_is_not_reordered_against_a_wiped_base(self):
        wiped = p("2026-10-19T13:09:52.250Z") + "\n"
        full = "\n".join([p("2026-10-18T18:09:49.079Z"), p("2026-10-19T13:09:52.250Z"), p("2026-10-22T13:29:47.000Z")]) + "\n"
        self.assertIsNone(pg.repair_history(wiped, full))

    def test_non_json_junk_lines_are_removed(self):
        good = p("a") + "\n" + p("b") + "\n"
        junk = "PLACEHOLDER_FOR_FULL_HISTORY_WITH_APPEND\n" + p("a") + "\n$(cat /tmp/history.jsonl)\n" + p("b") + "\n"
        self.assertEqual(pg.repair_history(good, junk), good)
        self.assertEqual(pg.repair_history(None, junk), good)

    def test_latest_pass_is_appended_once(self):
        latest = json.dumps({"product": "LOCK Pulse", "status": "live", "completedAt": "c"})
        hist = p("a") + "\n"
        out = pg.append_latest(latest, hist)
        self.assertEqual(out.splitlines()[-1], json.dumps(json.loads(latest), separators=(",", ":")))
        self.assertIsNone(pg.append_latest(latest, out))

    def test_non_live_latest_is_not_appended(self):
        seeded = json.dumps({"product": "LOCK Pulse", "status": "seeded", "completedAt": "c"})
        self.assertIsNone(pg.append_latest(seeded, p("a") + "\n"))


if __name__ == "__main__":
    unittest.main()
