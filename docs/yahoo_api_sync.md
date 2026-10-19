# Sparta Yahoo API sync

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
