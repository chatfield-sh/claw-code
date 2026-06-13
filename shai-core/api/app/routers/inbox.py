"""Screen 2: Inbox — triage + draft (no-send). The trust gate forbids sending.

When Google is connected the draft is pushed to Gmail Drafts (compose scope only,
never send); otherwise it is staged in the response for the user to copy.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import google, repo
from ..agents.email import EmailAgent
from ..deps import RequestContext, get_current_user

router = APIRouter(prefix="/inbox", tags=["inbox"])
_agent = EmailAgent()


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
    cred = repo.get_google_credential(ctx)
    if cred and google.is_configured():
        try:
            gmail_draft = google.create_draft(cred["access_token"], sender,
                                              f"Re: {subject}", body)
            pushed = gmail_draft.get("id")
        except Exception:  # noqa: BLE001 - staging still succeeds if push fails
            pushed = None

    return {
        "draft": body,
        "status": "pushed" if pushed else "pending",
        "gmail_draft_id": pushed,
        "sendable": False,  # SHAI never sends; the user sends from Gmail
    }
