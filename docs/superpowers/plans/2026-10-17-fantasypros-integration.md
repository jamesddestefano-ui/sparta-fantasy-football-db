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
- [ ] Write failing tests for identity/scope/scoring, secret echo, retries and output isolation.
- [ ] Run tests and verify failures.
- [ ] Implement minimal validation, bounded opt-in retries, redirect refusal and immutable batch publishing.
- [ ] Run the whole offline suite; commit and verify.

### Task 2: Reproducible analysis

Files: scripts/fantasypros_evaluate.py; tests/test_fantasypros_evaluate.py; intelligence/fantasypros/research/.
Interfaces: evaluate(rows) compares common full-PPR cohorts; comparison reads existing decision evidence without modifying it.
- [ ] Write failing numerical/cohort/leakage tests and run.
- [ ] Implement evaluation and Week 6 evidence artifact with missing-data flags.
- [ ] Run tests; commit and read back artifacts.

### Task 3: Verification and review

Files: docs/fantasypros_sparta_pilot.md; docs/fantasypros_integration_report.md.
- [ ] Record all test results, pre-existing learning failure, unresolved specification/credential/quota blockers.
- [ ] Review entire diff; verify protected paths unchanged and no secrets committed.
- [ ] Push feature branch, create draft PR targeting main and verify remote SHAs.

## Execution ledger

Baseline: five offline tests pass; Sparta validation passes; learning validation fails on existing ledger. Do not relax validation or mutate history.
Ruling: user explicitly requests autonomous implementation, so skill confirmation handoffs are superseded. Work in fresh dedicated clone and requested feature branch; no additional worktree needed.
