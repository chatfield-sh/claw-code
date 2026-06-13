"""Audit-log viewer — tenant-scoped view of recorded actions."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import repo
from ..deps import RequestContext, get_current_user

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit(limit: int = 100, ctx: RequestContext = Depends(get_current_user)) -> dict:
    rows = repo.list_audit(ctx, min(limit, 500))
    return {"entries": [dict(r) for r in (rows or [])]}
