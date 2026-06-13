"""Screen 3: Tasks — ranked by weight."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..agents.task import TaskAgent
from ..deps import RequestContext, get_current_user
from ..schemas import Task

router = APIRouter(prefix="/tasks", tags=["tasks"])
_agent = TaskAgent()


@router.post("/rank", response_model=list[Task])
def rank(tasks: list[Task], ctx: RequestContext = Depends(get_current_user)) -> list[Task]:
    return _agent.rank(ctx, tasks)


@router.post("/extract", response_model=list[Task])
def extract(payload: dict, ctx: RequestContext = Depends(get_current_user)) -> list[Task]:
    return _agent.extract(ctx, payload.get("text", ""))
