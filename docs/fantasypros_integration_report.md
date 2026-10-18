# FantasyPros integration review report

Status: **PARTIAL — offline contracts validated; live authentication/quota unverified**.
Repository: jamesddestefano-ui/sparta-fantasy-football-db.
Feature branch: feature/sparta-fantasypros-integration; deployment target: main,
now explicitly requested by the repository owner for the manual Actions workflow.
Starting commit: acb3611ed5001d286c9bd54630b3bfa6e1ff5cfd.
Intervening main merged: ba436f7fa102dea9f577b9cffc86e6ec0624a6e7 (Pulse updates only).
Final SHA and Actions installation/run evidence: delivery message and the verified
GitHub main history (a commit cannot include its own SHA).
Draft PR: https://github.com/jamesddestefano-ui/sparta-fantasy-football-db/pull/1.

## Implementation

All seven requested endpoint adapters now use the supplied OpenAPI structure:
consensus, projections, injuries, news, compare, player-points and experts.
Rest-of-season projections use ros=true. Default all remains exactly three pilot
calls; extra endpoints require explicit selection. Pilot projections deliberately
request WR only, including Wicks/Cowing's position, due unresolved source-schema
issues in DST/kicker variants. No FantasyPros IDs are guessed from names.

The attached .json file actually contains YAML. Pinned JSON conversion and source
hash provenance live under contracts/. Runtime uses pinned jsonschema (justified
for nested allOf/oneOf/ref validation); YAML is not a runtime dependency.
Documented normalizations: YAML-null type entries, nullable support, NFL-specific
generic parameter enums. Format annotations are not universally enforced because
the source's timestamp examples conflict with their offset requirements.

Fixed source-incompatible assumptions: required projection position parameter;
fpid/name/position_id/stats array; explicit stats.points_ppr even when the top-level
scoring label is STD; ranking player_position_id/Yahoo ID and epoch timestamp.
Individual positions must match the requested slice, and declared counts must
match received records. Empty/malformed/conflicting/truncated responses fail.

Transport uses 15-second timeout, bounded size, no credential-bearing redirects,
zero retries by default and at most two opt-in transient retries. API errors omit
bodies/credentials. Decoded secret echoes, duplicate JSON members and nonfinite
values are rejected. Successful batches preserve provider/retrieval timestamps,
raw hashes, mappings, quality flags, original fields and normalized PPR values.
Publication is immutable, atomic and content-deduplicated; no partial batches.
All results remain unvalidated_for_decisions; availability stays UNKNOWN.

## Manual workflow and secret

.github/workflows/fantasypros_sparta_pilot.yml: workflow_dispatch only,
contents:read, pinned actions, Python 3.12, serialized concurrency, tests first.
Only sanitized counts/status are uploaded with one-day retention; no raw player
payloads, credentials or authoritative league data leave the runner as artifacts.

Owner reports adding FANTASYPROS_API_KEY as an Actions secret; its value has not
been requested or inspected. Preflight verifies Boolean presence, not successful
authentication. Default budget=0 makes no API calls. Live pilot requires exactly
three confirmed requests, a provider quota evidence reference and rotated-key
attestation. No quota endpoint exists in the supplied OpenAPI. Secret presence
never establishes quota or credential rotation. Current quota is unconfirmed.

## Tests and review

python -m unittest discover -s tests -v: **38 passed**, including supplied contracts,
all adapters, ROS, PPR selection, context/identity/count checks, secret echo,
retry bounds, partial-response rejection, immutable publication and quota gates.
These are offline synthetic tests, not authenticated provider responses.
python scripts/validate_sparta.py: PASS (12 teams,204 draft,17 roster,157 transactions).
python scripts/validate_learning.py: FAIL with **653 pre-existing errors**.
Historical ledger and validator unchanged; no relaxation or history rewrite.
git diff --check: PASS. Workflow YAML parsed and dispatch/read-only/concurrency
invariants checked. Main read-back/run results are reported after installation.

Independent review reproduced credential-echo escaping and numerical overflow;
regressions verify their fixes. A second review found per-row position/count
validation gaps; reproduced and fixed with rejection tests. Neither review found
apparent authoritative-state writes or redirect/header leakage. No review claims
live correctness.

## Results and data quality

Authenticated endpoints: **none yet**. No FantasyPros live calls made in this
session before quota confirmation. No provider record counts can be reported.

Week 6 analytical artifact references immutable Oct16/17 decisions with source
ledger hash. Recorded Wicks target share/usage favors Wicks; recorded SF injuries
create Cowing opportunity. Cowing's recorded two targets/50% routes and Monday
status uncertainty weaken certainty. FP ranks/projections/verified intervals are
null; independent underlying NFL sources and matched actual outcomes are missing.
This is historical evidence review, not a live prediction or Yahoo lineup change.

Ranking epoch timestamps have a provisional 48-hour freshness/5-minute future
window. Injury/news responses do not guarantee season/week fields or complete
identity metadata; flags preserve these limits. Expert publication timestamps
without offsets require review. Historical as-of evaluation needs a separate
validated timestamp mode. No predictive improvement or model weight promotion.
Current user $1 pickup-plus-FAAB instruction conflicts with AGENTS14/50 and v3
FAAB-only history; research flags it, accounting remains unchanged.

User-facing ownership filtering is not automated: raw NFL intelligence must be
reviewed against current authenticated Yahoo proof before Brain recommendations.
No player availability is inferred. No cross-source Pulse dedupe/cursor advance
is performed just because FantasyPros data is collected.

## Files

Created: .github/workflows/fantasypros_sparta_pilot.yml; requirements-fantasypros.txt;
contracts/fantasypros_public_v2.openapi.json; contracts/fantasypros_source.json;
scripts/fantasypros_contract.py; scripts/fantasypros_actions.py;
scripts/fantasypros_evaluate.py; tests/fantasypros_fixtures.py;
tests/test_fantasypros_contract.py; tests/test_fantasypros_actions.py;
tests/test_fantasypros_evaluate.py; .gitignore; design/plan/report docs;
intelligence/fantasypros/research/2026-week06-wicks-cowing.json;
intelligence/fantasypros/research/offline-validation.json.
Modified: scripts/fantasypros_ingest.py; tests/test_fantasypros_ingest.py;
docs/fantasypros_sparta_pilot.md.
No implementation changes to data/,learning/,Pulse cursors or existing intelligence.
The merge imports only upstream Pulse updates; FantasyPros did not generate them.

## Deepnote / Hugging Face

Deepnote project 4e60d132-6e5b-45ae-b9c5-9765bb95e541, notebook
6535e38d6bcc4abba510d364dbf141ca: two read-back blocks, evaluator/comparison/manifest
analytical files pinned to 119b393, before later evaluator numerical hardening.
Never run; paired cohort empty. Project creation/file tools automatically started
Basic CPU machine time; cost not reported. Explicit shutdown returned stopped.
Synchronize reviewed code before future execution. No credential or league DB.

[Analytical notebook](https://deepnote.com/workspace/james-4106-48eceaa3-2249-4b92-ab08-e63f2de0a40b/project/4e60d132-6e5b-45ae-b9c5-9765bb95e541/notebook/6535e38d6bcc4abba510d364dbf141ca?utm_source=openai&utm_medium=mcp&utm_campaign=openaimcp&utm_content=6535e38d6bcc4abba510d364dbf141ca&utm_term=get_notebook)

Hugging Face model search returned UNAVAILABLE. No model downloads, datasets,
paid jobs, training or model deployment. Paired descriptive baseline harness
supports future repeated holdout evaluations; no improvement claim exists.

## Remaining gates

Verify Actions installation and secret-presence preflight; confirm quota and key
rotation without exposing values; then run one three-request pilot. Record actual
HTTP200/authentication/counts and independently reconcile IDs/scoring/timestamps.
Resolve baseline learning-validation incompatibilities separately, preserving
history. Independently corroborate Week6 usage/injuries and align pre-kickoff
forecasts/actual outcomes. Resolve source-schema issues before broader positions.
No hourly collection, paid modeling, rule changes or production intelligence
promotion until validated evidence and required authorizations exist.
