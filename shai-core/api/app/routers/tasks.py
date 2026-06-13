"""Screen 3: Tasks — ranked by weight; persisted per tenant."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import repo
from ..agents.task import TaskAgent
from ..deps import RequestContext, get_current_user
from ..schemas import Task

router = APIRouter(prefix="/tasks", tags=["tasks"])
_agent = TaskAgent()


def _to_task(row: dict) -> Task:
    return Task(
        id=str(row["id"]), title=row["title"], detail=row.get("detail"),
        weight=float(row["weight"]), status=row["status"],
        owner=row.get("owner"), due=row.get("due"),
    )


@router.get("", response_model=list[Task])
def list_tasks(status: str | None = None, ctx: RequestContext = Depends(get_current_user)) -> list[Task]:
    rows = repo.list_tasks(ctx, status)
    return [_to_task(r) for r in (rows or [])]


@router.post("", response_model=Task)
def create_task(task: Task, ctx: RequestContext = Depends(get_current_user)) -> Task:
    row = repo.create_task(ctx, task.title, weight=task.weight, detail=task.detail, due=task.due)
    return _to_task(row) if row else task  # echo input if DB unavailable


@router.post("/{task_id}/status", response_model=Task)
def set_status(task_id: str, payload: dict, ctx: RequestContext = Depends(get_current_user)) -> Task:
    row = repo.set_task_status(ctx, task_id, payload.get("status", "done"))
    return _to_task(row) if row else Task(id=task_id, title="", status=payload.get("status", "done"))


@router.post("/rank", response_model=list[Task])
def rank(tasks: list[Task], ctx: RequestContext = Depends(get_current_user)) -> list[Task]:
    return _agent.rank(ctx, tasks)


@router.post("/extract", response_model=list[Task])
def extract(payload: dict, ctx: RequestContext = Depends(get_current_user)) -> list[Task]:
    return _agent.extract(ctx, payload.get("text", ""))
