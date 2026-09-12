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

## Grok Pulse intelligence feed

16. `intelligence/grok_pulse_latest.json` is the official machine-readable Grok Pulse ingestion point for Sparta. `intelligence/grok_pulse_history.jsonl` is the append-only Pulse pass history.
17. Treat Grok Pulse as supplemental intelligence only. It may inform player evaluation, watchlists, lineup analysis, waiver priority, injury/role monitoring, and source discovery, but it may never directly change ownership, roster, transactions, FAAB, waiver state, or lineup state.
18. A Pulse pass is considered new only when `status` is `live` and `completedAt` is populated and differs from the last processed pass. `seeded`, failed, partial, or duplicate passes are not new intelligence events.
19. Preserve Pulse provenance. Use each item's `at`, `expert`, `outlet`, `players`, `text`, and `url`; verify consequential claims against the underlying source or independent reporting when practical.
20. Before turning any Pulse item into an add/drop recommendation, re-read current Sparta ownership and roster state. Repository ownership rules always override Pulse availability assumptions.
21. If Pulse and repository state conflict on ownership or roster status, treat Pulse as stale/intelligence-only unless new ownership-authoritative evidence supports a repository update.
22. Grok/LOCK is authorized to write only Pulse mirror artifacts under `intelligence/` using its dedicated server-side credential. It must not modify `data/` or any roster, ownership, FAAB, waiver, transaction, lineup, or reconciliation file.
23. The preferred consumer path is GitHub, not direct `grok.me` scraping: read `intelligence/grok_pulse_latest.json`, compare `completedAt`, then process only genuinely new items.
24. User-facing Watch output must be ownership-filtered: elevate only JD-owned players, players with confirmed Sparta availability, or an opponent-owned player whose change directly creates a meaningful JD waiver, lineup, trade, or matchup decision. Do not surface incidental names merely because they appear in a feed or article.

## Yahoo live snapshot

25. `data/yahoo_live_snapshot_latest.json` is the canonical **current** authenticated Yahoo Sparta live-state artifact (league `sparta`, Yahoo league ID `102586`). It is the CURRENT LIVE VIEW for ownership/availability handoff to Prime Sparta Fantasy Watch when `completed` is true, `observed_at` is recent, `yahoo_league_id` is `102586`, and `source` is authenticated Yahoo Agent Computer. Otherwise treat availability as UNKNOWN.
26. Durable structured history/state remains in `data/current_roster_jd.json`, `data/transactions.json`, `data/faab.json`, `data/waiver_state.json`, `data/lineups/`, `data/reconciliation.json`, and related files. The snapshot does **not** replace those files.
27. On each successful Yahoo live check, refresh `yahoo_live_snapshot_latest.json` even when no new transaction occurred. Update durable transaction/roster/FAAB files only when authoritative Yahoo state changed, using semantic dedupe. Never invent transactions or double-count FAAB/fees. Never import Mongo/DFS/props.

## Required operational loop

USER UPDATE → READ CURRENT REPOSITORY STATE → ANALYZE → VALIDATE LEAGUE + DATA INTEGRITY → WRITE DATABASE CHANGE → COMMIT TO GITHUB → READ BACK / VERIFY → REPORT RESULT.

## Yahoo live-feed authority

28. Before ownership-dependent analysis, inspect latest `main` for current Yahoo Sparta live-feed or snapshot artifacts, including newly added repository paths not named in older prompts.
29. A current, successfully completed Yahoo artifact is ownership-authoritative only when it explicitly identifies Billy's 2026 Sparta league and includes a valid completion or observation timestamp.
30. Valid newer Yahoo Sparta evidence may update roster, ownership, free-agent/waiver classification, transactions, FAAB, waiver priority, and lineup state through the required validation, commit, and read-back loop.
31. Never consume Mongo, unscoped Yahoo, failed, partial, stale, or ambiguous feed artifacts. If current Sparta availability is not established, use `UNKNOWN`.
32. Preserve provenance and conflicts. Yahoo ownership truth supersedes Grok Pulse and external fantasy/news intelligence.
33. A Yahoo-confirmed transaction may be recorded as completed only by appending immutable transaction history and updating derived state; recommendations and watchlist entries remain non-transactions.

## Measurable decision learning loop

34. Effective 2026-09-11 23:37 ET, every material Sparta recommendation must create an immutable decision record under `learning/decision_ledger.jsonl`. Do not rely on chat memory as the learning record.
35. Each decision record must preserve decision-time information: `decision_id`, `system`, `timestamp_et`, `week`, `decision_type`, `subject`, `recommendation`, `confidence` (1-5), `urgency`, `decision_deadline`, `information_available_at_decision`, `key_supporting_signals`, `key_risk_factors`, `alternative_considered`, and then later append/complete `actual_user_action`, `final_pre_deadline_state`, `outcome`, `outcome_grade`, `process_grade`, `result_notes`, `error_category`, `lesson`, `future_rule_adjustment`, and `reviewed_at`.
36. Confidence scale: 1 weak lean; 2 modest lean; 3 solid recommendation; 4 strong recommendation; 5 exceptional/immediate-action recommendation. Urgency must be one of LOW, MEDIUM, HIGH, IMMEDIATE.
37. Every resolved material decision receives two independent grades: outcome grade A-F and process grade A-F. Judge process only from information available at decision time; never use hindsight to rewrite reasoning.
38. Use the repository error taxonomy for failed/weak decisions, allowing multiple categories. Preserve `PROCESS_GOOD_VARIANCE_BAD` when appropriate instead of forcing a reasoning error.
39. Track signal performance over repeated decisions, including at minimum snap share, route participation, target share, air yards, red-zone usage, goal-line usage, rush share, injury replacement role, depth-chart promotion, coach comments, beat reporter information, Vegas/game environment, weather, offensive/defensive injuries, market/consensus, Grok Pulse, authenticated league state, expert consensus, projection disagreement, and late-breaking news.
40. Do not change signal weights because of one result. Prefer repeated evidence; structural data-integrity failures may justify immediate rule changes.
41. Maintain confidence calibration and a cumulative Sparta season scorecard. Confidence 5 recommendations should materially outperform lower-confidence recommendations over time; recalibrate if they do not.
42. After each NFL week, create a Sparta weekly learning review covering BEST DECISIONS, WORST DECISIONS, GOOD PROCESS/BAD RESULT, BAD PROCESS/GOOD RESULT, MISSED OPPORTUNITIES, SIGNALS THAT WORKED, SIGNALS THAT FAILED, DATA QUALITY ISSUES, TIMING ISSUES, RULE CHANGES PROPOSED, RULE CHANGES ADOPTED, and RULES REJECTED DUE TO INSUFFICIENT SAMPLE.
43. Maintain versioned learning rules under `learning/rules/`. Every change must preserve date, old rule, new rule, reason, supporting decisions, sample size, and expected effect. Never silently rewrite historical rules or historical recommendations.
44. Sparta-specific learning must track add/drop/FAAB/start-sit/trade/IR/streaming/defense/injury-contingency/roster-construction decisions; recommended availability vs actual ownership; recommended bid vs actual/winning bid; FAAB saved/overspent; points after recommendation; replacement points; starter-vs-bench differential; drop regret; pickup regret; missed breakout rate; successful early-add rate; weeks held; roster value created; and value per FAAB dollar.
45. Every completed Sparta pickup also incurs the $1 real-money transaction fee. Learning reviews must evaluate both FAAB efficiency and cumulative transaction-fee churn.
46. Never cross-contaminate learning state with Mongo, DFS, props, or another league. Only shared NFL intelligence may be compared outside Sparta; ownership, roster, FAAB, waiver, lineup, and performance metrics remain Sparta-specific.
47. No hindsight rewriting. Historical recommendation text, reasoning, confidence, urgency, timestamps, and decision-time evidence remain immutable; outcomes and lessons are appended afterward.
48. The Prime learning standard is: OBSERVE → RECOMMEND → RECORD → GRADE → DIAGNOSE → LEARN → UPDATE RULES → TEST AGAIN. The objective is improving calibration, speed, accuracy, discipline, and value—not merely counting wins.
