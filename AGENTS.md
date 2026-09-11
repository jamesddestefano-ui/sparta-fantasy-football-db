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
14. Waiver/FAAB recommendations after Week 1 must use the current real-money FAAB balance stored here.
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

## Required operational loop

USER UPDATE → READ CURRENT REPOSITORY STATE → ANALYZE → VALIDATE LEAGUE + DATA INTEGRITY → WRITE DATABASE CHANGE → COMMIT TO GITHUB → READ BACK / VERIFY → REPORT RESULT.
