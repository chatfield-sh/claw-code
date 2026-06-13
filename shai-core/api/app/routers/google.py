"""Google OAuth + calendar sync routes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from .. import google, repo
from ..deps import RequestContext, get_current_user

router = APIRouter(prefix="/google", tags=["google"])


@router.get("/status")
def status(ctx: RequestContext = Depends(get_current_user)) -> dict:
    return {
        "configured": google.is_configured(),
        "connected": repo.get_google_credential(ctx) is not None,
    }


@router.get("/auth")
def auth() -> dict:
    """Return the consent URL the user should visit to connect Google."""
    try:
        return {"url": google.auth_url()}
    except google.GoogleNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/callback")
def callback(code: str, ctx: RequestContext = Depends(get_current_user)) -> dict:
    """OAuth redirect target: exchange the code and store the tokens."""
    try:
        tokens = google.exchange_code(code)
    except google.GoogleNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    expires_at = None
    if tokens.get("expires_in"):
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(tokens["expires_in"]))
    repo.store_google_credential(
        ctx, tokens["access_token"], tokens.get("refresh_token"),
        tokens.get("scope"), expires_at,
    )
    return {"connected": True}


@router.post("/calendar/sync")
def calendar_sync(ctx: RequestContext = Depends(get_current_user)) -> dict:
    """Pull primary-calendar events into calendar_event (tenant-scoped)."""
    cred = repo.get_google_credential(ctx)
    if not cred:
        raise HTTPException(status_code=400, detail="Google not connected for this user.")
    events = google.list_calendar_events(cred["access_token"])
    synced = 0
    for ev in events:
        start = (ev.get("start") or {}).get("dateTime") or (ev.get("start") or {}).get("date")
        end = (ev.get("end") or {}).get("dateTime") or (ev.get("end") or {}).get("date")
        repo.upsert_calendar_event(
            ctx, ev.get("id", ""), ev.get("summary", "(no title)"),
            start, end, ev.get("location"),
        )
        synced += 1
    return {"synced": synced}
