"""End-to-end smoke tests against the FastAPI app (offline, no DB/Claude)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["modules"] == ["generic"]


def test_brief():
    r = client.get("/brief")
    assert r.status_code == 200
    assert "headline" in r.json()


def test_insights_analyze():
    r = client.post("/insights/analyze", json={"raw_input": "revenue,1200\ncost,800", "label": "Q2"})
    assert r.status_code == 200
    body = r.json()
    assert body["insight"]["impact"] == 1200


def test_tasks_rank():
    payload = [
        {"title": "low", "weight": 1, "status": "open"},
        {"title": "high", "weight": 99, "status": "open"},
        {"title": "done", "weight": 50, "status": "done"},
    ]
    r = client.post("/tasks/rank", json=payload)
    assert r.status_code == 200
    ranked = r.json()
    assert ranked[0]["title"] == "high"
    assert ranked[-1]["title"] == "done"


def test_inbox_draft_is_never_sendable():
    r = client.post("/inbox/draft", json={"sender": "a@b.com", "subject": "hi", "body": "can you help?"})
    assert r.status_code == 200
    assert r.json()["sendable"] is False
