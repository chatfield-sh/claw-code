"""The /ask endpoint returns a well-formed answer offline (empty context)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ask_shape():
    r = client.post("/ask", json={"query": "what did we decide last week?"})
    assert r.status_code == 200
    body = r.json()
    assert "answer" in body
    assert "intent" in body
    assert set(body["sources"]) == {"notes", "memory"}
