"""Prod config guard, structured logging, audit viewer."""

from __future__ import annotations

import json
import logging

from fastapi.testclient import TestClient

from app.config import DEFAULT_SECRET, Settings
from app.main import app
from app.observability import JsonFormatter

client = TestClient(app)


# ---- Config guard ----------------------------------------------------------
def test_dev_allows_default_secret():
    s = Settings(shai_env="dev", shai_secret_key=DEFAULT_SECRET)
    assert s.problems() == []


def test_prod_rejects_default_secret():
    s = Settings(shai_env="prod", shai_secret_key=DEFAULT_SECRET)
    assert any("SHAI_SECRET_KEY" in p for p in s.problems())


def test_prod_requires_issuer_when_clerk_enabled():
    s = Settings(shai_env="prod", shai_secret_key="strong-secret",
                 clerk_secret_key="sk_live_x", clerk_issuer="")
    assert any("CLERK_ISSUER" in p for p in s.problems())


def test_prod_clean_config_has_no_problems():
    s = Settings(shai_env="prod", shai_secret_key="strong-secret",
                 clerk_secret_key="sk_live_x", clerk_issuer="https://x.clerk.accounts.dev")
    assert s.problems() == []


# ---- Structured logging ----------------------------------------------------
def test_json_formatter_emits_valid_json():
    rec = logging.LogRecord("shai.request", logging.INFO, __file__, 1, "request", None, None)
    rec.request_id = "abc12345"
    rec.status = 200
    out = json.loads(JsonFormatter().format(rec))
    assert out["msg"] == "request" and out["request_id"] == "abc12345" and out["status"] == 200


def test_response_carries_request_id_header():
    r = client.get("/health")
    assert r.headers.get("X-Request-ID")


# ---- Audit viewer ----------------------------------------------------------
def test_audit_endpoint_shape():
    r = client.get("/audit")
    assert r.status_code == 200
    assert "entries" in r.json()
