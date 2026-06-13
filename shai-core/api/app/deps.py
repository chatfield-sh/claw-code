"""The tenant seam.

`get_current_user` is the ONE place that resolves which tenant + user a request
belongs to. With Clerk configured it verifies the bearer token and maps the
Clerk subject to a ``user_profile``; without it (dev / single-user) it returns
the seeded dev identity. To go multi-tenant later you change resolution *here* —
every downstream query already filters by ``ctx.tenant_id``, so isolation
becomes live without a rewrite. This is the highest-leverage "design for the
future" decision in the build, kept deliberately small.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from fastapi import Header

from .config import settings

log = logging.getLogger("shai.deps")


@dataclass(frozen=True)
class RequestContext:
    """Resolved identity for a request. Pass this into every agent and query."""

    tenant_id: str
    user_id: str
    # Populated from user_profile; drives role-aware prompting (no hardcoded vertical).
    role: str = "operator"
    goals: tuple[str, ...] = ()
    comms_style: str = "direct, concise"


def _dev_context() -> RequestContext:
    return RequestContext(
        tenant_id=settings.shai_dev_tenant_id,
        user_id=settings.shai_dev_user_id,
        role="founder",
        goals=("protect daily unprompted opens", "validate the executive habit"),
        comms_style="direct, warm, concise",
    )


def _context_from_profile(row: dict) -> RequestContext:
    goals = row.get("goals") or []
    return RequestContext(
        tenant_id=str(row["tenant_id"]),
        user_id=str(row["id"]),
        role=row.get("role") or "operator",
        goals=tuple(goals),
        comms_style=row.get("comms_style") or "direct, concise",
    )


async def get_current_user(
    authorization: str | None = Header(default=None),
) -> RequestContext:
    """Resolve the request's tenant + user.

    1. No Clerk configured  -> seeded dev identity (single-user mode).
    2. Clerk configured     -> verify the bearer token, map the subject to a
       user_profile (auto-provisioned in the dev tenant on first sight). If
       verification or the DB lookup fails, fall back to the dev identity so the
       scaffold stays usable.
    """
    if not settings.clerk_secret_key or not authorization:
        return _dev_context()

    from .auth import verify_clerk_token  # lazy: avoids importing httpx/jwt at boot

    token = authorization.removeprefix("Bearer ").strip()
    claims = verify_clerk_token(token)
    if not claims or "sub" not in claims:
        log.info("falling back to dev identity: unverified token")
        return _dev_context()

    # Map Clerk subject -> user_profile (lazy import avoids a deps<->repo cycle).
    from . import repo

    profile = repo.get_or_create_user_by_clerk(
        clerk_id=claims["sub"],
        tenant_id=settings.shai_dev_tenant_id,
        name=claims.get("name") or claims.get("email") or "SHAI user",
    )
    return _context_from_profile(profile) if profile else _dev_context()
