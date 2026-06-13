"""Persistence wiring — degradation contract.

These assert that the app stays usable when *no* database is present: repo reads
return None and HTTP endpoints return empty/echoed payloads. They only make
sense without a DB, so the absence-asserting cases skip when one is reachable
(CI runs them in a no-DB unit pass; the live round-trip is covered by
test_integration_db.py).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import repo
from app.db import db_available
from app.deps import RequestContext
from app.main import app

client = TestClient(app)
CTX = RequestContext(tenant_id="t", user_id="u")

requires_no_db = pytest.mark.skipif(
    db_available(), reason="degradation path is only observable without a database"
)


@requires_no_db
def test_repo_reads_return_none_without_db():
    assert repo.list_tasks(CTX) is None
    assert repo.open_risks(CTX) is None
    assert repo.search_notes(CTX, "x") is None


@requires_no_db
def test_list_tasks_endpoint_empty_without_db():
    r = client.get("/tasks")
    assert r.status_code == 200
    assert r.json() == []


@requires_no_db
def test_notebook_ask_returns_results_key_without_db():
    r = client.post("/notebook/ask", json={"query": "kickoff"})
    assert r.status_code == 200
    assert r.json()["results"] == []


def test_create_task_returns_task_shape():
    # Echoes input without a DB; returns the persisted row with one. Either way
    # the response carries the same title/weight.
    r = client.post("/tasks", json={"title": "ship it", "weight": 42})
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "ship it"
    assert body["weight"] == 42


def test_initiative_advise_returns_next_steps():
    r = client.post("/initiatives/advise", json={"name": "SHAI", "goal": "validate habit"})
    assert r.status_code == 200
    assert isinstance(r.json()["next_steps"], list)


def test_health_reports_new_surfaces():
    body = client.get("/health").json()
    assert "google" in body and "clerk" in body
    assert body["google"] is False and body["clerk"] is False
