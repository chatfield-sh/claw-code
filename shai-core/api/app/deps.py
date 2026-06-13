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
import uuid
from dataclasses import dataclass

from fastapi import Header, HTTPException

from .config import settings

log = logging.getLogger("shai.deps")

# Stable namespace for deriving a tenant UUID from a Clerk org/user id.
_TENANT_NS = uuid.UUID("9f1d6d1e-3a2b-5c4d-8e7f-0a1b2c3d4e5f")


def _clerk_tenant_id(claims: dict) -> str:
    """Derive an isolated tenant per Clerk org (or per user when org-less).

    Never returns the shared dev tenant for an authenticated Clerk user, so
    isolation holds the moment a second account exists.
    """
    seed = claims.get("org_id") or claims["sub"]
    return str(uuid.uuid5(_TENANT_NS, str(seed)))


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
    base = RequestContext(
        tenant_id=settings.shai_dev_tenant_id,
        user_id=settings.shai_dev_user_id,
        role="founder",
        goals=("protect daily unprompted opens", "validate the executive habit"),
        comms_style="direct, warm, concise",
    )
    # Overlay the live profile so the settings screen actually drives prompting.
    from . import repo  # lazy: avoids a deps<->repo import cycle

    row = repo.get_user_profile(base)
    return _context_from_profile(row) if row else base


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

    1. Clerk NOT configured -> seeded dev identity (single-user / dev mode).
    2. Clerk configured     -> a valid bearer token is REQUIRED. A missing or
       invalid token returns 401 (never the privileged dev identity). The
       subject maps to a user_profile in a tenant isolated per Clerk org/user.
    """
    if not settings.clerk_secret_key:
        return _dev_context()  # dev mode only — no auth configured

    # Clerk is configured: authentication is mandatory and fails closed.
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")

    from .auth import verify_clerk_token  # lazy: avoids importing httpx/jwt at boot

    token = authorization.removeprefix("Bearer ").strip()
    claims = verify_clerk_token(token)
    if not claims or "sub" not in claims:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    from . import repo  # lazy import avoids a deps<->repo cycle

    tenant_id = _clerk_tenant_id(claims)
    repo.get_or_create_tenant(tenant_id, name=claims.get("org_id") or "personal")
    profile = repo.get_or_create_user_by_clerk(
        clerk_id=claims["sub"],
        tenant_id=tenant_id,
        name=claims.get("name") or claims.get("email") or "SHAI user",
    )
    if not profile:
        raise HTTPException(status_code=503, detail="Identity store unavailable")
    return _context_from_profile(profile)
