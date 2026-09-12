# Prime Sparta measurable decision learning

This directory is the durable, Sparta-only decision → outcome → learning record.

## Event model

`decision_ledger.jsonl` is append-only. A material recommendation first creates a `DECISION` event containing every required field. Future-looking fields remain `null` until known. After the result becomes measurable, append an `OUTCOME_REVIEW` event with the same `decision_id`; never rewrite the original line.

Confidence uses 1–5. Urgency uses LOW, MEDIUM, HIGH, or IMMEDIATE. Outcome and process are graded independently with A/B/C/D/F.

## Update cycle

OBSERVE → RECOMMEND → RECORD → GRADE → DIAGNOSE → LEARN → VERSION RULES → TEST AGAIN

Only reviewed decisions update signal performance, confidence calibration, and the season scorecard. One ordinary result is not enough to change a rule. All records remain isolated to Billy's 2026 Sparta league.
