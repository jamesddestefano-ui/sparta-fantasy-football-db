# FantasyPros Integration Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline; user explicitly directs autonomous implementation.

**Goal:** Harden the existing intelligence pilot and produce reproducible evaluation artifacts.
**Architecture:** Standard-library transport, fail-closed validation, immutable batch output, offline analysis.
**Tech Stack:** Python 3, unittest, Git.
**Spec:** docs/superpowers/specs/2026-10-17-fantasypros-design.md

## Global Constraints

Sparta only. No authoritative state, decision ledger or Pulse cursor changes. No paid compute, schedules or exposed credential reuse. Endpoint contracts remain provisional pending authoritative OpenAPI.

## Review Focus

Credential-bearing redirects and echoed secrets; duplicate player contradictions; malformed/missing context; partial or repeated output writes; hindsight leakage into comparisons.

### Task 1: Harden ingestion

Files: scripts/fantasypros_ingest.py; tests/test_fantasypros_ingest.py.
Interfaces: retain request_spec/fetch; add validate_payload and publish_batch.
- [x] Write failing tests for identity/scope/scoring, secret echo, retries and output isolation.
- [x] Run tests and verify failures.
- [x] Implement minimal validation, bounded opt-in retries, redirect refusal and immutable batch publishing.
- [x] Run the whole offline suite; commit and verify.

### Task 2: Reproducible analysis

Files: scripts/fantasypros_evaluate.py; tests/test_fantasypros_evaluate.py; intelligence/fantasypros/research/.
Interfaces: evaluate(rows) compares common full-PPR cohorts; comparison reads existing decision evidence without modifying it.
- [x] Write failing numerical/cohort/leakage tests and run.
- [x] Implement evaluation and Week 6 evidence artifact with missing-data flags.
- [x] Run tests; commit and read back artifacts.

### Task 3: Verification and review

Files: docs/fantasypros_sparta_pilot.md; docs/fantasypros_integration_report.md.
- [x] Record all test results, pre-existing learning failure, unresolved specification/credential/quota blockers.
- [x] Review entire diff; verify protected paths unchanged and no secrets committed.
- [ ] Create draft PR targeting main and verify final remote SHAs (feature branch already pushed).

## Execution ledger

Baseline: five offline tests pass; Sparta validation passes; learning validation fails on existing ledger. Do not relax validation or mutate history.
Ruling: user explicitly requests autonomous implementation, so skill confirmation handoffs are superseded. Work in fresh dedicated clone and requested feature branch; no additional worktree needed.

Task 1 complete: 3831314 plus safety followups 646fc80/b03b374/addb1e9; red→green tests verify rejection, isolation, quota/rotation gates, secret echo, partial HTTP, retries and publication.
Task 2 complete: 119b393; paired descriptive metrics and immutable-source comparison. API-backed results remain blocked.
Task 3 in progress: 26 tests pass; Sparta validation passes; learning validation fails with 653 pre-existing errors. Protected paths unchanged. Deepnote project/notebook created and verified, no notebook run; automatically started Basic CPU machine was explicitly stopped. HF search unavailable; no download or job.
Ruling: no OpenAPI reference arrived in the user's reply; do not invent schemas for additional endpoints or claim existing contracts verified.
Ruling: keep learning validator and immutable events unchanged. A draft PR can expose the blocked state; it does not satisfy production acceptance.

October18 continuation: supplied OpenAPI converted/pinned, all7 adapters+ROS added,
PPR and schema-derived tests pass. Added manual Actions/helper and quota preflight
under new main-install directive.38 offline tests pass. Independent reviews' secret,
overflow, row-position and count findings reproduced and fixed. Main merge imported
upstream Pulse intelligence only. Await main installation/readback/preflight evidence.
