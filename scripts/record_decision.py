"""Append Brain decisions and outcome reviews to learning/decision_ledger.jsonl safely.

Used by Claude's scheduled Sparta sessions (docs/brain_playbook.md). Never edits
existing lines (AGENTS.md rules 48, 52); appends one validated event and re-runs
the learning validator, rolling back the append if validation fails.

  python scripts/record_decision.py decision path/to/decision.json
  python scripts/record_decision.py review   path/to/review.json
  python scripts/record_decision.py open --week 7      # list DECISIONs with no OUTCOME_REVIEW yet

decision.json needs: decision_id, week, decision_type, subject, recommendation,
confidence (1-5), urgency, decision_deadline, information_available_at_decision,
key_supporting_signals, key_risk_factors, alternative_considered.
review.json needs: decision_id, actual_user_action, outcome, outcome_grade,
process_grade, result_notes, error_category, lesson, future_rule_adjustment.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from yahoo_parse import ET_TZ  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "learning" / "decision_ledger.jsonl"
SYSTEM = "CLAUDE_SPARTA_BRAIN"
REVIEW_FIELDS = ["actual_user_action", "outcome", "outcome_grade", "process_grade", "result_notes",
                 "error_category", "lesson", "future_rule_adjustment"]


def now_et() -> str:
    return datetime.now(ET_TZ).replace(microsecond=0).isoformat()


def load_events(ledger: Path = LEDGER) -> list[dict]:
    return [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]


def _append_validated(event: dict, ledger: Path = LEDGER) -> None:
    before = ledger.read_text()
    with open(ledger, "a") as fh:
        if before and not before.endswith("\n"):
            fh.write("\n")
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    out = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate_learning.py"), str(ledger.parent)],
                         capture_output=True, text=True)
    if out.returncode != 0:
        ledger.write_text(before)
        raise SystemExit("REJECTED (ledger unchanged):\n" + (out.stdout + out.stderr)[-1500:])


def record_decision(d: dict, ledger: Path = LEDGER) -> dict:
    existing = {e.get("decision_id") for e in load_events(ledger) if e.get("event_type") == "DECISION"}
    if d.get("decision_id") in existing:
        raise SystemExit(f"decision_id {d['decision_id']} already recorded; decisions are immutable")
    event = {"event_type": "DECISION", "record_version": 3, "system": SYSTEM, "timestamp_et": now_et(),
             "pulse_used": False, **d}
    event["system"] = SYSTEM
    _append_validated(event, ledger)
    return event


def record_review(r: dict, ledger: Path = LEDGER) -> dict:
    events = load_events(ledger)
    if not any(e.get("event_type") == "DECISION" and e.get("decision_id") == r.get("decision_id") for e in events):
        raise SystemExit(f"no DECISION {r.get('decision_id')} to review")
    missing = [f for f in REVIEW_FIELDS if f not in r]
    if missing:
        raise SystemExit(f"review missing {missing}")
    event = {"event_type": "OUTCOME_REVIEW", "system": SYSTEM, "reviewed_at": now_et(), **r}
    event["system"] = SYSTEM
    _append_validated(event, ledger)
    return event


def open_decisions(week: int | None = None, ledger: Path = LEDGER) -> list[dict]:
    events = load_events(ledger)
    reviewed = {e.get("decision_id") for e in events if e.get("event_type") == "OUTCOME_REVIEW"}
    reviewed |= {e.get("decision_id") for e in events
                 if e.get("event_type") == "DECISION" and (e.get("outcome_grade") or e.get("reviewed_at"))}
    return [e for e in events if e.get("event_type") == "DECISION" and e.get("decision_id") not in reviewed
            and (week is None or e.get("week") == week)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("decision", "review"):
        sp = sub.add_parser(name)
        sp.add_argument("json_file")
    op = sub.add_parser("open")
    op.add_argument("--week", type=int)
    args = ap.parse_args(argv)
    if args.cmd == "open":
        for e in open_decisions(args.week):
            rec = e.get("recommendation")
            rec = rec.get("format") or rec.get("detail") if isinstance(rec, dict) else rec
            print(f"W{e.get('week')} {e['decision_id']} [{e.get('decision_type')}] conf={e.get('confidence')}: {str(rec)[:120]}")
        return 0
    payload = json.loads(Path(args.json_file).read_text())
    ev = record_decision(payload) if args.cmd == "decision" else record_review(payload)
    print(f"RECORDED {ev['event_type']} {ev['decision_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
