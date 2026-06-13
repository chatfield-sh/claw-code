"""Google connectors: unconfigured by default, and the no-send invariant holds."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import google
from app.main import app

client = TestClient(app)


def test_not_configured_by_default():
    assert google.is_configured() is False


def test_auth_url_raises_when_unconfigured():
    with pytest.raises(google.GoogleNotConfigured):
        google.auth_url()


def test_auth_endpoint_returns_503_unconfigured():
    assert client.get("/google/auth").status_code == 503


def test_status_endpoint():
    # `configured` is derived from settings (deterministic); `connected` reflects
    # DB state, which the live integration tests may have populated, so only its
    # type is asserted here.
    body = client.get("/google/status").json()
    assert body["configured"] is False
    assert isinstance(body["connected"], bool)


def test_scopes_have_no_send_permission():
    # Compose (draft) yes; gmail.send must never be requested.
    assert not any("gmail.send" in s for s in google.SCOPES)
    assert any("gmail.compose" in s for s in google.SCOPES)
