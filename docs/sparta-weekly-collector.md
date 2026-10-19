# Weekly evidence collection

`python scripts/sparta_collect.py --job <report_card|waivers|injuries|lineup_check>`
writes JSON and Markdown under `intelligence/handoff/2026-wkNN-<job>.*`.
Use `--week N` to select a period explicitly. Outputs are evidence for
`CLAUDE_SPARTA_BRAIN`, with no recommendations, decisions, notifications or
changes to authoritative roster, FAAB, transaction, learning or Pulse files.

## Inputs and authority

The collector chooses the newest completed, Sparta-scoped authenticated Yahoo
API/browser snapshot. Approved weekly API evidence uses the existing
`yahoo_sync.py` client, mapping, pagination, parser and reconciliation in
**report-only** mode. Weekly snapshots stay under
`data/yahoo_api/weekly/2026-wNN/`; historical rosters never replace the canonical
current `data/yahoo_api/latest.json`. `coverage_week` distinguishes roster/stats
period from Yahoo's current league week. Historical evidence is never used to
confirm current free-agent availability.

With API approval still pending, authenticated browser snapshots remain the
fallback. JD screenshot and authenticated read-back evidence can fill JD-only
sections, with separate provenance; they cannot manufacture the other teams'
rosters, budgets or free agents. Missing, stale (>24 hours), wrong-week and
incomplete sections remain visibly PARTIAL/STALE/UNAVAILABLE. Stale or incomplete
ownership evidence yields UNKNOWN availability. Percent rostered is context only.

The schema is `contracts/sparta_handoff.schema.json`. Every section records a
source path, SHA256, observation timestamp and coverage week. Combined job data
references its scoreboard/opponent-roster source sections. JSON is validated,
finite-number checked and read back before publication. Identical evidence
produces no routine commit; source changes produce new provenance hashes.

The exact historical optimizer uses Yahoo eligible positions, unique identities,
actual slots and actual points; it excludes IR slots. Missing points or an invalid
actual lineup produce null totals instead of invented zeros. It searches stored
requested-week API artifacts rather than treating today's roster as historical.
Yahoo weekly points are parsed only with explicit weekly coverage. A current
Yahoo lineup can contain an injured player; this is surfaced as an evidence flag.

## Schedule and credentials

`.github/workflows/sparta_collect.yml` has manual dispatch and paired UTC crons
with an ET/DST guard: Tuesday 09:00 report card, Tuesday 14:00 waivers, Saturday
10:00 injuries, Sunday 10:30 lineup check. GitHub schedules can be delayed and are
not exact-time guarantees. Private-repository reads/writes use authenticated
checkout/GITHUB_TOKEN. Contents write permission and ordinary main protection
permissions are necessary; a protection or concurrent-push rejection fails safely.

No Yahoo API request occurs unless repository variable
`SPARTA_YAHOO_API_APPROVED=true` is explicitly set after provider approval. Existing
`YAHOO_CLIENT_ID`, `YAHOO_CLIENT_SECRET`, `YAHOO_REFRESH_TOKEN`, optional
`YAHOO_REDIRECT_URI` are reused, never printed. Optional `SPARTA_SECRETS_PAT` saves
a rotated token using the existing secret mechanism. Refresh failure produces a
sanitized limitation and qualified cached evidence. No API access was attempted
during this implementation. The workflow performs no durable-state apply.

Official methods reviewed on 2026-10-19:
<https://sports.yahoo.com/developer/docs/#roster-resource>,
<https://sports.yahoo.com/developer/docs/#player-resource> and resource chaining:
`league/<key>/teams/roster;week=N/players/stats;type=week;week=N`.
These are offline-tested transport paths, **not live-validated integration claims**.
Weekly stats extend the existing roster request, rather than adding a new client.

## Current readiness and limits

All four sample handoffs are PARTIAL because available authenticated cached data
does not cover every required section. Complete league collection needs approved
Yahoo API access or a fresh full authenticated browser snapshot. The existing
API parser has no documented player projection source, so API-only lineup checks
remain partial until requested-week Yahoo projection evidence is supplied.
Tuesday report cards require final scores and exact-week actual player points.
Do not estimate transaction FAAB or complete pending reconciliation from this job.

No FantasyPros endpoint is called, no new production FantasyPros ingestion is
activated, and its support request remains unsent. An existing weekly board is
included only as a reference when an explicit PASS validation receipt binds its
SHA256, league, season and week; otherwise it is excluded. The already-approved
board workflow is untouched.

Full testing includes source precedence/scope, DST, stale availability, mixed
Yahoo identifiers, owned-player exclusion, duplicate identities, invalid slots,
missing points, historical selection, repeated scoreboard pairings, schema
checks and safe output writes. The full learning gate retains all653 historical
findings and four approved grandfather warnings.
