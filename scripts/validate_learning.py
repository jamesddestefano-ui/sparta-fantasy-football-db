from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEARNING = ROOT / "learning"
LEDGER = LEARNING / "decision_ledger.jsonl"

REQUIRED = ["decision_id","system","timestamp_et","week","decision_type","subject","recommendation","confidence","urgency","decision_deadline","information_available_at_decision","key_supporting_signals","key_risk_factors","alternative_considered","actual_user_action","final_pre_deadline_state","outcome","outcome_grade","process_grade","result_notes","error_category","lesson","future_rule_adjustment","reviewed_at"]
EVENT_TYPES = {"DECISION", "DECISION_SCHEMA_SUPPLEMENT", "OUTCOME_REVIEW"}
URGENCY = {"LOW", "MEDIUM", "HIGH", "IMMEDIATE"}
GRADES = {"A", "B", "C", "D", "F", None}


def load_json(path: Path):
    return json.loads(path.read_text())


def main() -> None:
    errors: list[str] = []
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
            errors.append(f"missing learning artifact: {path.relative_to(ROOT)}")

    decisions: set[str] = set()
    if LEDGER.exists():
        for line_number, raw in enumerate(LEDGER.read_text().splitlines(), 1):
            if not raw.strip():
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError as exc:
                errors.append(f"ledger line {line_number}: invalid JSON: {exc}")
                continue
            missing = [field for field in REQUIRED if field not in event]
            if missing:
                errors.append(f"ledger line {line_number}: missing {missing}")
            if event.get("system") != "PRIME_SPARTA_FANTASY_WATCH":
                errors.append(f"ledger line {line_number}: wrong system")
            if event.get("event_type") not in EVENT_TYPES:
                errors.append(f"ledger line {line_number}: invalid event_type")
            if event.get("confidence") not in range(1, 6):
                errors.append(f"ledger line {line_number}: confidence must be 1-5")
            if event.get("urgency") not in URGENCY:
                errors.append(f"ledger line {line_number}: invalid urgency")
            if event.get("outcome_grade") not in GRADES or event.get("process_grade") not in GRADES:
                errors.append(f"ledger line {line_number}: invalid grade")
            decision_id = event.get("decision_id")
            if event.get("event_type") == "DECISION":
                if decision_id in decisions:
                    errors.append(f"ledger line {line_number}: duplicate DECISION id")
                decisions.add(decision_id)
            elif decision_id not in decisions:
                errors.append(f"ledger line {line_number}: review/supplement precedes DECISION")

    for name in ["signal_performance.json", "confidence_calibration.json", "season_scorecard.json"]:
        path = LEARNING / name
        if path.exists() and load_json(path).get("system") != "PRIME_SPARTA_FANTASY_WATCH":
            errors.append(f"{name}: wrong system")

    rules_path = LEARNING / "rules" / "learning_rules_v1.json"
    if rules_path.exists():
        rules_data = load_json(rules_path)
        if rules_data.get("version") != "learning_rules_v1":
            errors.append("learning rules version mismatch")
        for rule in rules_data.get("rules", []):
            for field in ["date", "old_rule", "new_rule", "reason", "supporting_decisions", "sample_size", "expected_effect"]:
                if field not in rule:
                    errors.append(f"rule {rule.get('rule_id')}: missing {field}")

    if errors:
        raise SystemExit("SPARTA LEARNING VALIDATION FAILED:\n- " + "\n- ".join(errors))
    print(f"SPARTA LEARNING VALIDATION PASSED decisions={len(decisions)}")


if __name__ == "__main__":
    main()
