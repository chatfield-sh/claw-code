"""Screen 6: Notebook — meetings + knowledge (embedded; recall via pgvector)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import embeddings, repo
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
    title = payload.get("title", "Untitled meeting")
    repo.create_meeting(
        ctx, title, notes, result.get("summary"),
        result.get("decisions", []), result.get("follow_up"),
    )
    # Lay down an episodic memory of the meeting summary.
    summary = result.get("summary") or notes[:280]
    repo.add_memory(ctx, "episodic", f"Meeting '{title}': {summary}",
                    embedding=embeddings.embed_text(summary))
    return result


@router.post("/note")
def add_note(payload: dict, ctx: RequestContext = Depends(get_current_user)) -> dict:
    note = _knowledge.add_note(ctx, payload.get("body", ""), title=payload.get("title"),
                               tags=payload.get("tags"))
    if not note:
        return {"note": payload}
    row = {k: v for k, v in dict(note).items() if k != "embedding"}  # don't echo the vector
    return {"note": row}


@router.post("/ask")
def ask(payload: dict, ctx: RequestContext = Depends(get_current_user)) -> dict:
    hits = _knowledge.recall(ctx, payload.get("query", ""))
    return {"results": hits}
