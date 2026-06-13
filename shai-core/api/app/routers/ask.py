"""Top-level /ask — orchestrator-driven Q&A over the user's notes + memory."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..agents import Orchestrator
from ..deps import RequestContext, get_current_user

router = APIRouter(prefix="/ask", tags=["ask"])
_orchestrator = Orchestrator()


@router.post("")
def ask(payload: dict, ctx: RequestContext = Depends(get_current_user)) -> dict:
    return _orchestrator.answer(ctx, payload.get("query", ""))
