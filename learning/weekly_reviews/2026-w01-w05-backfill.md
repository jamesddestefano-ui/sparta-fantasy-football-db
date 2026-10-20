# PRIME SPARTA WEEKLY LEARNING REVIEW — Weeks 1–5 backfill

Week: 2026 Weeks 1–5 (graded late, in one pass)
Review completed_at_et: 2026-10-19T23:30:00-04:00 (Brain / Claude)
Source: James's Yahoo Matchup screenshots for every week, starters and full bench (sent in chat 2026-10-19 ~22:45 ET). Moves: `data/transactions.json`. Grades are in `learning/decision_ledger.jsonl` (OUTCOME_REVIEW events). Process grades use only what was known when each call was made.

## RESULTS AND LINEUP EFFICIENCY
| Wk | Opponent | JD | Opp | Result | Best possible | Left on bench | Eff. |
|---|---|---|---|---|---|---|---|
| 1 | AMON A ROLL | 153.22 | 173.44 | L | 169.22 | 16.00 | 90.5% |
| 2 | FOCUS | 142.56 | 182.34 | L | 157.36 | 14.80 | 90.6% |
| 3 | X-Factor | 113.08 | 111.78 | W | 121.86 | 8.78 | 92.8% |
| 4 | SHOWSTOPPERS | 144.12 | 164.40 | L | 160.92 | 16.80 | 89.6% |
| 5 | CLIN-TON POR-TIS | 117.12 | 138.66 | L | 126.60 | 9.48 | 92.5% |
| 6 | The U | 120.92 | 152.60 | L | 127.42 | 6.50 | 94.9% |

Season: 72.36 points left on the bench (91.8% average). A perfect lineup would not have flipped any of the five losses (closest: Week 4, 160.92 vs 164.40).

## BEST DECISIONS
- SPARTA-2026W3-WILSON-FOR-HOLANI: Emanuel Wilson for $8 → 27.00 in W4, 13.20 in W5. A / B.
- SPARTA-2026W4-WILSON-START-PRICE-OUT + WILSON-XTD-HOLD: Wilson over Dobbins (+19.8). A / A.
- SPARTA-2026W1-VELE-START-OVER-DOBBINS: +16.3. A / B.
- SPARTA-2026W4-KINGKONG-TRADE-ALLEN-REVIEW: kept Braelon Allen (18.60 in W5). A / B.

## WORST DECISIONS
- SPARTA-2026W4-OLLIE-GORDON-ADD: would have dropped Wilson the week he scored 27.00; contradicted the Wilson HOLD a day later. D / C.
- SPARTA-2026W4-WICKS-SMITH-THU-DNP-WATCH: kept Wicks (4.80) in FLEX over Vele (17.40). D / C.
- SPARTA-2026W3-HENRY-WAIVER-WATCH: passed on Hunter Henry while JD's TEs scored ~2/week; Henry scored 14.80 against JD in W6. D / C.
- SPARTA-2026W2-HOLANI-FOR-FIELDS: $1 churn, one bench week. D / C.

## GOOD PROCESS / BAD RESULT
- SPARTA-2026W2-DOBBINS-OVER-VELE (and its 08:11 restatement): Harvey-out role bump didn't show (3.60 vs Vele 11.40). D / B.
- SPARTA-2026W2-WAIVER-LADDER-MARKET: market-correct $12 bid won Raheim Sanders, who never started; ladder #2 Allen came free anyway. C / B.

## BAD PROCESS / GOOD RESULT
- None identified.

## MISSED OPPORTUNITIES
- Tight end all season: starters scored 0.00, 6.60, 1.20, 0.00 in Weeks 3–6.
- FLEX: the best FLEX option sat on the bench in W1 (Wicks 15.30, Douglas 14.40), W2 (Worthy 13.50), W4 (Vele 17.40) and W5 (Dobbins 15.40).

## SIGNALS THAT WORKED
- Backfield role change / lead-back volume (Wilson W3–W4; Allen with Hall out).
- Holding through practice-report noise (Chase W5, JSN W6).

## SIGNALS THAT FAILED
- Single-report role bumps for a backup (Dobbins W2 with Harvey out).
- Prior target share carried into a changed QB/WR room (Wicks W4, W6).

## DATA QUALITY ISSUES
- Weekly results were not stored anywhere until today; fixed by `matchups` and `weekly` in `learning/season_scorecard.json`.
- Recorded FAAB bids sum to $61 while Yahoo shows $33 left of $100 ($67 spent): $6 of free-agent costs not recorded.
- Many restatements, watches and admin confirmations were logged as DECISIONs (17 of the 54 reviews so far are excluded from counts for that reason).

## TIMING ISSUES
- None material in Weeks 1–5.

## NFL PULSE PERFORMANCE
- No Week 1–5 decision graded here recorded pulse_used=TRUE; season aggregates unchanged (see `intelligence/sparta_pulse_learning.json`).

## RULE CHANGES PROPOSED
- FLEX rule: every start/sit note ranks ALL eligible bench players with their projection (seen in W2, W4, W6 — repeated evidence, 3 weeks).
- Waiver bid rule: anchor bids to Sparta's own clearing prices for hot RBs ($12 Sanders, $27 Shipley); our $4–$7 bids lost or were irrelevant (W2, W5 — 2 examples, watch one more).
- Drop rule: never name a current starter as the drop for a speculative handcuff (W4 Gordon).
- Logging rule: restatements, watches and confirmations go in as operational entries, not DECISIONs.
- (From W6) Roster/IR advice needs a JD roster observation under 24h old.

## RULE CHANGES ADOPTED
- None written to `learning/rules/` yet; the FLEX rule now has 3 weeks of evidence and is ready to adopt in the next rules version.

## RULES REJECTED DUE TO INSUFFICIENT SAMPLE
- "Never pay $10+ for a backup RB" — one example (Sanders); keep tracking.

## WEEK SCORECARD (Weeks 1–6 combined, calibrated calls only)
- total material decisions: 37 counted (54 reviewed; 17 excluded as restatements/watches/admin)
- followed recommendations: 26 (17 W / 5 L / 4 N)
- ignored recommendations: 5 (recommendation was right in 2: Tucker hold, Packers hold; James's call was better in 2: Gordon, Wicks W6)
- outcome grade distribution: A10 B10 C7 D8 F2
- process grade distribution: A8 B20 C7 D2 F0
- confidence calibration notes: conf 4 = 13-6-6 (52%), conf 3 = 4-3 (57%), conf 5 = 2-1 — confidence is not yet separating good calls from bad ones.
- transaction fees incurred: $0
- FAAB spent: $61 recorded ($67 per Yahoo balance)
- pickup regret: Sanders $12, Gadsden $12, Holani $1
- drop regret: Tre Tucker (26.70 against JD in W6)
- successful early adds: Braelon Allen $1, Emanuel Wilson $8

## NOTES
Do not rewrite historical recommendations. Grade process only from information available at decision time. Prefer multi-week evidence for rule changes unless a clear structural defect was exposed. NFL Pulse usefulness must be judged on factual accuracy, timeliness, decision impact, mistake prevention, roster value, false alarms, and duplication—not merely the fantasy outcome. Do not double-count repeated reporting of the same underlying NFL fact.
