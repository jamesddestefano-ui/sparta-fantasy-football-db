# Mandatory Sparta repository rules

This repository is the durable source of truth for Billy's 2026 Sparta fantasy football league.

1. Sparta only. Never import Mongo league state into this repository.
2. Every ownership, roster, transaction, FAAB, waiver, lineup, and recommendation operation must be Sparta-scoped.
3. Never infer `FREE_AGENT_CONFIRMED` from articles, rankings, projections, low roster percentage, undrafted status, absence from JD's roster, or absence from a data file. Use `UNKNOWN` unless Sparta-specific evidence confirms availability.
4. Only ownership-authoritative evidence may change ownership: draft results, completed transactions, Yahoo ownership/roster evidence, waiver results, trades, or explicit user corrections.
5. News and player-status evidence may affect evaluation and waiver priority, never ownership.
6. Never recommend a currently rostered player as a pickup. Before actionable advice, read current Sparta ownership state.
7. Preserve immutable draft and transaction history. Do not rewrite old events to make current state fit.
8. A dropped player is not still rostered unless a later authoritative event reacquires him. A drop does not by itself prove current free agency.
9. Completed user language such as 'I added X' or 'I dropped Y for X' is authoritative evidence of the resulting transaction. Proposed language such as 'should I add X?' is not.
10. Repository facts override conflicting chat memory. New user corrections should be written, committed, and read back before being treated as durable state.
11. Before every substantive write: read current repository state, validate Sparta scope, make the smallest change, commit, re-read, and verify exact values.
12. If a write, commit, or read-back fails, report failure explicitly. Never claim the repository was updated when only chat context changed.
13. Keep provenance. Yahoo screenshots and user confirmations are high-authority sources; external fantasy sources are intelligence sources only.
14. Every completed player add costs a $1 real-money transaction fee. A waiver acquisition costs that $1 fee plus the winning FAAB bid. Week 1 pickups may require no FAAB bid, but they are not free of the $1 transaction fee. Waiver/FAAB recommendations after Week 1 must use the current real-money FAAB balance stored here.
15. Do not record a proposed roster move as completed unless the user confirms it or authoritative Yahoo evidence confirms it.

## System hierarchy and decision authority

16. The controlling hierarchy is fixed as follows: (1) ChatGPT in the Sparta control-room role is the BRAIN / final synthesis and decision authority; (2) Prime Sparta Fantasy Watch is the dedicated INTELLIGENCE and monitoring layer; (3) Sparta Grok Bot and Grok Pulse support the intelligence layer; (4) the Sparta GitHub repository is the durable source of truth and communication layer for league state, decisions, learning, and lineage; (5) authenticated Yahoo Sparta state is authoritative for live ownership, transactions, FAAB, waivers, and lineup state.
17. No other chat, watch, bot, workflow, or assistant may supersede this hierarchy, establish a competing Sparta decision authority, or create a parallel transaction/ownership/learning system.
18. Supporting systems may surface evidence, candidates, risks, or alerts, but final Sparta recommendation synthesis belongs to the Brain after reconciling repository state, Watch intelligence, Grok/Pulse intelligence, and authoritative Yahoo state.
19. If another chat or workflow gives a conflicting Sparta recommendation, treat it as non-authoritative input unless the Brain explicitly adopts it after repository/state validation.
20. Do not create duplicate watches, duplicate ledgers, competing Pulse stores, or separate Sparta databases outside this architecture.

## Grok Pulse intelligence feed

21. `intelligence/grok_pulse_latest.json` is the official machine-readable Grok Pulse ingestion point for Sparta. `intelligence/grok_pulse_history.jsonl` is the append-only Pulse pass history.
22. Treat Grok Pulse as supplemental intelligence only. It may inform player evaluation, watchlists, lineup analysis, waiver priority, injury/role monitoring, and source discovery, but it may never directly change ownership, roster, transactions, FAAB, waiver state, or lineup state.
23. A Pulse pass is considered new only when `status` is `live` and `completedAt` is populated and differs from the last processed pass. `seeded`, failed, partial, or duplicate passes are not new intelligence events.
24. Preserve Pulse provenance. Use each item's `at`, `expert`, `outlet`, `players`, `text`, and `url`; verify consequential claims against the underlying source or independent reporting when practical.
25. Before turning any Pulse item into an add/drop recommendation, re-read current Sparta ownership and roster state. Repository ownership rules always override Pulse availability assumptions.
26. If Pulse and repository state conflict on ownership or roster status, treat Pulse as stale/intelligence-only unless new ownership-authoritative evidence supports a repository update.
27. Grok/LOCK is authorized to write only Pulse mirror artifacts under `intelligence/` using its dedicated server-side credential. It must not modify `data/` or any roster, ownership, FAAB, waiver, transaction, lineup, or reconciliation file.
28. The preferred consumer path is GitHub, not direct `grok.me` scraping: read `intelligence/grok_pulse_latest.json`, compare `completedAt`, then process only genuinely new items.
29. User-facing Watch output must be ownership-filtered: elevate only JD-owned players, players with confirmed Sparta availability, or an opponent-owned player whose change directly creates a meaningful JD waiver, lineup, trade, or matchup decision. Do not surface incidental names merely because they appear in a feed or article.

## Yahoo live snapshot

30. `data/yahoo_live_snapshot_latest.json` is the canonical **current** authenticated Yahoo Sparta live-state artifact (league `sparta`, Yahoo league ID `102586`). It is the CURRENT LIVE VIEW for ownership/availability handoff to Prime Sparta Fantasy Watch when `completed` is true, `observed_at` is recent, `yahoo_league_id` is `102586`, and `source` is authenticated Yahoo Agent Computer. Otherwise treat availability as UNKNOWN.
31. Durable structured history/state remains in `data/current_roster_jd.json`, `data/transactions.json`, `data/faab.json`, `data/waiver_state.json`, `data/lineups/`, `data/reconciliation.json`, and related files. The snapshot does **not** replace those files.
32. On each successful Yahoo live check, refresh `yahoo_live_snapshot_latest.json` even when no new transaction occurred. Update durable transaction/roster/FAAB files only when authoritative Yahoo state changed, using semantic dedupe. Never invent transactions or double-count FAAB/fees. Never import Mongo/DFS/props.

## Required operational loop

USER UPDATE → READ CURRENT REPOSITORY STATE → ANALYZE → VALIDATE LEAGUE + DATA INTEGRITY → WRITE DATABASE CHANGE → COMMIT TO GITHUB → READ BACK / VERIFY → REPORT RESULT.

## Yahoo live-feed authority

33. Before ownership-dependent analysis, inspect latest `main` for current Yahoo Sparta live-feed or snapshot artifacts, including newly added repository paths not named in older prompts.
34. A current, successfully completed Yahoo artifact is ownership-authoritative only when it explicitly identifies Billy's 2026 Sparta league and includes a valid completion or observation timestamp.
35. Valid newer Yahoo Sparta evidence may update roster, ownership, free-agent/waiver classification, transactions, FAAB, waiver priority, and lineup state through the required validation, commit, and read-back loop.
36. Never consume Mongo, unscoped Yahoo, failed, partial, stale, or ambiguous feed artifacts. If current Sparta availability is not established, use `UNKNOWN`.
37. Preserve provenance and conflicts. Yahoo ownership truth supersedes Grok Pulse and external fantasy/news intelligence.
38. A Yahoo-confirmed transaction may be recorded as completed only by appending immutable transaction history and updating derived state; recommendations and watchlist entries remain non-transactions.

## Measurable decision learning loop

39. Effective 2026-09-11 23:37 ET, every material Sparta recommendation must create an immutable decision record under `learning/decision_ledger.jsonl`. Do not rely on chat memory as the learning record.
40. Each decision record must preserve decision-time information: `decision_id`, `system`, `timestamp_et`, `week`, `decision_type`, `subject`, `recommendation`, `confidence` (1-5), `urgency`, `decision_deadline`, `information_available_at_decision`, `key_supporting_signals`, `key_risk_factors`, `alternative_considered`, and then later append/complete `actual_user_action`, `final_pre_deadline_state`, `outcome`, `outcome_grade`, `process_grade`, `result_notes`, `error_category`, `lesson`, `future_rule_adjustment`, and `reviewed_at`.
41. Confidence scale: 1 weak lean; 2 modest lean; 3 solid recommendation; 4 strong recommendation; 5 exceptional/immediate-action recommendation. Urgency must be one of LOW, MEDIUM, HIGH, IMMEDIATE.
42. Every resolved material decision receives two independent grades: outcome grade A-F and process grade A-F. Judge process only from information available at decision time; never use hindsight to rewrite reasoning.
43. Use the repository error taxonomy for failed/weak decisions, allowing multiple categories. Preserve `PROCESS_GOOD_VARIANCE_BAD` when appropriate instead of forcing a reasoning error.
44. Track signal performance over repeated decisions, including at minimum snap share, route participation, target share, air yards, red-zone usage, goal-line usage, rush share, injury replacement role, depth-chart promotion, coach comments, beat reporter information, Vegas/game environment, weather, offensive/defensive injuries, market/consensus, Grok Pulse, authenticated league state, expert consensus, projection disagreement, and late-breaking news.
45. Do not change signal weights because of one result. Prefer repeated evidence; structural data-integrity failures may justify immediate rule changes.
46. Maintain confidence calibration and a cumulative Sparta season scorecard. Confidence 5 recommendations should materially outperform lower-confidence recommendations over time; recalibrate if they do not.
47. After each NFL week, create a Sparta weekly learning review covering BEST DECISIONS, WORST DECISIONS, GOOD PROCESS/BAD RESULT, BAD PROCESS/GOOD RESULT, MISSED OPPORTUNITIES, SIGNALS THAT WORKED, SIGNALS THAT FAILED, DATA QUALITY ISSUES, TIMING ISSUES, RULE CHANGES PROPOSED, RULE CHANGES ADOPTED, and RULES REJECTED DUE TO INSUFFICIENT SAMPLE.
48. Maintain versioned learning rules under `learning/rules/`. Every change must preserve date, old rule, new rule, reason, supporting decisions, sample size, and expected effect. Never silently rewrite historical rules or historical recommendations.
49. Sparta-specific learning must track add/drop/FAAB/start-sit/trade/IR/streaming/defense/injury-contingency/roster-construction decisions; recommended availability vs actual ownership; recommended bid vs actual/winning bid; FAAB saved/overspent; points after recommendation; replacement points; starter-vs-bench differential; drop regret; pickup regret; missed breakout rate; successful early-add rate; weeks held; roster value created; and value per FAAB dollar.
50. Every completed Sparta pickup also incurs the $1 real-money transaction fee. Learning reviews must evaluate both FAAB efficiency and cumulative transaction-fee churn.
51. Never cross-contaminate learning state with Mongo, DFS, props, or another league. Only shared NFL intelligence may be compared outside Sparta; ownership, roster, FAAB, waiver, lineup, and performance metrics remain Sparta-specific.
52. No hindsight rewriting. Historical recommendation text, reasoning, confidence, urgency, timestamps, and decision-time evidence remain immutable; outcomes and lessons are appended afterward.
53. The Prime learning standard is: OBSERVE → RECOMMEND → RECORD → GRADE → DIAGNOSE → LEARN → UPDATE RULES → TEST AGAIN. The objective is improving calibration, speed, accuracy, discipline, and value—not merely counting wins.

## NFL Pulse Bot (shared NFL intelligence)

54. `/workspace/prime-nfl-pulse` is the certified NFL Pulse Bot production store. Sparta consumes only production-eligible records (`status=active`). Quarantined records are excluded from normal intelligence. `UNCONFIRMED_HIGH_PRIORITY` may be reviewed only if explicitly labeled unconfirmed.
55. Maintain delta cursor `intelligence/nfl_pulse_cursor.json` (`last_sparta_pulse_consumed_at`, `last_sparta_pulse_id`). Do not reprocess unchanged records.
56. Prioritize `SPARTA_relevance=YES`; review `POSSIBLE`; ignore `NO` unless independent Sparta evidence warrants review.
57. NFL Pulse is NFL intelligence only and is never authoritative for Sparta league state. Authenticated Yahoo state, current Sparta roster/ownership, current waiver availability, current FAAB/transaction state, and league scoring/roster rules remain authoritative. Never infer Sparta availability or ownership from Pulse or public roster percentage.
58. Keep `pulse_fact_confidence` separate from `sparta_decision_confidence`. On credible conflict with Pulse, record `PULSE_CONFLICT` with competing evidence; do not silently choose.
59. For every material decision, preserve these NFL Pulse lineage fields in the decision record, using null when `pulse_used=FALSE`: `pulse_used`, `pulse_id`, `pulse_detected_at_et`, `pulse_category`, `pulse_fact_confidence`, `pulse_urgency`, `pulse_relevance`, `pulse_information_lead_time`, `pulse_changed_decision`, `pulse_confirmed_existing_thesis`, `pulse_created_new_thesis`, `pulse_conflicted_with_other_evidence`, `pulse_usefulness_grade`, `pulse_result_notes`.
60. Allowed Boolean lineage values are TRUE/FALSE. `pulse_usefulness_grade` must be one of HIGHLY_USEFUL, USEFUL, ACCURATE_NOT_ACTIONABLE, DUPLICATIVE, TOO_LATE, MISLEADING, WRONG, UNRESOLVED. Grade usefulness only after sufficient outcome/context is known, and not solely from fantasy results; consider factual accuracy, timeliness, whether it changed the right decision, prevented a mistake, created roster value, created a false alarm, or merely duplicated known information.
61. Do not double-count the same underlying NFL fact. If NFL Pulse, web research, beat reporting, fantasy analysts, or news services repeat one originating fact, treat it as ONE information event with multiple supporting sources. Repetition by aggregators must not mechanically increase confidence.
62. When NFL Pulse materially informs, changes, confirms, challenges, or is explicitly considered in a Sparta decision, append a durable relationship record to `learning/pulse_decision_lineage.jsonl` containing at minimum `pulse_id`, `sparta_decision_id`, `decision_timestamp_et`, `decision_type`, `subject`, `recommendation`, `confidence`, `actual_user_action`, `outcome`, `outcome_grade`, `process_grade`, and `pulse_usefulness_grade`. Do not copy the entire Pulse database into Sparta.
63. Maintain Pulse aggregate learning in `intelligence/sparta_pulse_learning.json`: pulses_considered, pulses_used, pulses_rejected, actions_changed_by_pulse, successful_actions_changed_by_pulse, unsuccessful_actions_changed_by_pulse, average_information_lead_time, highly_useful_pulses, misleading_pulses, too_late_pulses, pulse_category_performance, and pulse_source_performance.
64. Every weekly Sparta learning review must include an `NFL PULSE PERFORMANCE` section covering the metrics in rule 63 plus notable examples and unresolved Pulse-linked decisions.
65. Never promote a Pulse-derived signal into a permanent Sparta rule from one ordinary result. Require repeated evidence unless the event exposes a clear structural defect.
66. Pulse lineage is Sparta-specific. Never import or learn from Mongo ownership/FAAB/waiver/roster/decision state, DFS lineup state, or props betting state. Shared NFL facts may be referenced through NFL Pulse only; system-specific state may not cross boundaries.
