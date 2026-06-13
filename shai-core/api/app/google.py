"""Google connectors — OAuth + Gmail (read + draft) + Calendar (read).

Honors the trust gate: Gmail integration reads the inbox and *creates drafts*,
never sends. All network calls use httpx. Helpers raise ``GoogleNotConfigured``
when client credentials are absent so routers can return a clear 503.
"""

from __future__ import annotations

import base64
from email.message import EmailMessage
from urllib.parse import urlencode

import httpx

from .config import settings

AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
CALENDAR_API = "https://www.googleapis.com/calendar/v3"

# Read inbox + calendar; compose (not send) drafts. Send scope is intentionally absent.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar.readonly",
    "openid",
    "email",
]


class GoogleNotConfigured(RuntimeError):
    """Raised when Google client credentials are not set."""


def is_configured() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret)


def _require_configured() -> None:
    if not is_configured():
        raise GoogleNotConfigured(
            "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to enable Google connectors."
        )


def auth_url(state: str = "") -> str:
    """Build the OAuth consent URL (offline access so we get a refresh token)."""
    _require_configured()
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_URI}?{urlencode(params)}"


def exchange_code(code: str) -> dict:
    """Exchange an authorization code for tokens."""
    _require_configured()
    resp = httpx.post(TOKEN_URI, data={
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


def list_calendar_events(access_token: str, max_results: int = 10) -> list[dict]:
    resp = httpx.get(
        f"{CALENDAR_API}/calendars/primary/events",
        headers=_headers(access_token),
        params={"maxResults": max_results, "singleEvents": "true", "orderBy": "startTime"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("items", [])


def list_inbox(access_token: str, max_results: int = 10) -> list[dict]:
    resp = httpx.get(
        f"{GMAIL_API}/messages",
        headers=_headers(access_token),
        params={"maxResults": max_results, "q": "in:inbox"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("messages", [])


def create_draft(access_token: str, to: str, subject: str, body: str) -> dict:
    """Create a Gmail draft. Never sends — the user approves and sends in Gmail."""
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    resp = httpx.post(
        f"{GMAIL_API}/drafts",
        headers=_headers(access_token),
        json={"message": {"raw": raw}},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()
