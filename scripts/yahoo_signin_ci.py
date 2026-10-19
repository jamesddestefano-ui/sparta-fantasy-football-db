"""Finish Yahoo sign-in inside GitHub Actions (phone-friendly; no local Python).

Reads YAHOO_CLIENT_ID / YAHOO_CLIENT_SECRET / YAHOO_REDIRECT_URI from the
environment and the one-time code (or the whole localhost URL Yahoo redirected
to) from YAHOO_AUTH_CODE. Exchanges it for a refresh token, confirms read
access to Sparta, and writes the refresh token to the file named by
--token-file so the workflow can store it as a secret. Never prints the token.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from yahoo_auth import extract_code  # noqa: E402
from yahoo_client import YahooClient, exchange_token  # noqa: E402
import yahoo_parse as yp  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--token-file", required=True)
    ap.add_argument("--league-id", default="102586")
    args = ap.parse_args()

    cid = os.environ.get("YAHOO_CLIENT_ID", "").strip()
    secret = os.environ.get("YAHOO_CLIENT_SECRET", "").strip()
    redirect = os.environ.get("YAHOO_REDIRECT_URI", "").strip() or "oob"
    code = extract_code(os.environ.get("YAHOO_AUTH_CODE", ""))
    if not (cid and secret):
        print("::error::Add YAHOO_CLIENT_ID and YAHOO_CLIENT_SECRET secrets first.")
        return 1
    if not code:
        print("::error::No code provided. Paste the code (or the whole localhost URL) into the run form.")
        return 1

    tokens = exchange_token(cid, secret, {"grant_type": "authorization_code",
                                          "redirect_uri": redirect, "code": code})
    refresh = tokens.get("refresh_token")
    if not refresh:
        print("::error::Yahoo returned no refresh token.")
        return 1
    print(f"::add-mask::{refresh}")
    if tokens.get("access_token"):
        print(f"::add-mask::{tokens['access_token']}")

    client = YahooClient(cid, secret, refresh, redirect_uri=redirect)
    game_key = yp.parse_game_key(client.get("game/nfl"))
    meta = yp.parse_league_meta(client.get(f"league/{game_key}.l.{args.league_id}"))
    print(f"Verified read access to '{meta['name']}' (league {meta['league_id']}, "
          f"season {meta['season']}, week {meta['current_week']}).")

    Path(args.token_file).write_text(client.refresh_token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
