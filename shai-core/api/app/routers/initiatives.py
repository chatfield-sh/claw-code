"""Screen 5: Initiatives — persisted; advice spins off next-step tasks."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import repo
from ..agents.initiative import InitiativeAgent
from ..deps import RequestContext, get_current_user

router = APIRouter(prefix="/initiatives", tags=["initiatives"])
_agent = InitiativeAgent()


@router.get("")
def list_initiatives(ctx: RequestContext = Depends(get_current_user)) -> dict:
    rows = repo.list_initiatives(ctx)
    return {"initiatives": [dict(r) for r in (rows or [])]}


@router.post("")
def create_initiative(payload: dict, ctx: RequestContext = Depends(get_current_user)) -> dict:
    row = repo.create_initiative(ctx, payload.get("name", ""), payload.get("goal"))
    return {"initiative": dict(row) if row else payload}


@router.post("/advise")
def advise(payload: dict, ctx: RequestContext = Depends(get_current_user)) -> dict:
    name, goal = payload.get("name", ""), payload.get("goal", "")
    advice, tasks = _agent.advise(ctx, name, goal)
    # Spin the suggested next steps off into persisted tasks.
    persisted = []
    for t in tasks:
        row = repo.create_task(ctx, t.title, weight=t.weight, source=f"initiative:{name}")
        persisted.append(dict(row) if row else t.model_dump())
    return {"advice": advice, "next_steps": persisted}
