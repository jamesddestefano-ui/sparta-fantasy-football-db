# Directive: Sparta LOCK Pulse hourly pass (recreate after 2026-10-22 cleanup)

- From: Claude (Sparta Brain), for James (owner), 2026-10-22
- To: Sparta Grok Bot
- Why: James deleted every hourly Grok Bot job on 2026-10-22 to stop a broken mirror job that kept writing a stale 2026-10-19 pass and wiping the Pulse history. This directive recreates **only the good job** (the hourly LOCK Pulse pass the "Sparta FF Bot" was committing). The mirror job must **not** come back.

## Paste this into Grok Bot

```
Create ONE scheduled job: "Sparta LOCK Pulse — hourly pass".

SCHEDULE
- Every hour at :20 (America/New_York), 7:20 AM–11:20 PM ET daily.
- Sundays (Sunday mode): every 30 min from 8:50 AM to 8:50 PM ET, and set "sundayMode": true. Focus on inactives, late scratches and weather.

REPO (GitHub: jamesddestefano-ui/sparta-fantasy-football-db, branch main)
Write ONLY these two files. Never touch data/, learning/ or any other path.
1) intelligence/grok_pulse_latest.json: replace with this pass.
2) intelligence/grok_pulse_history.jsonl: APPEND exactly one line (this pass as compact JSON) to the end. Never rewrite, truncate, reorder or re-upload the whole file. No blank lines.
Before writing: pull main and read the current grok_pulse_latest.json. If its completedAt is newer than or equal to yours, write nothing.
Commit as "Sparta FF Bot <sparta-ff-bot@local>" with message:
  intelligence: <Day> <h:mm AM/PM> ET LOCK Pulse <completedAt> (<"quiet" or 1-line summary>)
If the push is rejected, pull --rebase and retry (max 3). Never force-push.
Do NOT create any "mirror" job, any copy from grok.me /api/pulse, or any second writer to these files.

READ EACH PASS (don't hard-code rosters)
- JD roster: data/current_roster_jd.json
- Waiver targets: intelligence/board/latest.json (waiver_targets)
- JD's opponent this week: data/current_roster_jd.json -> scores.opponent

SOURCES (X/Twitter)
- National: Ian Rapoport, Adam Schefter, Tom Pelissero, Jordan Schultz, Matthew Berry, Adam Levitan, Establish The Run, RotoWire NFL.
- Usage data: Fantasy Points Data (@FantasyPtsData).
- One beat per team: ARI @Cardschatter, ATL @marcraimondi, BAL @jamisonhensley, BUF @JoeBuscaglia, CAR @josephperson, CHI @adamjahns, CIN @pauldehnerjr, CLE @MaryKayCabot, DAL @toddarcher, DEN @TroyRenck, DET @davebirkett, GB @RobDemovsky, HOU @AaronWilson_NFL, IND @HolderStephen, JAX @ESPNdirocco, KC @jessenewell, LAC @bynoahfurtado, LAR @StuJRams, LV @AdamHillLVRJ, MIA @Marcel_LJ, MIN @alec_lewis, NE @MikeReiss, NO @nick_underhill, NYG @JordanRaanan, NYJ @RichCimini, PHI @Tim_McManus, PIT @bepryor, SEA @bcondotta, SF @mattbarrows, TB @JennaLaineESPN, TEN @TDavenport_NFL, WAS @john_keim.
List every source in "sourceNotes" (sourceId, source, handle, team, sourceType, dateAdded, grade, note, at).

WHAT TO EMIT
Only posts from the last 2 hours not already in the previous pass, naming:
- a JD player (relevance JD_ROSTER), a waiver target (WAIVER_TARGET), JD's opponent's starters (OPPONENT), or
- any team's role change that could create a pickup: starter injured/benched, backup promoted, new lead back, WR moving into a starting role (DISCOVERY).
Priority: practice participation (DNP/limited/full), game designations, IR moves, inactives, depth-chart / first-team reps, snap/route/target share, coach comments on roles.
Skip contracts, opinion and general team news. One originating fact = one item; reposts go in "corroboration". If nothing qualifies, publish a "quiet" pass with "items": [] (still status "live").

PASS FORMAT (grok_pulse_latest.json)
{"product":"LOCK Pulse","timezone":"America/New_York","generatedAt":<ISO UTC>,"status":"live","completedAt":<ISO UTC, = finish time>,"nextAtLabel":"<next run, e.g. 11:20 AM ET>","inWindow":true,"itemCount":<n>,"sundayMode":<bool>,"sourceNotes":[...],"items":[...]}
Each item: id, at (post time, ISO UTC), expertId, expert, handle, outlet, text, players, playerIds, url (the X post), kind (PRACTICE_REPORT | INJURY_STATUS | IR_ACTIVATION | DEPTH_CHART | USAGE | COACH_COMMENT | TRANSACTION | INACTIVES), eventId, signal, priorStatus, newStatus, why, implication, opportunity, corroboration, supportingSources, priority (HIGH/MEDIUM/LOW), sourceType (BEAT/NATIONAL/ANALYST/USAGE_DATA), team, relevance (JD_ROSTER/WAIVER_TARGET/OPPONENT/DISCOVERY).
Label unverified reports "UNCONFIRMED:" at the start of text.

LIMITS
Pulse is intelligence only. Never change rosters, ownership, FAAB, waivers, transactions or lineups. Never invent posts or URLs. If X can't be reached, skip the pass and write nothing (don't publish a stale or partial pass).
```

## Brain-side checks after it's live

- The first pass lands at the next :20 and `scripts/pulse_guard.py` (workflow `pulse_guard.yml`) leaves it untouched (newer completedAt, history only appended).
- No commits titled "Update/Append Grok Pulse intelligence 2026-10-19..." appear at :08.

## Status (2026-10-22 ~10:45 ET)

- IMPLEMENTED by Grok Bot as "Sparta LOCK Pulse — hourly pass", task ID 7816b8ad-12c6-4f9e-90d3-8d446a9634b5. Hourly at :20, 7:20 AM–11:20 PM ET. First run ~11:20 AM ET 2026-10-22.
- Gap: Grok Bot can't run every 30 minutes on Sundays in one job. Suggested fix: a second Sunday-only job at :50 (8:50 AM–8:50 PM ET) with the same directive. It catches the ~11:30 AM inactives before the 1 PM kickoffs.
- Sunday gap closed: "Sparta LOCK Pulse — Sunday :50 pass", task ID cac32e10-aee6-42ff-a190-64a767d8dc95, Sundays at :50, 8:50 AM–8:50 PM ET, sundayMode true. First run Sun 2026-10-25 8:50 AM ET.

## Amendment 2026-10-23: Grok writes latest.json only

On 2026-10-22/23 a Grok job wrote non-JSON placeholder lines into the history ("PLACEHOLDER_FOR_FULL_HISTORY...", "$(cat /tmp/history.jsonl)") because it rewrote the whole file. From now on:
- Both Grok jobs (hourly :20 task 7816b8ad…, Sunday :50 task cac32e10…) write **only** `intelligence/grok_pulse_latest.json`.
- `pulse_guard.yml` / `scripts/pulse_guard.py` appends each new live pass to `grok_pulse_history.jsonl` automatically (one compact line, deduped by completedAt), strips junk lines and restores wiped passes.

Paste to Grok Bot:

```
Update BOTH jobs "Sparta LOCK Pulse — hourly pass" (7816b8ad-12c6-4f9e-90d3-8d446a9634b5) and "Sparta LOCK Pulse — Sunday :50 pass" (cac32e10-aee6-42ff-a190-64a767d8dc95):
1. Stop writing intelligence/grok_pulse_history.jsonl entirely. Do not read, rewrite, append to or upload it. A GitHub automation in the repo now appends each new pass to history automatically.
2. Write ONLY intelligence/grok_pulse_latest.json, as one complete, valid JSON object (the full pass). Never write placeholders, shell commands such as $(cat ...), "..." or truncated content. If the full JSON can't be produced, write nothing.
3. Before writing, read the current grok_pulse_latest.json. If its completedAt is newer than or equal to yours, write nothing.
4. One commit per pass: "intelligence: <Day> <h:mm AM/PM> ET LOCK Pulse <completedAt> (<quiet or 1-line summary>)", author "Sparta FF Bot <sparta-ff-bot@local>". On a rejected push, pull --rebase and retry (max 3); never force-push.
5. Everything else in the job stays the same (schedule, sources, filters, item schema, limits).
Also check for any other job or integration that writes to this repo (names containing "mirror", "Grok Pulse intelligence", "PRIME Pulse", or a grok.me GitHub sync) and turn it off. Only these two jobs should write the Pulse feed.
```
