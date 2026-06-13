"""Screen 2: Inbox — triage + draft (no-send). The trust gate forbids sending."""

from __future__ import annotations

from fastapi import APIRouter, Depends

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
    body = _agent.draft_reply(ctx, payload.get("sender", ""), payload.get("subject", ""),
                              payload.get("body", ""))
    # Staged only — never sent. Production pushes this to Gmail Drafts.
    return {"draft": body, "status": "pending", "sendable": False}
