"""The nightly cron entrypoint runs offline and online."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app import jobs
from app.main import app

client = TestClient(app)


def test_run_daily_brief_generates_at_least_one():
    # No DB -> dev fallback context (1). With a DB -> one per user_profile.
    assert jobs.run_daily_brief(eod=False) >= 1


def test_main_morning_ok():
    assert jobs.main(["jobs", "morning"]) == 0


def test_main_eod_ok():
    assert jobs.main(["jobs", "eod"]) == 0


def test_main_rejects_unknown_mode():
    assert jobs.main(["jobs", "weekly"]) == 2


def test_brief_latest_endpoint_has_snapshot_key():
    body = client.get("/brief/latest").json()
    assert "snapshot" in body  # None without a DB/cron run; dict once generated
