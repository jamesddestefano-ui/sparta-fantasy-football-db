# Sparta Fantasy Football DB

Dedicated, auditable system of record for Billy's 2026 Sparta fantasy football league (Yahoo).

This repository contains **Sparta data only**. Never import Mongo ownership, roster, lineup, waiver, FAAB, transaction, or recommendation state here.

## Source-of-truth order

1. Explicit user correction or confirmed completed move
2. Authoritative Yahoo Sparta screenshots / transaction log / roster state
3. Current Yahoo league snapshots
4. Aug. 30, 2026 Sparta auction board
5. Derived repository state
6. External fantasy/news sources (evaluation only; never ownership authority)

## Core data

- `data/league.json` — league settings
- `data/teams.json` — team identities, manager/display names, waiver priority
- `data/draft_2026.json` — authoritative Aug. 30 auction results
- `data/current_roster_jd.json` — current JD roster snapshot
- `data/transactions.json` — immutable confirmed transaction ledger
- `data/faab.json` — FAAB rules and current balance checkpoints
- `data/waiver_state.json` — league waiver priority snapshot
- `data/yahoo_api/latest.json` — current Yahoo state pulled by the official API (all 12 rosters, FAAB, waiver priority, standings, this week's matchups, recent transactions, top available players by position)
- `data/yahoo_api/reconciliation_latest.json` — what Yahoo shows that the repository does not yet record
- `AGENTS.md` — mandatory read/write/verification rules for ChatGPT/Codex

## Required update loop

READ CURRENT REPOSITORY STATE → ANALYZE → VALIDATE SPARTA SCOPE → WRITE SMALLEST AUTHORITATIVE CHANGE → COMMIT → READ BACK → VERIFY → REPORT.

A discussed or proposed roster move is never recorded as completed. Only explicit user confirmation or authoritative Yahoo evidence may create a transaction.

## Measurable learning

- `learning/decision_ledger.jsonl` — append-only decision and outcome-review events
- `learning/schema/decision_event.schema.json` — required decision-time and review fields
- `learning/signal_performance.json` — reviewed signal counts and performance
- `learning/confidence_calibration.json` — expected-versus-actual results by confidence
- `learning/season_scorecard.json` — cumulative Sparta decision metrics
- `learning/rules/learning_rules_v1.json` — versioned initial learning rules
- `learning/weekly/` — isolated post-week reviews
- `scripts/validate_learning.py` — structural validation

Historical recommendation reasoning is immutable. Results, grades, diagnoses, and lessons are appended later. No historical recommendations are backfilled unless reliable decision-time evidence exists.

## Yahoo API auto-sync

`.github/workflows/yahoo_sync.yml` pulls Sparta from the official Yahoo Fantasy API about four times a day (plus early Wednesday/Thursday after waivers) and on demand from the Actions tab. It is read-only on Yahoo. See `docs/yahoo_api_sync.md` for the one-time setup and how report-only vs apply mode work.
