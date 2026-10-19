# Draft support request — FantasyPros Public API v2 contract mismatches

Status: prepared for the owner; **not sent**. No new live request authorized or made.
Destination from supplied contract: https://secure.fantasypros.com/support-request/

Subject: Public API v2 NFL rankings, WR projections and injuries differ from supplied OpenAPI

Hello FantasyPros API Support,

We are integrating the Public API v2 as read-only supplemental NFL research. We need current official response schemas or sanitized representative examples for three endpoints. We have kept strict validation and have not guessed replacement types, removed required fields, or broadened enums.

Our authorized diagnostic run on2026-10-18 at01:04:36–01:04:37 UTC sent exactly these three GETs, header-only x-api-key authentication, no redirects/retries:

| Path under https://api.fantasypros.com/public/v2/json | Exact query |
|---|---|
| /nfl/2026/consensus-rankings | position=FLX&scoring=PPR&week=6&type=WW |
| /nfl/2026/projections | position=WR&positions=WR&week=6 |
| /nfl/injuries | year=2026&week=6&include_probabilities=true |

All three HTTP statuses were200; all failed response-schema validation. No recognized provider error envelope was detected. We do not regard200 alone as successful authentication or valid NFL data. Raw response bodies and request IDs were not retained in this run. Diagnostics preserve only schema locations/keywords, capped at12 per endpoint, and are not exhaustive. Actual replacement values/types cannot be reconstructed from those diagnostics.

The supplied OpenAPI is version2.0/OpenAPI3.1.1; original YAML SHA256 `d76e56d4486716edb6d17137c68d27c4924b111f500abe1cd9e223fb1690adcd`; JSON conversion SHA256 `b885833209339048644bc8149d98c4e218075c88babb72bf0705aa0e3b7942af`. Mechanical YAML-null compatibility normalization only; no response coercion.

1. **Consensus rankings**: `ranking_type_name` fails the NFLRankingTypes enum; several player records omit required `tier` (documented integer). Please distinguish request type code from response display name and document current enum/code values. Is tier conditional/optional for this request or tied to a supported parameter or subscription scope? Please provide a current FLX/PPR/weekly example with exact player identifier and Yahoo-ID types.
2. **WR projections**: player `fpid` and `mflid` fail documented string types; `stats` fails documented array type. The contract's numeric ID examples also conflict with its declared string types. Please provide the current exact ID types and stats container/keys. Where are full-PPR points represented, and what are expert aggregation, scoring label, season and week semantics? We currently select only documented `stats[].points_ppr`, never infer PPR from an STD total. Are both position and positions expected? Please clarify without assuming an undocumented alias.
3. **Injuries**: `injury_update_date` fails documented string type; `status` and `status_short` fail their documented enums. Please provide current complete enums (including null/empty/no-designation cases, if supported), date type/nullability/timezone and the exact injuries response structure. Explain request year/week versus response scope and whether historical/current reports differ. We need to preserve uncertain reports separately from confirmed injury statuses.

Please also confirm entitlement expectations for these endpoints, how API errors/authentication/quota failures are signaled (including HTTP200 envelopes), and official usage/retention limits. A separately verified NFL news endpoint does not establish access to these three endpoints. We are not requesting a purchase, subscription upgrade, automatic polling or additional provider calls.

A revised official OpenAPI, versioned documentation link, or sanitized representative responses with no credentials would let us implement explicit adapters and offline regression fixtures. We will separately authorize any future live validation.

Thank you.

Owner attachment references: diagnostic Actions run39085126777 (private repository); exact safe schema paths preserved in PR2's `intelligence/fantasypros/research/live-pilot-diagnostics-2026-10-18.json`. Share only the sanitized diagnostics through approved support channels; no league rosters, ownership, FAAB, credentials or private raw payloads are needed.

## Subsequent stored evidence available for support review

Another writer committed week7 raw artifacts to main inbc0e4a8 while this CI task was in progress. We inspected them offline only; no new provider requests were made by this task. These are later observations, not reconstructions of the failed week6 bodies or proof of subscription/authentication for our strict ingestion path.

- `weekly_FLX.json`:151 players, ranking_type_name=`weekly`, first player tier absent; SHA2566afc72c15c4c58d8aa4541c9abb18170d8e559c2d5c7197caf63571ade50f6ca.
- `consensus_FLX.json`:36 players, ranking_type_name=`waiver`, first player tier absent; SHA256a5efa4ffcf3f6c34af1d9d2c52adbdb41e34adc4e42bf7fc2ebdb43433c88079.
- `projections_WR.json`:127 players; first player's fpid/mflid are integers and stats is an object with points/points_ppr/points_half keys, rather than the supplied string IDs/array. SHA2561143997bb8e3687d1558d9bef51545b9adfc87f7a29d91aabd69b6607ceb4ebb.
- `injuries_ALL.json`:229 rows; all observed injury_update_date/status/status_short values are strings, statuses IR/OUT/PUP/Suspended, short codes IR/O/PUP/S. This later snapshot does not reproduce the earlier date/status mismatches. SHA2562fdd5e0453e3d6da54140ad2a9d7f95aeddadf2d04df0c92fbbea34d908ad31b.

Paths are under `intelligence/fantasypros/weekly/2026-w07/raw/` in the now-private repository. Do not send raw/private files automatically. Please confirm current official schema semantics and null/empty cases before we implement adaptations. No strict schema was weakened here.
