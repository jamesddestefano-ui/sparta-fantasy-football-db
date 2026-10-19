"""Validate Sparta learning artifacts without rewriting history.

The decision ledger (learning/decision_ledger.jsonl) holds two kinds of lines:

* Decision events (have `event_type`): DECISION, DECISION_SCHEMA_SUPPLEMENT,
  OUTCOME_REVIEW. Validated against AGENTS.md rules 39-43: decision-time fields
  are required at DECISION time; outcome fields are appended later (rule 40), so
  they are optional on DECISION but must be well-formed when present.
* Operational log lines: entries with `type` (PULSE_CONSUME, live_check_quiet, ...)
  and Watch alert-triage entries with `decision` + `ts_et` (WAKE_/SUPPRESS_...).
  These are not decisions; they are counted and shape-checked only.

Historical records are immutable (rules 48, 52). Records that predate this
validator and cannot be completed are listed by decision_id, with a reason, in
learning/ledger_exceptions.json and reported as warnings instead of errors.
Any NEW malformed record still fails validation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEARNING = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "learning"
LEDGER = LEARNING / "decision_ledger.jsonl"
EXCEPTIONS = LEARNING / "ledger_exceptions.json"

# AGENTS.md rule 16: Brain (Claude since 2026-10-19; ChatGPT control room before), Watch, live checks.
SYSTEMS = {"PRIME_SPARTA_FANTASY_WATCH", "SPARTA_BRAIN_CONTROL_ROOM", "SPARTA_LIVE_CHECK", "CLAUDE_SPARTA_BRAIN"}
DECISION_TIME_FIELDS = [
    "decision_id", "system", "timestamp_et", "week", "decision_type", "subject", "recommendation",
    "confidence", "urgency", "decision_deadline", "information_available_at_decision",
    "key_supporting_signals", "key_risk_factors", "alternative_considered",
]
OUTCOME_FIELDS = [
    "actual_user_action", "final_pre_deadline_state", "outcome", "outcome_grade", "process_grade",
    "result_notes", "error_category", "lesson", "future_rule_adjustment", "reviewed_at",
]
EVENT_TYPES = {"DECISION", "DECISION_SCHEMA_SUPPLEMENT", "OUTCOME_REVIEW"}
URGENCY = {"LOW", "MEDIUM", "HIGH", "IMMEDIATE"}
GRADES = {"A", "B", "C", "D", "F", None}
OPS_TIME_FIELDS = ("at_et", "ts_et", "timestamp_et", "observed_at", "recorded_at_et")


def load_json(path: Path):
    return json.loads(path.read_text())


def check_decision_event(event: dict, decisions: set[str]) -> list[str]:
    problems: list[str] = []
    etype = event.get("event_type")
    did = event.get("decision_id")
    if etype not in EVENT_TYPES:
        return [f"invalid event_type {etype!r}"]
    if event.get("system") not in SYSTEMS:
        problems.append(f"unknown system {event.get('system')!r}")
    if not did:
        problems.append("missing decision_id")

    if etype == "DECISION":
        missing = [f for f in DECISION_TIME_FIELDS if f not in event]
        if missing:
            problems.append(f"missing decision-time fields {missing}")
        if "confidence" in event and event.get("confidence") not in range(1, 6):
            problems.append("confidence must be 1-5")
        if "urgency" in event and event.get("urgency") not in URGENCY:
            problems.append("invalid urgency")
    else:
        if did not in decisions:
            problems.append(f"{etype} precedes its DECISION")
        if etype == "OUTCOME_REVIEW":
            if event.get("confidence") not in (None, *range(1, 6)):
                problems.append("confidence must be 1-5 when present")
            if "outcome_grade" not in event or "process_grade" not in event:
                problems.append("OUTCOME_REVIEW needs outcome_grade and process_grade")

    if event.get("outcome_grade") not in GRADES or event.get("process_grade") not in GRADES:
        problems.append("invalid grade (A-F or null)")
    return problems


def main() -> None:
    errors: list[str] = []
    warnings: list[str] = []
    required_files = [
        LEARNING / "schema" / "decision_event.schema.json",
        LEARNING / "signal_performance.json",
        LEARNING / "confidence_calibration.json",
        LEARNING / "season_scorecard.json",
        LEARNING / "rules" / "learning_rules_v1.json",
        LEARNING / "weekly" / "README.md",
        LEDGER,
    ]
    for path in required_files:
        if not path.exists():
            errors.append(f"missing learning artifact: {path.name}")

    exceptions = {}
    if EXCEPTIONS.exists():
        exceptions = {e["decision_id"]: e for e in load_json(EXCEPTIONS).get("grandfathered", [])}

    decisions: set[str] = set()
    counts = {"DECISION": 0, "OUTCOME_REVIEW": 0, "DECISION_SCHEMA_SUPPLEMENT": 0, "operational": 0}
    unreviewed: list[str] = []
    reviewed: set[str] = set()
    if LEDGER.exists():
        for n, raw in enumerate(LEDGER.read_text().splitlines(), 1):
            if not raw.strip():
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError as exc:
                errors.append(f"ledger line {n}: invalid JSON: {exc}")
                continue

            if "event_type" in event:
                problems = check_decision_event(event, decisions)
                did = event.get("decision_id")
                if problems:
                    target = warnings if did in exceptions else errors
                    tag = " (grandfathered: " + exceptions[did]["reason"] + ")" if did in exceptions else ""
                    target.append(f"ledger line {n} [{did}]: " + "; ".join(problems) + tag)
                etype = event["event_type"]
                counts[etype] = counts.get(etype, 0) + 1
                if etype == "DECISION":
                    if did in decisions:
                        errors.append(f"ledger line {n}: duplicate DECISION id {did}")
                    decisions.add(did)
                    if event.get("outcome_grade") is not None or event.get("reviewed_at"):
                        reviewed.add(did)
                elif etype == "OUTCOME_REVIEW":
                    reviewed.add(did)
            elif "type" in event or ("decision" in event and any(event.get(f) for f in OPS_TIME_FIELDS)):
                # operational log: pulse consumption, live checks, Watch alert triage (wake/suppress)
                counts["operational"] += 1
                if not any(event.get(f) for f in OPS_TIME_FIELDS):
                    errors.append(f"ledger line {n}: operational entry has no timestamp")
            else:
                errors.append(f"ledger line {n}: neither a decision event (event_type) nor an operational entry (type)")

    unreviewed = sorted(decisions - reviewed)
    stale = [d for d in exceptions if d not in decisions]
    if stale:
        warnings.append(f"ledger_exceptions.json lists ids not in ledger: {stale}")

    for name in ["signal_performance.json", "confidence_calibration.json", "season_scorecard.json"]:
        path = LEARNING / name
        if path.exists() and load_json(path).get("system") not in SYSTEMS:
            errors.append(f"{name}: unknown system")

    rules_path = LEARNING / "rules" / "learning_rules_v1.json"
    if rules_path.exists():
        rules_data = load_json(rules_path)
        if rules_data.get("version") != "learning_rules_v1":
            errors.append("learning rules version mismatch")
        for rule in rules_data.get("rules", []):
            for field in ["date", "old_rule", "new_rule", "reason", "supporting_decisions", "sample_size", "expected_effect"]:
                if field not in rule:
                    errors.append(f"rule {rule.get('rule_id')}: missing {field}")

    for w in warnings:
        print("WARNING: " + w)
    if errors:
        raise SystemExit("SPARTA LEARNING VALIDATION FAILED:\n- " + "\n- ".join(errors))
    print(f"SPARTA LEARNING VALIDATION PASSED decisions={counts['DECISION']} "
          f"outcome_reviews={counts['OUTCOME_REVIEW']} supplements={counts['DECISION_SCHEMA_SUPPLEMENT']} "
          f"operational_entries={counts['operational']} awaiting_review={len(unreviewed)} "
          f"grandfathered_warnings={len(warnings)}")


if __name__ == "__main__":
    main()
