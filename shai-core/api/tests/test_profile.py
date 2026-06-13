"""Profile endpoint shape + offline fallback to the resolved context."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_profile_shape():
    r = client.get("/profile")
    assert r.status_code == 200
    assert set(r.json()) == {"name", "role", "goals", "comms_style"}


def test_update_profile_returns_shape():
    original = client.get("/profile").json()  # restore after, to avoid polluting
    try:
        r = client.put("/profile", json={"role": "operator"})
        assert r.status_code == 200
        assert "role" in r.json() and "goals" in r.json()
    finally:
        client.put("/profile", json={
            "name": original.get("name"), "role": original.get("role"),
            "goals": original.get("goals"), "comms_style": original.get("comms_style"),
        })
