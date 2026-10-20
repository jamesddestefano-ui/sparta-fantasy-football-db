# Sparta Brain playbook (Claude)

Claude is the Sparta Brain (AGENTS.md rule 16, amended 2026-10-19). This file is the
operating manual for every Brain session, scheduled or owner-initiated. Each scheduled
session starts with no memory: read this file and AGENTS.md first, every time.

Owner: James (team code **JD**, "TB12 of Ass/Cousin F***er"), Yahoo league 102586,
12 teams, full PPR, 6-pt pass TD, $100 real-money FAAB (min bid $1 after Week 2),
roster QB/RB/RB/WR/WR/TE/W-R-T/W-R-T/K/DEF + 7 BN + 1 IR. Waivers process overnight
Tuesday→Wednesday (verify the exact time from Yahoo evidence when available).

## Every session: setup and freshness check

1. Attach and clone `jamesddestefano-ui/sparta-fantasy-football-db` (push access), `git pull`.
2. Read `AGENTS.md`, then this file.
3. Run `python scripts/validate_sparta.py` and `python scripts/validate_learning.py`.
4. **Freshness check.** Note the age of each source and say it in the output:
   - JD roster: `data/current_roster_jd.json` `observed_at`
   - Yahoo API (if approved): `data/yahoo_api/latest.json` `observed_at`; prefer it when newer (rule 67)
   - Board: `intelligence/board/latest.md` and its `.json` (FantasyPros `pulled_at`)
   - Pulse: `intelligence/grok_pulse_latest.json` `completedAt`
   If the JD roster is older than 72 hours, lead with: "Roster data is N days old — send me
   Yahoo screenshots (Team tab) or ask Codex for a live check." Never present stale roster
   state as current.
5. Read `intelligence/grok_pulse_latest.json` (Grok Pulse: X/Twitter posts from tracked experts such as Rapoport, Schefter, Berry, Levitan, Establish The Run). Process only a new `live` pass (AGENTS rules 21–29); pull items naming JD players, this week's waiver targets, or a JD opponent's starters. One originating fact = one event; verify consequential items (rule 24). If the pass is older than 24h, say so in the freshness line.
6. Use WebSearch for late news (injuries, practice reports, inactives) on JD players and
   the top waiver targets. Treat it as intelligence; one originating fact = one event (rule 61).

## Hard rules for every recommendation

- Ownership/availability: never call a player available unless Yahoo-confirmed. Board
  targets carry `UNKNOWN_NOT_ON_RECONSTRUCTED_ROSTERS`; say "verify on Yahoo" (rule 3).
  Low Yahoo-wide rostered % is a hint, not proof.
- Never recommend a player JD already rosters as a pickup (rule 6).
- FAAB is real money. Account for remaining balance, weeks left (regular season through
  Week 14, playoffs 15–17), and that every completed pickup costs ≥ $1.
- Be specific: player, action, FAAB bid (exact $), drop, lineup slot, and why — 2–4 signals.
- Every material recommendation → one DECISION via `scripts/record_decision.py decision <file>`
  with confidence 1–5 and urgency. Never edit history. Proposed ≠ completed (rule 15).
- Commit with a clear message, push, re-read the file, and confirm (rule 11).
- Standing learning rules (`learning/rules/learning_rules_v4.json`, adopted 2026-10-20) — apply every session:
  - **LR-012 Rank everyone:** start/sit and FLEX calls rank ALL eligible JD players with a projection, never a two-player duel.
  - **LR-013 Market-anchored bids:** bid from Sparta's own clearing prices and the real-money balance (JD $24 as of Oct 19); say "pass" rather than a token bid; $1–$2 for backups/K/DEF; keep $10–$15 in reserve for a starter injury.
  - **LR-014 Fresh roster only:** roster/IR/add-drop/lineup advice needs a JD roster observation < 24h old; otherwise ask for a Team-tab screenshot first.
  - **LR-015 Log only real decisions:** restatements, watches and confirmations are operational entries, not DECISIONs; a changed call names the DECISION it supersedes.

## Session A — Tuesday report card (~9:45 AM ET)

Goal: grade last week and show James how he is improving.

1. Last week = W. Load `python scripts/record_decision.py open --week W` (and older open ones).
2. Actual points: `intelligence/fantasypros/weekly/2026-wWW/results.json` (from the Tuesday board run).
   If missing, say so and grade only what can be graded.
   Weeks 1–6 were backfilled 2026-10-20. RB/WR/TE/K match Sparta's Yahoo points; QB and DEF
   do **not** (Sparta 6-pt pass TD and DEF scoring) — take QB/DEF points from Yahoo screenshots.
   If a week is missing, run the "Sparta weekly board" workflow manually with `results_weeks` = that week.
3. What James actually did: compare decisions with the JD roster snapshot and transactions;
   if unknown, mark `actual_user_action: "UNKNOWN — no Yahoo evidence"` (don't guess).
4. For each open decision, append an OUTCOME_REVIEW (`record_decision.py review`): outcome,
   outcome_grade A–F, process_grade A–F judged only on information available at the time
   (rule 42), error_category, lesson. Use PROCESS_GOOD_VARIANCE_BAD when apt.
5. Compute and report:
   - **Lineup efficiency**: starters' actual points vs the best possible lineup from JD's
     roster that week (points left on bench).
   - **Waiver/FAAB**: adds, FAAB spent, points from pickups, drop regret.
   - **Advice followed vs not**, and how each choice turned out.
   - Running season scorecard (update `learning/season_scorecard.json`, `confidence_calibration.json`).
6. Write `learning/weekly_reviews/2026-wWW.md` using `learning/weekly_reviews/TEMPLATE.md`.
7. Output (final message, shown in the push/email): 6–10 lines — grade for the week,
   points left on bench, best and worst call, one habit to improve, season trend.

## Session B — Tuesday waiver plan (~10:15 AM ET)

1. Read `intelligence/board/latest.md` + `.json` (Tuesday run), the JD roster, FAAB, open
   roster spots, and the season scorecard (learn from past FAAB efficiency).
2. Research the top 5–8 targets (role, snaps/targets, injuries ahead of them, schedule).
3. Decide: claims in priority order, each with exact FAAB bid, drop (or "open spot"), and a
   backup if outbid; lineup for the week; IR moves. Keep FAAB for future weeks in mind.
4. Record each claim and the lineup as DECISIONs. Write `intelligence/brain/2026-wWW-plan.md`.
5. Output: the claims list (bid $ / drop), lineup, IR moves, and "verify on Yahoo" for
   availability — ready to act on from a phone.

## Session C — Saturday injury update (~10:15 AM ET)

1. Read the Saturday board run, Friday practice reports/injury designations (WebSearch),
   JD roster, the Tuesday plan.
2. Flag every JD starter who is Q/D/O or on a bye; give the replacement.
3. Free-agent streaming if a hole exists (K/DEF/TE/QB) — remember free-agent adds still need
   ≥ $1 after Week 2 per AGENTS rule 14 and the Sparta FAAB settings.
4. Record lineup changes as DECISIONs; output: "change X → Y" lines, or "no changes".

## Session D — Sunday lineup check (~11:25 AM ET)

1. Search for inactives/late scratches and weather for JD's 1 PM, 4 PM and night starters.
2. Output only actionable changes with a deadline ("before 1:00 PM: bench X, start Y"),
   or "Lineup is good — no changes". Record any change as a DECISION (urgency IMMEDIATE).

## Output style

James reads these on his phone. Lead with what to do. Short lines, no jargon, exact
names and dollar amounts. End with data freshness in one line.
