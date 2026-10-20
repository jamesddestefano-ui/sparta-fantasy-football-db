# Yahoo CI and board receipt handoff — 2026-10-20 UTC

Base main: `b0afd4142f8b811d285c05aa6ab7e4b7d30ff24d`.
Branch: `codex/yahoo-ci-board-receipt-20261020`. PR head is recorded in GitHub.

## Reproduced Yahoo test failure

A local depth-1 clone on Python 3.12 with the workflow's dependency requirement
and `python -m unittest discover -s tests` reproduces exactly one error among115
tests: `test_frozen_653_inventory_reproduces_from_original_git_commit`.
`git archive d8b72fab79c61d9ec8814f513483b63f73a908f7 ...` fails with
`fatal: not a tree object` because shallow checkout omits the historical evidence.
Fetching full history makes the same115 tests pass. The test is unchanged.

Yahoo sync, weekly board and manual pilot all run the full suite and had the
same checkout defect. Each now uses `fetch-depth: 0`, matching validation and
collector workflows. A configuration regression test protects all full-suite
workflows. No schedule, provider-call, authorization, quota or secret behavior changed.

## Existing board validation receipt

The existing board workflow now runs `sparta_board.py --validate-only` immediately
after building the board. This calls the existing `validate_sparta.py`, then
rebuilds offline with the existing `build_board` and compares it to the exact
saved JSON. No new provider schema, weakened checks or extra FantasyPros calls.

It atomically writes and reads back
`intelligence/board/2026-wNN.validation.json` with `status` and `board_sha256`, as
required by the collector. Metadata explicitly identifies the validation scope
and `provider_contract_validated: false`. PASS means Sparta-state validation and
builder/read-back agreement; it does not resolve the outstanding provider contract.
The existing commit step already stages the board directory, including receipts.
Failure writes FAIL in place of any previous PASS and stops before commit.
Changing board bytes invalidates the collector's hash match.

## Validation and safeguards

Full suite:120 offline tests pass. Existing Sparta and learning validators pass;
regression gate passes with all653 historical findings and four approved warnings.
Tests cover valid receipt consumption, changed board bytes, edited league scope,
invalid FAAB state revoking a previous receipt, and changed input rejection.

No live Yahoo/FantasyPros call was made. No authoritative data, historical ledger,
Pulse cursor, existing board content, handoff schedule or provider contract changed.
The local waivers preview from the preceding task remains untracked and is excluded
from this PR. Provider support draft remains unsent. Review this PR before merging;
automatic acquisition still depends on existing provider approval and credentials.
