"""Profile — role / goals / comms style that drive role-aware prompting."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import repo
from ..deps import RequestContext, get_current_user

router = APIRouter(prefix="/profile", tags=["profile"])


def _view(ctx: RequestContext, row: dict | None) -> dict:
    """Return the profile, falling back to the resolved context when no DB row."""
    if row:
        return {
            "name": row.get("name"),
            "role": row.get("role"),
            "goals": row.get("goals") or [],
            "comms_style": row.get("comms_style"),
        }
    return {"name": None, "role": ctx.role, "goals": list(ctx.goals),
            "comms_style": ctx.comms_style}


@router.get("")
def get_profile(ctx: RequestContext = Depends(get_current_user)) -> dict:
    return _view(ctx, repo.get_user_profile(ctx))


@router.put("")
def update_profile(payload: dict, ctx: RequestContext = Depends(get_current_user)) -> dict:
    row = repo.update_user_profile(
        ctx,
        name=payload.get("name"),
        role=payload.get("role"),
        goals=payload.get("goals"),
        comms_style=payload.get("comms_style"),
    )
    return _view(ctx, row)
