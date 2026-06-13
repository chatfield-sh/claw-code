"""Screen 1: Brief — morning brief + EOD recap (on-demand and persisted)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import repo
from ..agents.brief import BriefAgent
from ..deps import RequestContext, get_current_user
from ..schemas import BriefResponse

router = APIRouter(prefix="/brief", tags=["brief"])
_agent = BriefAgent()


@router.get("", response_model=BriefResponse)
def get_brief(eod: bool = False, ctx: RequestContext = Depends(get_current_user)) -> BriefResponse:
    """Build a brief on demand."""
    return _agent.build(ctx, eod=eod)


@router.get("/latest")
def latest(eod: bool | None = None, ctx: RequestContext = Depends(get_current_user)) -> dict:
    """Return the most recent cron-generated snapshot, or None if none exist."""
    snap = repo.latest_brief_snapshot(ctx, eod)
    if not snap:
        return {"snapshot": None}
    return {
        "snapshot": {
            "eod": snap["eod"],
            "headline": snap["headline"],
            "payload": snap["payload"],
            "created_at": snap["created_at"],
        }
    }
