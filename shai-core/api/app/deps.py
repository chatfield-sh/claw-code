"""The tenant seam.

`get_current_user` is the ONE place that resolves which tenant + user a request
belongs to. Today it returns the single dev identity (or a Clerk-verified one).
To go multi-tenant later you flip the resolution here — every downstream query
already filters by ``ctx.tenant_id``, so isolation becomes live without a
rewrite. This is the highest-leverage "design for the future" decision in the
build, kept deliberately small.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header

from .config import settings


@dataclass(frozen=True)
class RequestContext:
    """Resolved identity for a request. Pass this into every agent and query."""

    tenant_id: str
    user_id: str
    # Populated from user_profile; drives role-aware prompting (no hardcoded vertical).
    role: str = "operator"
    goals: tuple[str, ...] = ()
    comms_style: str = "direct, concise"


async def get_current_user(
    authorization: str | None = Header(default=None),
) -> RequestContext:
    """Resolve the request's tenant + user.

    Dev / single-user: returns the seeded dev identity.
    Production: verify the Clerk session token in ``authorization`` and look up
    the matching ``user_profile`` row (TODO sprint-1). The shape of the returned
    context does not change — only the source of truth does.
    """
    # TODO(sprint-1): when settings.clerk_secret_key is set, verify the bearer
    # token, map the Clerk subject -> user_profile, and load role/goals/style.
    return RequestContext(
        tenant_id=settings.shai_dev_tenant_id,
        user_id=settings.shai_dev_user_id,
        role="founder",
        goals=("protect daily unprompted opens", "validate the executive habit"),
        comms_style="direct, warm, concise",
    )
