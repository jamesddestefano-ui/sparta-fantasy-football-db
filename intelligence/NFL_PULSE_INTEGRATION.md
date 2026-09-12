# Sparta ← NFL Pulse Bot integration

**Store:** `/workspace/prime-nfl-pulse` (NFL Pulse Bot production-certified shared intelligence).

## Consumption
- Production-eligible only (`status=active`). Never use quarantined records as normal downstream intel.
- `UNCONFIRMED_HIGH_PRIORITY` may be reviewed but must stay explicitly labeled unconfirmed.
- Delta cursor: `intelligence/nfl_pulse_cursor.json` (`last_sparta_pulse_consumed_at`, `last_sparta_pulse_id`).
- Prioritize `SPARTA_relevance=YES`; review `POSSIBLE`; ignore `NO` unless independent Sparta evidence warrants.

## Authority
- Pulse answers: what changed in the NFL?
- Authenticated Yahoo / Sparta state answers: what can we do in league 102586?
- Pulse is evidence only — never a command for ADD/DROP/FAAB/START/SIT/TRADE/WAIVER PRIORITY.
- Keep `pulse_fact_confidence` separate from `sparta_decision_confidence`.
- Conflicts with Pulse → record `PULSE_CONFLICT` with competing evidence; do not silently pick one.

## Decision linkage & learning
- Material Sparta recommendations that use Pulse must append to existing `learning/decision_ledger.jsonl` (AGENTS.md §§34–48) and include pulse linkage fields: `pulse_id`, `pulse_detected_at_et`, `pulse_category`, `pulse_fact_confidence`, `pulse_urgency`, plus whether Pulse changed/improved the decision and information lead time.
- Pulse-specific aggregate counters: `intelligence/sparta_pulse_learning.json` (usefulness grades + cumulative metrics).
- Isolation: never import Mongo/DFS/props into Sparta decisions.
