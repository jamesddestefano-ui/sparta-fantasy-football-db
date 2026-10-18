# FantasyPros NFL API — Sparta read-only pilot

Status: workflow installed on main;38 local/Actions tests pass; secret presence verified.
Manual preflight39082871937 sent zero requests because quota/rotation gates were
not confirmed at that time. The owner has since confirmed rotation as
USER_CONFIRMED. Quota remains unverified, so no new pilot was dispatched.
Live authentication remains unverified. See the integration report.
No recurring schedule, transactions, decision-weight changes or production promotion.

## Authority and isolation

Authenticated Yahoo Sparta data controls live league truth; GitHub preserves
history; FantasyPros and Pulse provide NFL research; Sparta Brain remains final
synthesis authority. Every output is `unvalidated_for_decisions`, availability
UNKNOWN. No ownership inference from rankings or roster percentages. Raw provider
collection is not a user-facing recommendation feed: review/filter only JD-owned,
confirmed Sparta-available or material opponent developments using current Yahoo
proof before surfacing decisions. Automated ownership filtering is not enabled.

October 17 instruction models $1 per completed pickup plus applicable FAAB;
AGENTS 14/50 and learning_rules_v3 disagree. Research flags the conflict without
changing historical accounting.

## Supplied OpenAPI contract

`contracts/fantasypros_public_v2.openapi.json` is a JSON conversion of the supplied
YAML attachment. Original filename and SHA-256 are in `fantasypros_source.json`.
The source is retained without semantic changes. Runtime normalizations are
explicit in `scripts/fantasypros_contract.py`: YAML null members of `type` arrays
become JSON Schema `"null"`; OpenAPI `nullable` is honored. Generic SPORT oneOf
parameter enums overlap, so NFL-specific enums validate NFL parameters.
Format annotations are not blanket-enforced because source timestamp examples
omit offsets despite `date-time` annotations; safety timestamp checks are separate.
This verifies structure against supplied contracts, not actual provider behavior.

| Kind | Request/response behavior |
| --- | --- |
| consensus | FLX, PPR, type WW, week; documented player_position_id/Yahoo ID and epoch last_updated_ts |
| projections | Required position WR, positions WR, week; fpid/name/position_id/stats[].points_ppr |
| injuries | year/week/include_probabilities; name/yahoo_id and practice statuses; no response season/week/position fields guaranteed |
| news | limit 10/order_by updated; item IDs allow multiple news items for one player |
| compare | Two supplied verified FP IDs; weekly WR and player details; select PPR ranking map |
| points | start=end=requested week; WR, PPR, min false; verify weeks key |
| experts | WR, type WW, PPR; no supported week query; returned week must match requested pilot week |
| projections_ros | Same WR slice with documented ros=true; returned week must match requested as-of week |

Projection top-level scoring may be STD: the documented stats contain separate
points, points_half and points_ppr. Only points_ppr enters normalized PPR values.
Conflicting multiple stat rows are rejected rather than silently averaged.
The source DST required-field typo (`points_half def_sack`) and absent kicker
projection variant are unresolved; this pilot intentionally requests WR only.
No inference of FP IDs by approximate names. Rankings/injuries provide Yahoo IDs;
missing mappings and positions are explicit quality flags. ID reconciliation with
current authenticated Yahoo remains a decision gate.

## Tests and dependency justification

```bash
python -m pip install -r requirements-fantasypros.txt
python -m unittest discover -s tests -v
python scripts/validate_sparta.py
python scripts/validate_learning.py
python scripts/fantasypros_evaluate.py --comparison
```

Pinned jsonschema is the one added runtime dependency: validating nested allOf,
oneOf, refs, required fields and types from OpenAPI correctly warrants a maintained
validator. YAML was converted locally, so PyYAML is not a runtime requirement.
Learning validation already fails on heterogeneous immutable records; do not
rewrite history or weaken it for this integration.

## Manual GitHub Actions

`.github/workflows/fantasypros_sparta_pilot.yml` uses workflow_dispatch only,
contents:read, pinned actions, Python 3.12 and serialized concurrency. Unit/contract
tests run before secret injection or ingestion. Learning validation failure is
reported explicitly and does not grant permission to promote intelligence.

The repository owner reports adding FANTASYPROS_API_KEY. Workflow preflight checks
presence as a Boolean only; no secret value is read through tools, printed or
persisted. A present secret is not proof of successful FantasyPros authentication
or rotation. Default dispatch budget 0 runs tests/preflight with no API calls.
Live ingestion needs all three inputs: confirmed_request_budget=3, a reference to
verified provider quota evidence, and credential_rotated=true. Do not supply these
assertions without evidence. The supplied API has no quota-inspection endpoint;
quota cannot be inferred from key presence, API pricing or a 200 response.

Live mode makes exactly three calls (no retries), season 2026/week 6. No paid
service is added. Never enter credentials in dispatch inputs. The only artifact
is a sanitized status/count summary, retained one day; raw provider data is not
uploaded and contains no authoritative league information. GitHub controls
artifact access. Default preflight is safe for a public repository because the
summary contains no secret values, player-level data or league state.

## Local authenticated pilot after resolving quota and rotation

Inject rotated key using approved secret management, never a command argument,
.env committed file, URL, notebook or prompt. Once contracts, plan entitlement
and quota are confirmed:

```bash
python scripts/fantasypros_ingest.py --season 2026 --week 6 \
  --credential-rotated --request-budget 3 --retries 0 \
  --output-dir /tmp/sparta-fantasypros-review
```

`--kind all` means only the three pilot endpoints. Other kinds require explicit
selection; compare also requires --player-ids with two verified colon-delimited
IDs. Default retries zero; at most two opt-in retries for transient failures,
with worst-case budget coverage required. Redirects are refused. Response size
is bounded. JSON duplicate keys/nonfinite values, invalid schemas, bad identities,
context conflicts, empty arrays and stale/future ranking timestamps fail closed.

Batch publication is atomic, immutable and content-deduplicated. First retrieval
time is preserved on repeated identical provider content. Original provider fields,
raw response hashes, retrieval timestamps, mapping fields and quality flags are
retained. Provider timestamps missing or without proven timezone remain review
gates. News/injuries do not prove their historical week in the response. Existing
48-hour/5-minute future safety window requires a separate as-of mode for older
historical forecasts. Nothing advances a Pulse cursor.

Only intelligence/fantasypros or an external review directory is allowed. Never
point an external output at another authoritative datastore. No partial batch is
published on any endpoint failure.

## Research

The Week 6 artifact hashes immutable October 16/17 decisions. Recorded workload
favors Wicks; recorded injury-created opportunity favors Cowing. FP values remain
null until actual authenticated data exists. This is historical evidence review,
not a new prediction or lineup edit. Underlying route/injury sources still need
independent verification.

`fantasypros_evaluate.py --rows paired.json` expects player_id, season, week,
scoring=PPR, fantasypros, sparta, actual, lower and upper on a common cohort.
Metrics are descriptive; pre-kickoff provenance and nominal interval coverage
must be recorded by the caller. Empty/incomplete cohorts yield no accuracy claim.
No weights are promoted. Deepnote artifacts remain analytical and have not run.

## Explicit one-pilot authorization with unknown quota

The owner superseded the quota-confirmation gate for one execution, maximum3
requests, zero retries. user_authorized_unknown_quota=true is a separate manual
input; it never claims quota_confirmed=true. Rotation remains USER_CONFIRMED.
Authorization does not purchase credits, upgrade a plan, recur, or promote data.
Sanitized per-endpoint audit records HTTP status, schema result, count and timing.
Non200/network failures stop remaining calls; HTTP200 local validation failures may
complete the remaining authorized endpoint tests, with no partial batch accepted.

## Latest pilot result

Run39084236479 at2026-10-18T00:50:15Z used code763cda78 and consumed the one-pilot
user authorization. Exactly3 calls returnedHTTP200; all response validations
failed; no batch accepted.43 Actions tests passed. No validated record counts or
valid authenticated data established. No rerun under this authorization.
Production intelligence remains disabled; see integration report for evidence.
