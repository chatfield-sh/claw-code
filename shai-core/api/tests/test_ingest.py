"""Ingestion is inert without Google configured/connected (hermetic)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import ingest, jobs
from app.deps import RequestContext
from app.main import app

client = TestClient(app)
CTX = RequestContext(tenant_id="t", user_id="u")


def test_sync_inbox_noop_without_google():
    assert ingest.sync_inbox(CTX) == 0


def test_sync_calendar_noop_without_google():
    assert ingest.sync_calendar(CTX) == 0


def test_run_sync_is_zero_without_google():
    assert jobs.run_sync() == {"emails": 0, "events": 0}


def test_jobs_main_sync_ok():
    assert jobs.main(["jobs", "sync"]) == 0


def test_inbox_sync_requires_google_configured():
    assert client.post("/inbox/sync").status_code == 400


def test_calendar_sync_requires_google_configured():
    assert client.post("/google/calendar/sync").status_code == 400


def test_inbox_list_endpoint_shape():
    r = client.get("/inbox")
    assert r.status_code == 200
    assert "items" in r.json()
