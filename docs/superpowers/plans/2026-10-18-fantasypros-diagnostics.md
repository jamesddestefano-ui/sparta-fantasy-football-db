# FantasyPros diagnostic repair implementation plan

> Execute inline using superpowers:executing-plans. Owner explicitly authorizes autonomous engineering and one additional pilot; no repeated confirmation.

Goal: distinguish provider errors from schema mismatches without weakening validation.
Architecture: extend existing contract exceptions and sanitized ingestion audit; preserve all authoritative state and existing stores.
Tech: Python, unittest, jsonschema, existing manual GitHub Actions workflow.
Spec: October 18 master user directive and AGENTS.md; prior design remains subject to current user authorization.

Constraints: maximum three authenticated data requests, zero retries, stop on provider error; no recurring collection or production promotion. FAAB-only cost per AGENTS14/50. No historical edits.
Review focus: provider values/keys leaking via validation errors; HTTP200 quota/entitlement errors; schema-only failures misclassified as authentication; partial batches; protected-file changes.

## Task 1: diagnostics and stop behavior
- [x] Add failing tests to tests/test_fantasypros_diagnostics.py for safe schema paths, hostile keys/values, HTTP200 provider failures stopping requests, and ordinary schema failures allowing bounded diagnostics.
- [x] Run unittest discover and observe the new failures.
- [x] In fantasypros_contract.py expose bounded schema-owned paths and validator keywords through a ValueError subclass; never instance values or arbitrary keys.
- [x] In fantasypros_ingest.py reject error envelopes before schema parsing; attach fixed classifications, safe diagnostics and stop flag; preserve HTTP status; audit classification without provider text.
- [x] Run full offline suite, Sparta validator, diff checks; commit on isolated branch and read back.

## Task 2: controlled pilot
- [x] Verify workflow uses secrets.FANTASYPROS_API_KEY, retries0, no schedule, contents read.
- [x] Push tested branch; dispatch existing manual workflow once with budget3, rotated=true and unknown-quota authorization=true.
- [x] Inspect resulting run/artifact; do not rerun. Record statuses, counts and exact safe mismatch diagnostics. No accepted batch unless every endpoint validates.

## Task 3: audit and durable handoff
- [x] Classify learning errors and lineage gaps without changing historical events or relaxing validator.
- [x] Review Yahoo freshness, isolation, FAAB, Pulse cursors and workflow checks; document limitations.
- [x] Document measured tool feasibility/cost/testing safeguards; no production expansion before live validation.
- [x] Review branch, commit report, push and verify remote file contents and SHA; merge only when checks permit.

Execution ledger: baseline main d8b72fab79c61d9ec8814f513483b63f73a908f7, clean clone; 43 tests pass; Sparta validator passes; learning validator fails. Old run39084236479 bodies absent, exact cause unrecoverable. Current user authorizes one NEW pilot. Use existing fresh clone as isolated workspace. Cloud runtime has no configured provider secrets; use Actions secret without reading value.

Execution: Task1 complete f48471b (47 offline tests); Task2 complete run39085126777 (3 HTTP200 schema failures, no accepted batch); Task3 audit/report prepared. Independent review found numeric status gap; RED→GREEN fixed e27a3bc, full47 pass. Ruling: user authorizes autonomous execution and existing fresh clone provides isolation; no repeated approval. No merge while checks fail. Protected history unchanged. HF searches unavailable; Deepnote inspected only. Final remote commit/check/readback verification recorded in PR.
