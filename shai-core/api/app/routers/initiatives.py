"""Screen 5: Initiatives — advice -> next-step tasks."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..agents.initiative import InitiativeAgent
from ..deps import RequestContext, get_current_user

router = APIRouter(prefix="/initiatives", tags=["initiatives"])
_agent = InitiativeAgent()


@router.post("/advise")
def advise(payload: dict, ctx: RequestContext = Depends(get_current_user)) -> dict:
    advice, tasks = _agent.advise(ctx, payload.get("name", ""), payload.get("goal", ""))
    return {"advice": advice, "next_steps": [t.model_dump() for t in tasks]}
