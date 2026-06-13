"""Persistence wiring degrades cleanly with no database (hermetic).

These assert the *contract* of degradation: reads return None at the repo layer
and empty/echoed payloads at the HTTP layer, so the app stays usable offline.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import repo
from app.deps import RequestContext
from app.main import app

client = TestClient(app)
CTX = RequestContext(tenant_id="t", user_id="u")


def test_repo_reads_return_none_without_db():
    assert repo.list_tasks(CTX) is None
    assert repo.open_risks(CTX) is None
    assert repo.search_notes(CTX, "x") is None


def test_list_tasks_endpoint_empty_without_db():
    r = client.get("/tasks")
    assert r.status_code == 200
    assert r.json() == []


def test_create_task_echoes_input_without_db():
    r = client.post("/tasks", json={"title": "ship it", "weight": 42})
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "ship it"
    assert body["weight"] == 42


def test_initiative_advise_returns_next_steps():
    r = client.post("/initiatives/advise", json={"name": "SHAI", "goal": "validate habit"})
    assert r.status_code == 200
    assert isinstance(r.json()["next_steps"], list)


def test_notebook_ask_returns_results_key():
    r = client.post("/notebook/ask", json={"query": "kickoff"})
    assert r.status_code == 200
    assert r.json()["results"] == []


def test_health_reports_new_surfaces():
    body = client.get("/health").json()
    assert "google" in body and "clerk" in body
    assert body["google"] is False and body["clerk"] is False
