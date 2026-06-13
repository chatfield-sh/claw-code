"""Screen 6: Notebook — meetings + knowledge (process notes, ask-your-knowledge)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..agents.knowledge import KnowledgeAgent
from ..agents.meeting import MeetingAgent
from ..deps import RequestContext, get_current_user

router = APIRouter(prefix="/notebook", tags=["notebook"])
_meeting = MeetingAgent()
_knowledge = KnowledgeAgent()


@router.post("/meeting")
def process_meeting(payload: dict, ctx: RequestContext = Depends(get_current_user)) -> dict:
    return _meeting.process(ctx, payload.get("notes", ""))


@router.post("/ask")
def ask(payload: dict, ctx: RequestContext = Depends(get_current_user)) -> dict:
    hits = _knowledge.recall(ctx, payload.get("query", ""))
    return {"results": hits}
