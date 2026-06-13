"""Screen 2: Inbox — triage + draft (no-send). The trust gate forbids sending.

When Google is connected the draft is pushed to Gmail Drafts (compose scope only,
never send); otherwise it is staged in the response for the user to copy.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import google, ingest, repo
from ..agents.email import EmailAgent
from ..deps import RequestContext, get_current_user

router = APIRouter(prefix="/inbox", tags=["inbox"])
_agent = EmailAgent()


@router.get("")
def list_inbox(ctx: RequestContext = Depends(get_current_user)) -> dict:
    """Return synced inbox messages, ranked by stake."""
    rows = repo.list_email_items(ctx)
    return {"items": [dict(r) for r in (rows or [])]}


@router.post("/sync")
def sync(ctx: RequestContext = Depends(get_current_user)) -> dict:
    """Pull recent Gmail into email_item, triaged by stake."""
    if not google.is_configured():
        raise HTTPException(status_code=400, detail="Google connectors not configured.")
    if not repo.get_google_credential(ctx):
        raise HTTPException(status_code=400, detail="Google not connected for this user.")
    return {"synced": ingest.sync_inbox(ctx)}


@router.post("/triage")
def triage(payload: dict, ctx: RequestContext = Depends(get_current_user)) -> dict:
    stake = _agent.triage(ctx, payload.get("sender", ""), payload.get("subject", ""),
                          payload.get("body", ""))
    return {"stake": stake}


@router.post("/draft")
def draft(payload: dict, ctx: RequestContext = Depends(get_current_user)) -> dict:
    sender = payload.get("sender", "")
    subject = payload.get("subject", "")
    body = _agent.draft_reply(ctx, sender, subject, payload.get("body", ""))

    # Push to Gmail Drafts if connected; otherwise stage in the response.
    pushed = None
    if google.is_configured():
        try:
            token = google.access_token_for(ctx)  # auto-refreshes if expired
            if token:
                gmail_draft = google.create_draft(token, sender, f"Re: {subject}", body)
                pushed = gmail_draft.get("id")
        except Exception:  # noqa: BLE001 - staging still succeeds if push fails
            pushed = None

    return {
        "draft": body,
        "status": "pushed" if pushed else "pending",
        "gmail_draft_id": pushed,
        "sendable": False,  # SHAI never sends; the user sends from Gmail
    }
