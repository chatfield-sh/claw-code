"""Tenant seam: with no Clerk configured, requests resolve to the dev identity."""

from __future__ import annotations

import asyncio

from app.config import settings
from app.deps import get_current_user


def test_dev_identity_when_clerk_absent():
    assert not settings.clerk_secret_key  # default scaffold config
    ctx = asyncio.run(get_current_user(authorization=None))
    assert ctx.tenant_id == settings.shai_dev_tenant_id
    assert ctx.user_id == settings.shai_dev_user_id
    assert ctx.role == "founder"


def test_bearer_ignored_without_clerk_config():
    # Even with a token, no Clerk config => dev identity (no accidental trust).
    ctx = asyncio.run(get_current_user(authorization="Bearer anything"))
    assert ctx.tenant_id == settings.shai_dev_tenant_id
