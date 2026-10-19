# Sparta weekly evidence collector implementation plan

Owner supplies full requirements and autonomous execution. Extend existing Yahoo sync/parsers and board slot definitions; no duplicate client/database, notifications, recommendations or DECISIONs.

Design: scripts/sparta_collect.py reads the newest qualified official API snapshot or authenticated browser snapshot, then uses source-labeled screenshot/connected evidence for missing JD-only sections. Every section has its own source/hash/observation/week, freshness, coverage and missingness. Optional explicitly approved Yahoo refresh delegates existing yahoo_sync in report-only mode. No FantasyPros calls; stored board reference only with hash-bound validation receipt.

Four jobs: report_card (previous week, final-score/complete historical-roster gates, exact eligible-slot optimization), waivers (position-grouped Yahoo availability and all FAAB), injuries (JD and explicitly mapped next opponent), lineup_check (current slots, injuries/byes/IR flags and only sourced projections). Never estimate missing points/FAAB, fabricate empty successful sections or treat public rostered percentages as availability.

Add contracts/sparta_handoff.schema.json and offline tests for source preference/isolation, stale/partial data, exact historical week, no greedy lineup errors, IR exclusion, current-lineup flags, unknown FAAB, board validation, side-effect boundaries and ET DST schedule dispatch. Use existing fp_weekly.current_week with ET date and sparta_board.STARTER_SLOTS/FLEX_OK, not parallel season/lineup configuration.

One workflow with Tue09:00/Tue14:00/Sat10:00/Sun10:30 America/New_York triggers and manual dispatch. Dual UTC cron plus ET guard handles DST; serialized authenticated writes, pull --rebase, output readback, no notifications. GitHub delays remain best effort. Only handoff outputs committed by default; explicit approved refresh can update existing Yahoo API snapshots/report/history only, never durable transactions/FAAB/roster.

Validation: RED→GREEN tests, full suite/current validators/regression gate, independent review, one offline sample per job, protected-path comparison, fresh pull --rebase before branch push, PR only (new build not merged unless instructed).
