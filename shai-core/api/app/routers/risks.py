"""Risk radar — list open risks and trigger a scan."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import repo
from ..agents.risk import RiskAgent
from ..deps import RequestContext, get_current_user

router = APIRouter(prefix="/risks", tags=["risks"])
_agent = RiskAgent()


@router.get("")
def list_risks(ctx: RequestContext = Depends(get_current_user)) -> dict:
    rows = repo.open_risks(ctx)
    return {"risks": [dict(r) for r in (rows or [])]}


@router.post("/scan")
def scan(ctx: RequestContext = Depends(get_current_user)) -> dict:
    created = _agent.scan(ctx)
    return {"created": len(created)}
