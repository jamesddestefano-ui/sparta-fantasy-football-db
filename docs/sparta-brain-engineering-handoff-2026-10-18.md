# Sparta Brain engineering handoff — October 18, 2026

Execution report: 2026-10-18T01:06:59.126920+00:00. Status: **FantasyPros unvalidated; production intelligence disabled**.
Branch: `codex/fantasypros-diagnostics-20261018`. Baseline/latest main at initialization: `d8b72fab79c61d9ec8814f513483b63f73a908f7`.
Live-tested code: `f48471b77c278e77180240d0b6133d81f5df4ee9`. Final offline-tested repair: `e27a3bc` (numeric provider status stop). The containing GitHub commit/PR identifies the documentation revision; do not confuse it with live-tested code.

## Completed work and controlled pilot

Read complete AGENTS.md, README, FantasyPros design/plan/report, learning schemas/governance, NFL Pulse integration, workflow and actual failed job117547347102. Fresh clone was clean. Preserved existing architecture and authoritative records.

Prior run39084236479 retained only generic OPENAPI_SCHEMA_MISMATCH diagnostics; its precise response failures cannot be reconstructed. This session adds bounded schema-owned paths and missing-field diagnostics, preserving strict validation. Never log instance values, arbitrary provider keys, raw error text or credentials. HTTP200 error envelopes now stop the pilot, including numeric status/code/status_code401/403/429; no partial batches publish. Existing supplied contract remains unchanged.

Owner's current directive authorized ONE additional pilot despite unknown quota, superseding historical consumed-authorization and quota-confirmation notes. Dispatched the existing workflow once, on tested branch, with budget3, rotation attested, unknown quota truthfully recorded, zero retries.

[Live run39085126777](https://github.com/jamesddestefano-ui/sparta-fantasy-football-db/actions/runs/39085126777), live requests 2026-10-18T01:04:36.467419Z–01:04:37.282314Z. Secret presence true; configured source `secrets.FANTASYPROS_API_KEY`. No key value requested/read. Exactly **three authenticated data requests**, no retries. No new pilot is authorized by the remaining unused budget (none remains).

| Endpoint | HTTP | Schema result | Validated records | Observed mismatch |
|---|---|---|---|---|
| NFL2026 week6 PPR FLEX consensus |200|FAIL|null|ranking_type_name enum; player tier missing|
| NFL2026 week6 WR projections, PPR stats selected |200|FAIL|null|fpid, mflid, stats type|
| NFL injuries, year2026/week6 |200|FAIL|null|injury_update_date type; status/status_short enums|

These are exact **schema locations**, not inferred actual values or an exhaustive error inventory (12 diagnostics maximum per endpoint, repeated across players). All three responses reached player/injury schema validation. No recognized error envelope was detected. No HTTP401/403/429 was observed in the pilot. Valid authenticated, correctly scoped/scored usable data is **not established**. Remaining quota unknown. No accepted batch; counts unavailable, not zero. No authoritative reconciliation, production weights or lineup changes.

Root cause established for this run: live provider representation differs from the supplied pinned OpenAPI contract. It is unsafe to guess actual types, optionality, ranking enum mapping or injury meanings from validator keywords. Do not remove tier requirements, broaden enums/types, coerce unknown structures or claim authentication success just to pass. Next correction needs provider-confirmed contract/examples or owner-supplied sanitized representative payloads. Once reviewed adapters have offline fixtures, another live validation requires separate authorization.

Provider documentation: repository's owner-supplied Public API v2 OpenAPI (SHA256 `b885833209339048644bc8149d98c4e218075c88babb72bf0705aa0e3b7942af`) defines base URL, x-api-key, required projection position, WR stats.points_ppr, ranking/player IDs, injury structure and request context. Current docs lookup did not supply a replacement: developer search found no useful official reference; `/about/api/` showed Page Not Found, documentation-root `/public/v2/` returned403 Missing Authentication Token. That was an unauthenticated documentation lookup, not an additional authenticated pilot/data-endpoint call. Do not interpret it as credential failure. No speculative data endpoints were queried.

Sanitized audit: `intelligence/fantasypros/research/live-pilot-diagnostics-2026-10-18.json`, read back from actual live-step job117549959899 logs after preflight, excluding unittest synthetic audits. Artifact12120014576 was uploaded with one-day retention. CLI ZIP download failed Forbidden; job-log readback succeeded. No raw provider body retained. Existing workflow stores valid raw batches only ephemerally on runner and uploads sanitized summaries; no usable batch existed here.

## Verification and review

- Baseline43 offline tests pass; repair47 pass locally and47 in Actions. Regression tests first reproduced missing diagnostics/HTTP200 continuation, then passed. Fresh independent code review found numeric-status continuation; reproduced with four failing cases and fixed offline; final47 pass. Final numeric-status repair has not been live-tested; no repeat pilot.
- `python scripts/validate_sparta.py`: PASS,12 teams,204 draft records,17 roster entries,157 transactions; stored FAAB33 and waiver priority3. These are repository baseline values, not a new live Yahoo check.
- `python scripts/validate_learning.py`: FAIL,653 existing errors. Validator unchanged; no green repository-wide CI claim.
- `git diff --check`: PASS. Only scripts/tests and new engineering/research documentation changed. No data/, learning/, contracts/, existing Pulse mirrors or cursors altered.
- Existing workflow is manual-only, serialized, contents:read, pinned actions, tests before requests, zero retry invocation, secret-backed. Learning continue-on-error visibly preserves its failure; successful preflight never means production readiness.
- Ruleset list returned empty; branch-protection details inaccessible403 to integration. Do not infer protection absent. PR checks must determine merge eligibility; do not bypass failing checks.

## Learning audit and remediation priority

`intelligence/fantasypros/research/learning-audit-2026-10-18.json` preserves source hashes and every validator error/line. Counts below are error occurrences, not independent corruptions.

| Root class | Errors | Evidence / treatment |
|---|---:|---|
| Legacy event/schema incompatibility |594|99 events lack event_type; six error occurrences each. Includes Pulse consumption, suppression, live-check observations and possible material decisions. Classify by meaning before any exemption.|
| System identity incompatibility |49|47 formal Brain and2 live-check records rejected by Watch-only validator. Preserve original actor; distinguish actor from Sparta scope in prospective schema.|
| Incomplete formal/review records |10|Five missing-field errors, three confidence errors, two urgency errors. Decision lines123/125 lack confidence/urgency; review157 has null confidence and references original reasoning. Source-backed supplements only; never invent values.|

Raw error totals: wrong system148, missing-field104, invalid event_type99, confidence102, urgency101, review-before-decision99. No invalid-JSON, invalid-grade or duplicate formal DECISION-ID errors found. There are160 events,56 formal decisions,3 reviews,2 supplements;57 records lack decision_id. "Review precedes DECISION" is emitted for all99 legacy events, so it does not independently prove99 orphan reviews.

Additional integrity gaps outside653: five nonblank Pulse relationship records; two reference the same Pulse/decision pair (inspect lifecycle before deduping); one refers to an ID without a formal DECISION; one lacks the canonical sparta_decision_id.102 events omit pulse_used (99 legacy,3 formal). Existing validator does not enforce Pulse lineage. Descriptive schema and JSON Schema differ on record versions, supplement event, decision types and lineage. Do not bulk rewrite either schema or history to erase discrepancies.

1. **P0:** Repair prospective writer validation and canonical event/version contracts; enforce Sparta scope, unique stable IDs, explicit recommendation versus non-decision events, and Pulse relationships. Preserve actor attribution. Add migration-aware tests before changing validator behavior; keep legacy findings visible.
2. **P1:** Review material legacy decisions, lines123/125 and missing Pulse references against immutable decision-time sources. Append supplements with original references and evidence; unresolved information stays unknown. Never backfill confidence, timestamps, reasoning or outcomes without contemporaneous proof.
3. **P1:** Define read-only, version-aware projection of the EXISTING ledger and review/supplement links. No duplicate ledger or database. Validate orphan links and semantic duplicate lifecycle events before updating aggregate metrics.
4. **P2:** Recompute calibration/FAAB efficiency and scorecards only from reconciled, graded cohorts; separate process/outcome grades and report exclusions. Do not change model weights from one outcome.

No historical or validator edits applied: evidence does not justify an automatic non-destructive content correction. Audit receipts and prioritized plan are the safe correction to the previously unexplained653 count.

## Yahoo, FAAB, isolation and intelligence safeguards

Latest main Yahoo artifact discovered: `data/yahoo_live_snapshot_latest.json`, completed=true, league102586, observed2026-10-15T19:56:00-04:00, read-only authenticated Yahoo UI provenance. More than49 hours old at this execution. It contains inconsistent roster/lineup summaries (Dobbins both starter and bench, Cowing listed in critical summary but absent from structured starter/bench lists). Preserve evidence; refresh Yahoo and reconcile before ownership-dependent advice. **Current availability UNKNOWN.** No pickup recommendation made.

Sparta-only validation passes. AGENTS14/50 resolve cost: FAAB dollars are real dollars; after Sep15 minimum winning bid $1; no separate pickup fee. Historical conflicting design text is superseded, accounting untouched. Transaction history, current roster, FAAB and lineups unchanged; no fabricated acquisition or availability.

Grok Pulse newness requires live+completedAt distinct; NFL Pulse uses active records and existing cursor. No ingestion performed, cursors unchanged. `/workspace/prime-nfl-pulse` unavailable in this environment, so production source content/eligibility cannot be independently checked. Governance reviewed; no claim of end-to-end runtime certification. Fact confidence stays separate from decision confidence; repeated originating NFL facts count once.

After eventual FantasyPros pass: reconcile explicit Yahoo IDs against fresh authoritative Sparta evidence; no fuzzy auto-match, preserve unmapped IDs and timestamps. Filter JD-owned, confirmed available or material opponent research; classify injury report uncertainty and publication staleness; dedupe originating facts across sources; compare projections on common scoring/week/player cohorts; leave final synthesis to Brain. These are gated next steps, not completed capabilities.

## Tool integration assessment

Superpowers was actually read/applied for debugging, planning, TDD, verification and independent code review. No competing Brain created. Deepnote project read through connected app; Hugging Face tools attempted and unavailable. Production expansion deferred because FantasyPros failed.

| Tool | Purpose / required data | Feasibility and testing | Cost/quota | Safeguards / readiness |
|---|---|---|---|---|
| Superpowers | Safer engineering using existing code, contracts and sanitized fixtures | Used here; red→green regressions, full suite and fresh review. Add CI suite coverage prospectively. | Agent/review compute; no FantasyPros calls for tests | No league mutations; engineering workflow usable, does not validate provider data by itself |
| Hugging Face | Evaluate opportunity-based point forecasts and calibrated uncertainty; licensed historical snaps/routes/targets/rush/red-zone features, injury-role changes, decision-time forecasts and actual PPR | Model and dataset searches returned UNAVAILABLE. Proposed baselines: consensus, prior rolling mean, regularized regression/tree quantiles; forward weekly holdouts, season/player leakage checks, paired MAE/RMSE/bias and interval coverage/calibration | No model downloads, jobs, training or paid compute; future dataset licensing/CPU/GPU cost unpriced | Verify licenses/publication timing; no private league upload, remote code or production promotion. BLOCKED exploratory feasibility, no model selected |
| Deepnote | Existing separate analytical notebook for projection accuracy, starter/bench deltas, actual FAAB value and confidence calibration; immutable hashed GitHub analytical exports only | Existing project4e60d132-6e5b-45ae-b9c5-9765bb95e541 read back: one notebook, three files, no integrations, lastRunAt=null, no schedule. Re-sync reviewed evaluator; reconcile cohorts; run offline parity and leakage tests before execution | No notebook execution/creation this session; future machine costs unknown. Prior report notes auto-start on creation and subsequent stop; current machine state not exposed by get_project | Static website sharing disabled; full workspace membership/privacy not proven. No data uploaded or public publication. RESEARCH SCAFFOLD ONLY |

No experimental accuracy improvement established. Brain approval, backtesting and calibration remain required for production models. Prefer the existing evaluator and notebook over new databases or tools.

## Brain handoff / next action

Use this report and linked sanitized audit as engineering evidence only. Keep FantasyPros disabled and pickup availability UNKNOWN until fresh Yahoo proof. Obtain provider-confirmed response contract/examples for the specific mismatches; implement explicit audited adapters with fixtures, then seek a separately authorized bounded live validation. In parallel, repair prospective learning contracts and source-backed lineage without rewriting history. No direct message into Brain chat was sent; GitHub is this handoff.
