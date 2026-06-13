"""Screen 6: Notebook — meetings + knowledge (persisted; recall via text search)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import repo
from ..agents.knowledge import KnowledgeAgent
from ..agents.meeting import MeetingAgent
from ..deps import RequestContext, get_current_user

router = APIRouter(prefix="/notebook", tags=["notebook"])
_meeting = MeetingAgent()
_knowledge = KnowledgeAgent()


@router.post("/meeting")
def process_meeting(payload: dict, ctx: RequestContext = Depends(get_current_user)) -> dict:
    notes = payload.get("notes", "")
    result = _meeting.process(ctx, notes)
    repo.create_meeting(
        ctx, payload.get("title", "Untitled meeting"), notes,
        result.get("summary"), result.get("decisions", []), result.get("follow_up"),
    )
    return result


@router.post("/note")
def add_note(payload: dict, ctx: RequestContext = Depends(get_current_user)) -> dict:
    row = repo.create_note(ctx, payload.get("body", ""), title=payload.get("title"),
                           tags=payload.get("tags"))
    return {"note": dict(row) if row else payload}


@router.post("/ask")
def ask(payload: dict, ctx: RequestContext = Depends(get_current_user)) -> dict:
    hits = _knowledge.recall(ctx, payload.get("query", ""))
    return {"results": hits}
