# Sparta Yahoo API sync

## Status (2026-10-24): APPROVED by Yahoo — owner finishing setup

- 2026-10-24 (James's email screenshot): Yahoo approved the Fantasy Sports API application. Access turns on after three steps: (1) sign the API Access and Use Agreement (DocuSign), (2) create a **new** app on the Yahoo Developer page with Fantasy Sports selected (existing apps don't get the permission), (3) submit the new app's Client ID with name/email on Yahoo's Developer Application Confirmation Form.
- 2026-10-24 ~10:12 PM ET: new app created, GitHub secrets updated to the new app (sign-in run #6 exchanged the code fine, then got HTTP 403 "application is not authorized" = access not provisioned yet), Client ID submitted on Yahoo's confirmation form ("We'll be in touch shortly"). Waiting on Yahoo to provision; then redo the sign-in once (fresh Agree link) and run the sync.
- 2026-10-24 10:14 PM ET: Yahoo auto-reply to the Client ID form: "review process typically takes 1-2 weeks". DocuSign signed by James 2026-10-23 6:35 PM (yahoo.com address; Yahoo countersignature pending). Expect access ~Nov 1-7. Until then: screenshots + Codex live checks.
- Then: update the GitHub secrets to the NEW app's Client ID/Secret, sign in once (iPhone steps below), run the sync manually, and re-enable the cron lines in `yahoo_sync.yml`.

## Earlier status (2026-10-20): BLOCKED — waiting on Yahoo approval

- Learned 2026-10-19 (James): Yahoo must approve the app before the Fantasy API returns
  Sparta data. Until then every run fails and `data/yahoo_api/latest.json` does not exist.
- The scheduled runs in `.github/workflows/yahoo_sync.yml` are paused; the manual
  "Run workflow" button still works for testing.
- Until approval, JD roster/FAAB/ownership come from James's Yahoo screenshots and the
  Codex live checks (`data/yahoo_live_snapshot_latest.json`, `data/current_roster_jd.json`).
- Do not spend a session debugging the sync while this note stands. When Yahoo approves:
  run the workflow manually, confirm `latest.json` is written with `completed: true`, then
  uncomment the cron lines and update this section.

Replaces hand-captured browser snapshots with scheduled pulls from the official
Yahoo Fantasy Sports API. Everything is read-only on Yahoo: the code issues GET
requests only and cannot make moves, place claims, or set lineups.

## One-time setup (about 10 minutes)

1. **Create a Yahoo developer app** at <https://developer.yahoo.com/apps/create/>
   - Application name: anything (e.g. `Sparta sync`)
   - Application type: **Installed Application**
   - Redirect URI(s): `https://localhost:8080` (required by the form)
   - API permissions: **Fantasy Sports → Read**
   - Copy the **Client ID** and **Client Secret** it shows.

2. **Sign in once** from a computer with Python 3.10+ and this repo checked out:

   ```
   python scripts/yahoo_auth.py
   ```

   Paste the Client ID and Secret, approve access in the browser, and paste back
   the code Yahoo shows. If Yahoo rejects `oob`, rerun with
   `--redirect-uri https://localhost:8080` and paste the full URL the browser
   lands on (the page itself will not load; that is expected). The script confirms
   it can read league 102586, then prints the values to store.

3. **Add GitHub secrets** (repo → Settings → Secrets and variables → Actions):
   `YAHOO_CLIENT_ID`, `YAHOO_CLIENT_SECRET`, `YAHOO_REFRESH_TOKEN`
   (and `YAHOO_REDIRECT_URI` only if you used `https://localhost:8080`).

4. **Run it**: Actions → *Sparta Yahoo API sync* → Run workflow (leave *apply* off
   for the first run) and check `data/yahoo_api/reconciliation_latest.json`.

## Setup from an iPhone (no computer)

1. Create the Yahoo app as in step 1 above (Confidential Client, redirect `https://localhost:8080`).
2. In Safari, create a fine-grained GitHub token at
   <https://github.com/settings/personal-access-tokens/new>: repository access
   **Only select repositories → sparta-fantasy-football-db**, permission
   **Secrets: Read and write**. Copy it.
3. Add four repository secrets (repo → Settings → Secrets and variables → Actions):
   `YAHOO_CLIENT_ID`, `YAHOO_CLIENT_SECRET`, `YAHOO_REDIRECT_URI` = `https://localhost:8080`,
   `SPARTA_SECRETS_PAT` = the token from step 2.
4. Open in Safari (replace `CLIENT_ID`):
   `https://api.login.yahoo.com/oauth2/request_auth?client_id=CLIENT_ID&redirect_uri=https://localhost:8080&response_type=code&scope=fspt-r`
   and tap **Agree**. Safari then fails to load a `localhost` page — expected.
   Copy the address from the address bar.
5. Within a few minutes: Actions → **Yahoo sign-in (one time)** → Run workflow →
   paste the address → Run. It verifies access to league 102586 and saves
   `YAHOO_REFRESH_TOKEN` for you.
6. Actions → **Sparta Yahoo API sync** → Run workflow.

`SPARTA_SECRETS_PAT` also lets the scheduled sync save a new refresh token
automatically if Yahoo ever rotates it.

## Modes

| Mode | What changes | How to turn on |
|---|---|---|
| Report-only (default) | `data/yahoo_api/latest.json`, `reconciliation_latest.json`, `history.jsonl` | default |
| Apply | also appends new Yahoo-confirmed add/drop moves to `transactions.json` and refreshes `faab.json`, `waiver_state.json`, `current_roster_jd.json` | repo variable `SPARTA_YAHOO_APPLY=true`, or tick *apply* on a manual run |

Apply mode never rewrites existing transactions, never auto-applies trades, and
refuses to run unless all 12 Yahoo teams map to repo team codes. If
`validate_sparta.py` fails afterwards, the workflow restores the durable files
and keeps only the snapshot and report.

## What one pull contains

About 13–20 API requests: league settings, all 12 teams (FAAB, waiver priority,
moves), every roster with lineup slots and injury status, standings, this week's
scoreboard with projections and win probability, the full transaction log, and
the top available players at QB/RB/WR/TE/K/DEF with percent owned and whether
each is on waivers or a free agent.

## Running locally

```
export YAHOO_CLIENT_ID=... YAHOO_CLIENT_SECRET=... YAHOO_REFRESH_TOKEN=...
python scripts/yahoo_sync.py            # report only
python scripts/yahoo_sync.py --apply    # apply confirmed changes
python -m unittest tests.test_yahoo_sync   # offline tests, no credentials needed
```

## Troubleshooting

- **`unmapped_teams` not empty**: a team renamed and its manager name changed too.
  Add its Yahoo `team_id` to `data/yahoo_team_map.json`.
- **HTTP 401 from the token endpoint**: the refresh token was revoked (e.g. app
  permissions changed). Rerun `scripts/yahoo_auth.py` and update the secret.
- **"Yahoo issued a new refresh token" warning**: update `YAHOO_REFRESH_TOKEN`.
