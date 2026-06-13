"""Live data ingestion — Gmail inbox + Google Calendar into the DB.

Both functions need a connected Google account; they return 0 (no-op) when the
user has not connected, so they are safe to call unconditionally from the cron.
The inbox sync triages each message by stake on the way in.
"""

from __future__ import annotations

import logging
from email.utils import parsedate_to_datetime

from . import google, repo
from .agents.email import EmailAgent
from .deps import RequestContext

log = logging.getLogger("shai.ingest")
_email = EmailAgent()


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None


def sync_inbox(ctx: RequestContext, max_results: int = 20) -> int:
    """Pull recent inbox messages into email_item, triaged by stake."""
    if not google.is_configured():
        return 0
    token = google.access_token_for(ctx)
    if not token:
        return 0
    synced = 0
    for ref in google.list_inbox(token, max_results=max_results):
        try:
            msg = google.get_message(token, ref["id"])
        except Exception as exc:  # noqa: BLE001 - skip a bad message, keep going
            log.warning("skip message %s: %s", ref.get("id"), exc)
            continue
        stake = _email.triage(ctx, msg.get("sender") or "", msg.get("subject") or "",
                              msg.get("snippet") or "")
        repo.upsert_email_item(
            ctx, msg["gmail_id"], msg.get("sender"), msg.get("subject"),
            msg.get("snippet"), stake, _parse_date(msg.get("date")),
        )
        synced += 1
    return synced


def sync_calendar(ctx: RequestContext, max_results: int = 10) -> int:
    """Pull primary-calendar events into calendar_event."""
    if not google.is_configured():
        return 0
    token = google.access_token_for(ctx)
    if not token:
        return 0
    synced = 0
    for ev in google.list_calendar_events(token, max_results=max_results):
        start = (ev.get("start") or {}).get("dateTime") or (ev.get("start") or {}).get("date")
        end = (ev.get("end") or {}).get("dateTime") or (ev.get("end") or {}).get("date")
        repo.upsert_calendar_event(
            ctx, ev.get("id", ""), ev.get("summary", "(no title)"),
            start, end, ev.get("location"),
        )
        synced += 1
    return synced
