# Sparta Brain — PRIME FantasyPros engineering coordination

Status: **offline improvements verified; rankings/projections/injuries remain unvalidated**. No new live provider requests, workflow dispatch, production activation, schedules or purchases in this execution. Yahoo, roster, FAAB, transactions and learning history unchanged.

## Inspected repository state and verified evidence

| Repository | Inspected main SHA | Relevant sources |
|---|---|---|
| Sparta | a0c9a407af636eb236d2cbb838c900732d04ef85 | AGENTS.md, existing integration/pilot docs, scripts/contracts/tests, prior pilot diagnostics in PR2 |
| PRIME private `-NFL-Prop-Odds-Data` | 84a8cf37e71db07ab52cee4fd996d020161eb72f | AGENTS.md, PRIME_SYSTEM_STATUS.md, research/integrations/FANTASYPROS_PUBLIC_V2.md, client/contract/adapter,32 tests, private capture/body/derived provenance |
| PRIME public `NFL-Prop-Bets` | 02355693613234571248f9492effc8d1a3b4d4e0 | AGENTS.md and research/handoffs/2026-10-18-fantasypros-connection-verification.md |

All three AGENTS files read completely. PRIME references were read only. No betting observations, models, outcomes, canonical PRIME identities, bankroll/accounting or unrelated system state were copied into Sparta.

PRIME [replacement-key verification run39083670533](https://github.com/jamesddestefano-ui/-NFL-Prop-Odds-Data/actions/runs/39083670533) was re-queried through GitHub: successful manual run at source863f3ed8ff13de2e4f8b009fb0c2228bc4b43311. It made one news request, category injury, limit1, received2026-10-18T00:41:51.436317Z, HTTP200/schema-valid, one item. Original response SHA256 `aa8ac8b6ccfefa9dd91935d73afd2488995d0b8c466928546e3907c0dd09f7ba`; receipt SHA256 `9c3f32e6899bc2742aeb81d25df19b2fbde7a7152d75f6d6732b08806b9142bd`. Original capture/body hashes, URL, schema and normalized adapter replay revalidated offline in PRIME, one row. Raw news/body/private receipt not copied to Sparta. Timestamp is naive; adapter correctly reports UNKNOWN_TIMEZONE_OR_UNAVAILABLE.

PRIME tests:32 FantasyPros tests passed locally. Existing final/post-merge CI39083764359/39084196222 report success; those CI runs do not prove other endpoint access. Policy readback: routine ingestion, standard probe and one-time connection verification all disabled. No recognized quota headers were captured; plan/usage and other endpoint entitlements remain unknown.

## Comparison and mismatch findings

Both systems use header-only `x-api-key`, the same API base and the **same original supplied OpenAPI**, SHA256 `d76e56d4486716edb6d17137c68d27c4924b111f500abe1cd9e223fb1690adcd`. Parsed contracts are semantically equal. Both specialize generic unions to NFL and normalize YAML-null type tokens. Neither verified contract contains a provider-backed fix for Sparta's failing endpoints.

| Sparta live diagnostic from prior authorized run39085126777 | PRIME evidence | Conclusion |
|---|---|---|
| Rankings: ranking_type_name enum; missing player tier | Only synthetic ranking fixture | No supported enum/optionality correction |
| Projections: fpid/mflid/stats types | Only synthetic projection fixture | No supported coercion or shape correction |
| Injuries: injury_update_date type; status/status_short enums | Only synthetic injury fixture; news item category Injury is a different endpoint | No supported type/status correction |

Prior Sparta pilot diagnostics remain in [PR2](https://github.com/jamesddestefano-ui/sparta-fantasy-football-db/pull/2). They identify schema locations, not actual replacement definitions. News success does not establish access, response shape, PPR semantics, season/week correctness or record counts for rankings/projections/injuries. No live calls were made to resolve those gaps. Do not broaden types/enums, remove required tier, manufacture IDs or select unknown stats structures just to pass.

## Compatible improvements applied to Sparta

Dedicated branch: `codex/prime-fantasypros-methods-20261018`, cut from current main. Existing PR2 diagnostic/error-stop fixes carried forward by cherry-pick4f7b9e0/3abd72e; original branch left intact. This branch overlaps PR2's implementation; reconcile before merging both. PR2's historical audit documentation remains accessible there.

- **Contract integrity:** verify pinned JSON bytes against the existing source manifest before schema use. Reject modified contract bytes instead of silently validating against a changed contract. No contract or provider response coercion introduced.
- **Strict numeric JSON:** use finite parse_float, rejecting1e309 even in otherwise unused additional fields; duplicate keys and NaN/Infinity protections retained. This closes a gap where fetch could accept overflow and publication later fail outside sanitized handling.
- **Transport-boundary timestamps:** capture request start and completed-body receipt before local schema/normalization processing. retrieved_at_utc now means receipt, not end-of-validation. Original response hash remains preserved.
- **Publication provenance:** retain per-item source-time fields verbatim. Normalize only explicitly timezone-aware news/injury publication times; naive/date-only/malformed/overflow dates remain unknown. Response ranking-update timestamps remain aggregate metadata, never asserted individual publication times.
- **Scope provenance:** add explicit requested_season/requested_week and nullable provider_season/provider_week. Existing scope checks remain; absent provider context stays absent instead of being silently manufactured from request parameters.

Existing response-schema/identity/count/PPR checks, redirect refusal, bounded transport, secret-echo rejection, no-partial-batch publication, UNKNOWN availability and unvalidated_for_decisions remain. Error-envelope stop handling includes numeric401/403/429. Credentials stay in the configured header; no new credential copied from PRIME.

PRIME methods deliberately not imported: its betting-specific adapters, feature candidates and canonical identity/game crosswalks; its request-ledger/storage hierarchy; raw-body publication. Persisted reservation-before-call and private failed-body retention are useful future designs, but Sparta's public/private retention policy and explicit future authorization must be settled first. No competing store or new live path created. Blanket format checking was not copied because supplied timestamp examples conflict with their formats; strict structural validation and explicit provenance remain.

## Tests and review

Baseline:43 main tests, plus prior diagnostics fixes yields47. Added six PRIME-method regression tests; **53 total tests pass** via `python -m unittest discover -s tests -v`. Tests are synthetic/offline, not evidence of new provider endpoint access.

Red→green reproduced numeric overflow acceptance, manifest tamper acceptance and receipt time measured after validation. Naive/date-only/aware timestamp cases verify semantics and separate provider/request scope. Independent review identified conversion overflow and aggregate ranking update misattributed as player publication; both reproduced and fixed; final53 pass. The reference PRIME suite's32 tests also pass. `git diff --check` passes.

`python scripts/validate_sparta.py` passes:12 teams,204 draft records,17 current roster entries,157 transactions; stored FAAB33/waiver priority3. These values are repository state, not a new Yahoo observation. `python scripts/validate_learning.py` continues to fail653 existing errors; neither validator nor history changed. No repository-wide green claim or check bypass.

No changes to authoritative data/, learning/, existing Pulse mirrors/cursors, contracts/ or workflows. No lineup, roster, transaction, accounting, model-weight or availability recommendation. All writes restricted to existing engineering modules, offline tests, plan and handoff/receipt.

## Remaining blockers and Brain next action

Keep FantasyPros research unvalidated and production disabled. Obtain provider-confirmed sanitized examples or revised contract for each failing endpoint. Compare exact types/enums/counts/PPR identity/context, write fixture-backed explicit adapters, then separately authorize bounded validation if desired. **This directive grants zero new live requests.** PRIME news evidence cannot substitute for those checks.

Use GitHub receipt and PR for final branch SHA, readback and CI disposition. No claim of messaging Brain chat directly. Preserve Yahoo authority, FAAB-only pickup cost, immutable decisions and existing research hierarchy.
