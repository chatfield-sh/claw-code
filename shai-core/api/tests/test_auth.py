"""Tenant seam + Clerk verification security properties."""

from __future__ import annotations

import asyncio

import jwt
import pytest
from fastapi import HTTPException

from app import auth
from app.config import settings
from app.deps import get_current_user


# ---- Dev mode (no Clerk) ---------------------------------------------------
def test_dev_identity_when_clerk_absent():
    assert not settings.clerk_secret_key  # default scaffold config
    ctx = asyncio.run(get_current_user(authorization=None))
    assert ctx.tenant_id == settings.shai_dev_tenant_id
    assert ctx.user_id == settings.shai_dev_user_id
    assert ctx.role == "founder"


def test_bearer_ignored_without_clerk_config():
    # No Clerk config => dev identity (no accidental trust of a bearer).
    ctx = asyncio.run(get_current_user(authorization="Bearer anything"))
    assert ctx.tenant_id == settings.shai_dev_tenant_id


# ---- Clerk configured: fail closed ----------------------------------------
def test_missing_token_is_401_when_clerk_configured(monkeypatch):
    monkeypatch.setattr(settings, "clerk_secret_key", "sk_test_x")
    monkeypatch.setattr(settings, "clerk_issuer", "https://good.clerk.accounts.dev")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_current_user(authorization=None))
    assert exc.value.status_code == 401


def test_invalid_token_is_401_not_dev_fallback(monkeypatch):
    monkeypatch.setattr(settings, "clerk_secret_key", "sk_test_x")
    monkeypatch.setattr(settings, "clerk_issuer", "https://good.clerk.accounts.dev")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_current_user(authorization="Bearer garbage.token.here"))
    assert exc.value.status_code == 401


# ---- Issuer pinning --------------------------------------------------------
def test_verify_rejects_foreign_issuer_without_network(monkeypatch):
    # A token from an attacker-controlled issuer is rejected before any JWKS
    # fetch — proving the issuer is pinned, not taken from the token.
    monkeypatch.setattr(settings, "clerk_issuer", "https://good.clerk.accounts.dev")
    forged = jwt.encode({"iss": "https://evil.example", "sub": "attacker"}, "k", algorithm="HS256")
    assert auth.verify_clerk_token(forged) is None


def test_verify_refuses_when_issuer_unconfigured(monkeypatch):
    monkeypatch.setattr(settings, "clerk_issuer", "")
    token = jwt.encode({"iss": "https://anything", "sub": "x"}, "k", algorithm="HS256")
    assert auth.verify_clerk_token(token) is None
