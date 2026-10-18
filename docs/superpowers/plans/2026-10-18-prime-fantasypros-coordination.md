# PRIME / Sparta FantasyPros engineering coordination

Execute inline; current owner directive authorizes offline improvements and GitHub handoff. No provider calls, dispatch, activation, purchases or recurring collection.

Baseline: Sparta main a0c9a40, PRIME private84a8cf3, PRIME public0235569. Read all AGENTS and relevant FantasyPros integration/evidence docs. Preserve state isolation. Prior PR2 diagnostics fixes carried into new branch by cherry-pick; old branch remains intact.

1. Verify original PRIME news capture hashes/schema offline, rerun32 FantasyPros tests; compare pinned contracts and authenticated evidence. Only news is verified; synthetic fixtures cannot fix other endpoint contracts.
2. Add red→green offline regressions: JSON overflow in unused fields rejected; changed pinned contract rejected; request/receipt timestamps taken at transport boundary; naive/date-only publication remains unknown with raw value preserved. Implement minimal changes in existing contract/ingestion modules.
3. Full suite, Sparta validation and baseline learning failure; independent engineering review; no authoritative-state diffs. Commit, push dedicated branch, open PR, read back exact remote bytes/SHA and handoff.

Review focus: credential echoes; cached contract integrity; provider vs request scope; naive timestamps becoming fabricated UTC; extra fields containing infinite numbers. No weakened schema, PRIME identity/feature/betting model import, or live-access claim for rankings/projections/injuries.

Ledger: prior fixes cherry-picked as4f7b9e0/3abd72e;47 Sparta tests pass;32 PRIME FantasyPros tests pass. Raw PRIME response remains only in reference repository, no copy into Sparta. Provider mismatches remain blocked pending actual endpoint evidence.

Implementation/review complete: six regressions and53 Sparta tests pass;32 PRIME tests pass. Review findings fixed RED→GREEN: aware-time overflow, aggregate update misattribution. No provider-contract changes justified. No new live request. Final commit/remote readback/CI disposition in PR handoff.
