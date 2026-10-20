# Request: Grok Pulse expansion — team beat coverage for Sparta (JD)

- From: Claude (Sparta Brain), approved by James (owner), 2026-10-20
- To: Sparta Grok Bot / Grok Pulse maintainer (writes only `intelligence/` mirror files, AGENTS rule 27)
- Status: REQUESTED — not yet implemented

## Why

Grok Pulse today follows national insiders and fantasy analysts (Rapoport, Schefter, Berry, Levitan, Establish The Run). Its items are accurate but rarely change a Sparta move: `intelligence/sparta_pulse_learning.json` shows 57 items graded ACCURATE_NOT_ACTIONABLE, 0 USEFUL/HIGHLY_USEFUL, 2 unresolved. The moves that cost JD points in Weeks 1–6 depended on team-level detail national accounts don't post or post late: practice participation, first-team reps, snap and route share, coach comments (Wicks role, Dobbins W2 usage, Wilson workload, Waller route share, Christian Kirk's return).

Goal: fewer, more decision-relevant items — not more volume.

## What to add

1. **One beat reporter per NFL team on JD's roster.** Pick the current primary beat writer for each team; the list follows `data/current_roster_jd.json` and changes as the roster changes. Today: BAL, CAR, CIN, CLE, DEN, LV, NO, NYJ, PHI, SEA, SF — plus ATL if Michael Penix Jr. is acquired (pending claim, processes Oct 21).
2. **One usage-data account** that posts weekly snap share, route participation and target share (one source, not several).
3. **Keep** the current national insiders and fantasy analysts unchanged.

Please list each new account in the feed's `sourceNotes` with team, handle and date added.

## Filter (what to emit)

Emit an item only if it names at least one of:
- a player on JD's roster (`data/current_roster_jd.json`);
- a player on this week's waiver-target list (`intelligence/board/latest.md` / `.json`);
- a starter for JD's opponent this week.

Priority topics: injury status and practice participation (DNP / limited / full), IR activations, depth-chart and first-team-rep changes, snap/route/target share, coach comments on roles, inactives.

## Item format (unchanged schema)

Keep the existing `grok_pulse_latest.json` item fields: `id`, `at`, `expertId`, `expert`, `handle`, `outlet`, `text`, `players`, `url`, `kind`, `eventId`, `signal`, `priorStatus`, `newStatus`, `why`, `implication`, `opportunity`, `corroboration`, `supportingSources`, `priority`. Add, if possible:
- `sourceType`: `BEAT` | `NATIONAL` | `ANALYST` | `USAGE_DATA`
- `team`: NFL team abbreviation
- `relevance`: `JD_ROSTER` | `WAIVER_TARGET` | `OPPONENT`

## Rules that still apply

- Pulse is intelligence only. It never changes ownership, roster, FAAB, waivers, transactions or lineups (AGENTS rules 22, 26, 57).
- Grok/LOCK writes only the Pulse mirror files under `intelligence/` (rule 27). No new store, no parallel ledger (rules 20, 21).
- One originating fact = one item; reposts go in `corroboration`, not as new items (rule 61).
- A pass counts as new only when `status` is `live` and `completedAt` changes (rule 23).

## How accounts will be judged (Brain side)

- Each Sparta decision that uses a Pulse item records `pulse_used=TRUE` and lineage (rules 59, 62).
- After 4 weeks (target review: Week 11 report card), any added account whose items never changed or confirmed a Sparta decision is proposed for removal; accounts with USEFUL/HIGHLY_USEFUL items stay.
- Success measure: at least 1 USEFUL or HIGHLY_USEFUL Pulse item per week by Week 11, with no rise in DUPLICATIVE items.

## Copy-paste message for the Grok bot

> Sparta Pulse expansion (approved by James): add one current beat reporter for each NFL team on JD's roster — BAL, CAR, CIN, CLE, DEN, LV, NO, NYJ, PHI, SEA, SF (add ATL if Penix is claimed) — plus one snap/route/target-share account. Keep current experts. Only emit items naming a JD player, a current waiver target, or JD's opponent's starters; prioritize practice participation, IR activations, depth-chart/first-team reps, usage share, coach role comments, inactives. Keep the existing item schema; add sourceType (BEAT/NATIONAL/ANALYST/USAGE_DATA), team, and relevance (JD_ROSTER/WAIVER_TARGET/OPPONENT) if possible. One fact = one item, reposts go in corroboration. Write only the Pulse mirror files under intelligence/. Full spec: docs/requests/2026-10-20-grok-pulse-expansion.md.
