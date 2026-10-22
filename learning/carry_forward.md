# Sparta carry-forward lessons (all seasons)

The repository is permanent (owner direction, James, 2026-10-22). This file is the **one place every Brain session reads** for what Sparta has learned across seasons: before every draft, at the start of every season, and whenever a decision touches one of these topics.

Status labels: **ADOPTED** (an active rule in `learning/rules/learning_rules_v*.json`), **PROPOSED** (owner direction or evidence that still needs season-end validation), **OBSERVATION** (one season of data, watch it). Never delete a lesson. When one is replaced, mark it SUPERSEDED with the date and reason.

## Draft (auction, $200)

| Lesson | Status | Source |
|---|---|---|
| Spend $1–3 on QB; stream or pick up starters. Every top-5 team in 2026 spent $5–10; the $26 QB team was 3-3. Hurts ($7) was lost for the season. | PROPOSED (owner) | `rules/2026-10-21-2027-auction-strategy-notes.md`, `rules/2026-10-14-2027-qb-coordinator-continuity-hypothesis.md` |
| Two top WRs (owner's core approach). JD's 2026 WRs delivered: JSN was the WR1. | PROPOSED (owner) | same |
| Don't starve RB/TE. In 2026 JD spent $153 WR / $36 RB / $1 TE, and RB2/TE/FLEX were weak all year. Keep ~$40–50 for an RB1-level back plus a mid-tier TE instead of a third $19+ WR. | PROPOSED | same |
| K $1 and DEF $1–2 at the draft; hold them. 2026: best kickers were cheap or undrafted; JD churned 8 K/DEF pickups ($10 FAAB). | PROPOSED | same |
| Check the offensive coordinator / play-caller and scheme before paying for a QB. | PROPOSED (hypothesis) | `rules/2026-10-14-...` |

## In season

| Lesson | Status | Source |
|---|---|---|
| Rank every eligible player for start/sit and FLEX; never a two-player duel. | ADOPTED (LR-012) | `rules/learning_rules_v4.json` |
| Anchor FAAB bids to Sparta's own clearing prices; FAAB is real money; keep $10–15 in reserve; pass rather than make a token bid. | ADOPTED (LR-013) | same |
| Roster/lineup advice needs a JD roster < 24h old. | ADOPTED (LR-014) | same |
| Log only real decisions; watches and confirmations are operational notes. | ADOPTED (LR-015) | same |
| Sell name value, buy current production. 2026 W7: Chase (WR15 by points per game, still ranked WR3 rest of season) + Dobbins for Bijan (RB3 by points per game) + B. Robinson. Grade this at season end. | OBSERVATION | `learning/decision_ledger.jsonl` SPARTA-2026W7-TRADE-BIJAN-FOR-CHASE-DOBBINS-20261021-1200 |
| Always enter a backup claim for any must-fill slot (K/DEF/QB) dropping the same player, so the backup cancels itself if the first claim wins. | OBSERVATION | 2026 W7 plan |
| Record W-L luck: points against can swamp lineup quality (2026 JD at 1-5: PF 7th, PA the highest seen). Judge the team by points for, not record. | OBSERVATION | 2026 W7 notes |

## Data and process

- Yahoo is the source of truth for ownership and FAAB. Ask for screenshots when data is older than 24h; check what time a screenshot was taken (2026 W7: a 10:31 PM screenshot was logged as AM).
- Other teams' rosters drift without league-wide transaction pulls (2026: ANT 19, JU 18 rosters in the reconstruction; Hockenson, Mayer and Flournoy moves missed). Fix: pull all 12 rosters each week.
- FantasyPros QB and DEF points don't match Sparta's scoring (6-pt pass TD, Sparta DEF). Use Yahoo for QB/DEF grading.

## Season rollover checklist

Run after the fantasy final (Week 17), and again before the next draft:

1. Finish the season: final OUTCOME_REVIEWs, `season_scorecard.json`, a season review in `learning/weekly_reviews/<season>-season.md`.
2. Season-end analysis: points per auction dollar by position for all 12 teams; K/DEF season totals from Yahoo; grade every trade and FAAB pickup (points after the move per $).
3. Update this file: promote PROPOSED lessons the data supports to ADOPTED (new `learning_rules_vN.json`, AGENTS rule 48); mark the rest OBSERVATION or SUPERSEDED. Keep everything.
4. Keep season files side by side, never overwrite: `data/draft_<season>.json`, season-tagged decisions (`week` plus `season`), `learning/weekly_reviews/<season>-wNN.md`, `intelligence/brain/<season>-wNN-plan.md`. Snapshot end-of-season state (`current_roster_jd.json`, `faab.json`, `transactions.json`) under `data/archive/<season>/` before resetting for the new season.
5. Draft prep (a few days before the auction): read this file and the season's auction notes, then build a price sheet (target $ by tier and position) and record it as a DECISION.
