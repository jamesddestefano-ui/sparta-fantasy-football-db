"""Minimal read-only Yahoo Fantasy Sports API v2 client for the Sparta league.

Standard library only. Credentials come from environment variables and are
never written to disk or logs:

    YAHOO_CLIENT_ID, YAHOO_CLIENT_SECRET, YAHOO_REFRESH_TOKEN
    YAHOO_REDIRECT_URI (optional; default "oob", must match the one used at sign-in)

The client only issues GET requests against the Fantasy API. It cannot make
roster moves, place claims, or change lineups.
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
API_BASE = "https://fantasysports.yahooapis.com/fantasy/v2/"
USER_AGENT = "sparta-fantasy-football-db/1.0 (read-only)"


class YahooAuthError(RuntimeError):
    pass


class YahooApiError(RuntimeError):
    pass


def strip_namespaces(root: ET.Element) -> ET.Element:
    """Yahoo XML is namespaced; drop namespaces so paths stay readable."""
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
        for key in list(el.attrib):
            if "}" in key:
                el.attrib[key.split("}", 1)[1]] = el.attrib.pop(key)
    return root


def _basic_auth(client_id: str, client_secret: str) -> str:
    raw = f"{client_id}:{client_secret}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def exchange_token(client_id: str, client_secret: str, form: dict[str, str]) -> dict:
    """POST to Yahoo's token endpoint (authorization_code or refresh_token grant)."""
    body = urllib.parse.urlencode(form).encode()
    req = urllib.request.Request(
        TOKEN_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": _basic_auth(client_id, client_secret),
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:300]
        raise YahooAuthError(f"token endpoint returned HTTP {exc.code}: {detail}") from None


class YahooClient:
    def __init__(self, client_id: str, client_secret: str, refresh_token: str,
                 min_interval_s: float = 0.5, redirect_uri: str = "oob"):
        if not (client_id and client_secret and refresh_token):
            raise YahooAuthError("YAHOO_CLIENT_ID, YAHOO_CLIENT_SECRET and YAHOO_REFRESH_TOKEN are required")
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.access_token: str | None = None
        self.refresh_token_rotated = False
        self.requests_made = 0
        self.redirect_uri = redirect_uri or "oob"
        self._min_interval = min_interval_s
        self._last_request = 0.0

    @classmethod
    def from_env(cls) -> "YahooClient":
        return cls(
            os.environ.get("YAHOO_CLIENT_ID", "").strip(),
            os.environ.get("YAHOO_CLIENT_SECRET", "").strip(),
            os.environ.get("YAHOO_REFRESH_TOKEN", "").strip(),
            redirect_uri=os.environ.get("YAHOO_REDIRECT_URI", "").strip() or "oob",
        )

    def refresh(self) -> None:
        payload = exchange_token(self.client_id, self.client_secret, {
            "grant_type": "refresh_token",
            "redirect_uri": self.redirect_uri,
            "refresh_token": self.refresh_token,
        })
        token = payload.get("access_token")
        if not token:
            raise YahooAuthError("token endpoint returned no access_token")
        self.access_token = token
        new_refresh = payload.get("refresh_token")
        if new_refresh and new_refresh != self.refresh_token:
            # Yahoo normally keeps the refresh token stable; if it ever rotates,
            # the stored secret must be updated by the owner.
            self.refresh_token = new_refresh
            self.refresh_token_rotated = True

    def get(self, path: str) -> ET.Element:
        """GET a Fantasy API resource path and return the namespace-free XML root."""
        if self.access_token is None:
            self.refresh()
        url = API_BASE + path.lstrip("/")
        for attempt in range(2):
            wait = self._min_interval - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            req = urllib.request.Request(url, headers={
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/xml",
                "User-Agent": USER_AGENT,
            })
            self._last_request = time.monotonic()
            self.requests_made += 1
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return strip_namespaces(ET.fromstring(resp.read()))
            except urllib.error.HTTPError as exc:
                if exc.code == 401 and attempt == 0:
                    self.refresh()
                    continue
                detail = exc.read().decode(errors="replace")[:300]
                raise YahooApiError(f"GET {path} returned HTTP {exc.code}: {detail}") from None
        raise YahooApiError(f"GET {path} failed after token refresh")
