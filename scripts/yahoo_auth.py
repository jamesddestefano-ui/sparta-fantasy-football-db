"""One-time Yahoo sign-in for the Sparta sync. Run this on your own computer.

    python scripts/yahoo_auth.py

It asks for your Yahoo app's Client ID and Client Secret, opens Yahoo's
consent page, and exchanges the code Yahoo shows you for a long-lived refresh
token. It then confirms the token can read Sparta (Yahoo league 102586) and
prints the three values to store as GitHub repository secrets:

    YAHOO_CLIENT_ID, YAHOO_CLIENT_SECRET, YAHOO_REFRESH_TOKEN

Nothing is written to disk. Never paste these values into a chat.
"""
from __future__ import annotations

import argparse
import getpass
import sys
import urllib.parse
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from yahoo_client import AUTH_URL, YahooClient, exchange_token  # noqa: E402
import yahoo_parse as yp  # noqa: E402


def extract_code(text: str) -> str:
    text = text.strip()
    if "code=" in text:
        return urllib.parse.parse_qs(urllib.parse.urlparse(text).query).get("code", [""])[0]
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--redirect-uri", default="oob",
                    help='"oob" (Yahoo shows a code) or the exact Redirect URI on your Yahoo app, '
                         'e.g. https://localhost:8080 (copy the code= value from the address bar)')
    ap.add_argument("--league-id", default="102586")
    args = ap.parse_args()

    client_id = input("Yahoo Client ID: ").strip()
    client_secret = getpass.getpass("Yahoo Client Secret (hidden): ").strip()
    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": args.redirect_uri, "response_type": "code",
        "scope": "fspt-r"})
    print("\nOpen this page, sign in to Yahoo, and click Agree:\n\n  " + url + "\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    code = extract_code(input("Paste the code Yahoo shows (or the full redirected URL): "))
    tokens = exchange_token(client_id, client_secret, {
        "grant_type": "authorization_code", "redirect_uri": args.redirect_uri, "code": code})
    refresh = tokens.get("refresh_token")
    if not refresh:
        print("Yahoo did not return a refresh token.", file=sys.stderr)
        return 1

    client = YahooClient(client_id, client_secret, refresh, redirect_uri=args.redirect_uri)
    game_key = yp.parse_game_key(client.get("game/nfl"))
    meta = yp.parse_league_meta(client.get(f"league/{game_key}.l.{args.league_id}"))
    print(f"\nVerified: read access to '{meta['name']}' (league {meta['league_id']}, "
          f"season {meta['season']}, week {meta['current_week']}).")

    print("\nAdd these as GitHub secrets (repo > Settings > Secrets and variables > Actions),")
    print("or with the GitHub CLI from this folder:\n")
    print(f"  gh secret set YAHOO_CLIENT_ID --body '{client_id}'")
    print("  gh secret set YAHOO_CLIENT_SECRET      # paste the secret when prompted")
    print("  gh secret set YAHOO_REFRESH_TOKEN      # paste the token below when prompted")
    if args.redirect_uri != "oob":
        print(f"  gh secret set YAHOO_REDIRECT_URI --body '{args.redirect_uri}'")
    print("\nRefresh token (treat like a password):\n\n  " + refresh + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
