# FantasyPros NFL API — Sparta read-only pilot

Status: OFFLINE IMPLEMENTATION ONLY; not operational or ready for production.
The authoritative OpenAPI specification, securely rotated credential and quota
confirmation were unavailable during implementation. All request definitions and
record-field mappings are provisional. Synthetic tests validate local safety
behavior; they do not validate provider contracts. No authenticated API request
has succeeded or been attempted in this work.

## Authority and isolation

FantasyPros is NFL research intelligence only. Authenticated Yahoo Sparta state
controls ownership, availability, roster, transactions, FAAB, waivers and lineup.
GitHub stores durable history; Sparta Brain retains final synthesis authority.
No Yahoo transaction implementation, scheduled collection or workflow is added.
Outputs always remain `unvalidated_for_decisions`; availability is `UNKNOWN`.

The October 17 directive models $1 real-money cost per completed pickup plus
applicable waiver FAAB. This conflicts with AGENTS.md rules 14/50 and
learning_rules_v3 (winning FAAB only). The new research artifact flags the
conflict; historical accounting and rule files are unchanged.

## Offline verification

```bash
python -m unittest discover -s tests -v
python scripts/validate_sparta.py
python scripts/validate_learning.py
python scripts/fantasypros_evaluate.py --comparison
```

Learning validation already fails on main's heterogeneous immutable ledger
formats. Do not rewrite history or loosen validation to make this pilot green.
See `fantasypros_integration_report.md` for the actual results.

## Contracts requiring authoritative verification

| Endpoint | Implementation state |
| --- | --- |
| `/nfl/2026/consensus-rankings` | Existing provisional FLEX/PPR request, hardened local validation |
| `/nfl/2026/projections` | Existing provisional weekly request; missing PPR metadata explicitly unverified |
| `/nfl/injuries` | Existing provisional request; historical week scope explicitly unverified |
| `/nfl/news` | Deferred pending specification and plan access |
| `/nfl/compare-players` | Deferred pending specification and plan access |
| `/nfl/2026/player-points` | Deferred pending specification and scoring rules |
| `/nfl/2026/rankings/experts` | Deferred pending specification and plan access |

Rest-of-season projections are not implemented. Do not assume the provider uses
these provisional parameters, field names, result arrays or timestamp formats.
The next engineer must validate request parameters and full response schemas
against the supplied OpenAPI, add schema-derived fixtures and then run live tests.

## Secure manual pilot, after resolving blockers

Rotate the exposed key; inject the replacement as `FANTASYPROS_API_KEY` using
approved secret management. Never place it in files, command arguments, URLs,
logs, notebooks or prompts. `--credential-rotated` is an operator attestation,
not proof of rotation. Default operation sends no requests without it and a
confirmed request budget. No secret store was created or modified here.

After contract validation and confirming plan quota, the intended three-request
Week 6 invocation is:

```bash
python scripts/fantasypros_ingest.py --season 2026 --week 6 \
  --credential-rotated --request-budget 3 \
  --output-dir /tmp/sparta-fantasypros-review
```

Retries default to zero. `--retries 1` permits up to six total requests for all
three kinds; the request budget must cover the worst case. At most two retries
are supported; only transient HTTP/network failures retry. Retry-After over 30
seconds stops for deferred retry. HTTP redirects are refused to protect headers.
No quota discovery endpoint is assumed.

All requests must finish and validate before publication. One immutable JSON
batch is published atomically with a content-derived SHA-256 identity; identical
provider content does not create another file. First retrieval timestamp is
retained for a repeated batch. Outputs include provider timestamps when present,
retrieval time, response hashes, quality flags, duplicate counts and explicit
contract status. Missing provider timestamps or Yahoo mappings are flagged;
contradictory identities/context, empty arrays and stale/future timestamps fail.
The provisional freshness window is 48 hours and 5 minutes future tolerance;
historical provider timestamps will require a separate as-of validation mode.
No inference of identity from name matching or of availability is performed.

Only `intelligence/fantasypros/` or an external review directory is permitted.
Never point an external review directory at another authoritative datastore.
No protected league files, decisions or Pulse cursor are written.

## Research evaluation

`fantasypros_evaluate.py --rows paired.json` consumes an explicit common cohort:
`player_id` (string), season 2026, week 1–18, scoring `PPR`, numeric `fantasypros`,
`sparta`, `actual`, `lower`, `upper`. Fantasy points must be finite and within
±1000. Duplicate player/weeks and incomplete paired rows are rejected. Intervals
are caller-supplied; label their model and nominal coverage in the input manifest.
Metrics include MAE, RMSE, bias, interval coverage/width and within-week pairwise
FantasyPros ordering accuracy. They are descriptive; forecast timing/provenance
is not automatically verified. No weights are promoted. Actual scoring import,
start/bench outcomes, waiver ROI and trade evaluation remain future adapters.

The Week 6 comparison references immutable October 16/17 decisions and hashes the
source ledger. Recorded usage favors Wicks; injury-contingent opportunity favors
Cowing. FantasyPros numbers and verified uncertainty intervals are null. This is
historical evidence review, not a fresh prediction, ownership check or lineup edit.
