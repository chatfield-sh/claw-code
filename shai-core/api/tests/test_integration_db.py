"""Live-database integration tests for the persistence layer.

Skipped automatically unless a Postgres is reachable (so the rest of the suite
stays hermetic). CI provides a pgvector service with schema.sql + seed.sql
applied; these round-trip every repo path against it. Each test uses unique
values so reruns against the same ephemeral DB don't collide.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app import repo
from app.config import settings
from app.db import db_available
from app.deps import RequestContext

pytestmark = pytest.mark.skipif(not db_available(), reason="requires a live database")

CTX = RequestContext(
    tenant_id=settings.shai_dev_tenant_id,
    user_id=settings.shai_dev_user_id,
)


def _tag() -> str:
    return uuid.uuid4().hex[:8]


def test_task_roundtrip():
    title = f"task-{_tag()}"
    created = repo.create_task(CTX, title, weight=77, source="itest")
    assert created and created["title"] == title
    assert created["tenant_id"] == uuid.UUID(settings.shai_dev_tenant_id)

    listed = repo.list_tasks(CTX)
    assert listed is not None and any(t["id"] == created["id"] for t in listed)

    done = repo.set_task_status(CTX, str(created["id"]), "done")
    assert done and done["status"] == "done"


def test_note_search_roundtrip():
    token = _tag()
    repo.create_note(CTX, body=f"kickoff notes {token}", title="Kickoff", tags=["meeting"])
    hits = repo.search_notes(CTX, token)
    assert hits is not None and any(token in h["body"] for h in hits)


def test_initiative_roundtrip():
    name = f"init-{_tag()}"
    created = repo.create_initiative(CTX, name, goal="validate the habit")
    assert created and created["name"] == name
    rows = repo.list_initiatives(CTX)
    assert rows is not None and any(r["id"] == created["id"] for r in rows)


def test_module_record_and_insight_roundtrip():
    rec = repo.create_module_record(CTX, "generic", f"Q2-{_tag()}", {"revenue": 1200})
    assert rec is not None
    ins = repo.create_module_insight(
        CTX, str(rec["id"]), "generic",
        {"headline": "up", "narrative": "n", "impact": 1200, "impact_unit": "$",
         "action": "review", "severity": "amber"},
    )
    assert ins and ins["module_record_id"] == rec["id"]
    assert ins["severity"] == "amber"


def test_google_credential_upsert_roundtrip():
    repo.store_google_credential(CTX, "access-1", "refresh-1", "scope", None)
    first = repo.get_google_credential(CTX)
    assert first and first["access_token"] == "access-1"

    # Upsert: same (tenant, user) updates in place rather than duplicating.
    repo.store_google_credential(CTX, "access-2", None, "scope", None)
    second = repo.get_google_credential(CTX)
    assert second["access_token"] == "access-2"
    assert second["refresh_token"] == "refresh-1"  # preserved on null


def test_calendar_sync_and_brief_aggregation():
    start = datetime.now(timezone.utc) + timedelta(hours=2)
    end = start + timedelta(hours=1)
    repo.upsert_calendar_event(CTX, f"gid-{_tag()}", "Strategy review", start, end, "Zoom")

    upcoming = repo.upcoming_events(CTX)
    assert upcoming is not None and any(e["title"] == "Strategy review" for e in upcoming)
    # Aggregations return a list (possibly empty), never None, when the DB is up.
    assert repo.open_risks(CTX) is not None
    assert repo.inbox_needs_you(CTX) is not None


def test_brief_snapshot_roundtrip():
    created = repo.create_brief_snapshot(CTX, True, f"recap-{_tag()}", {"eod": True, "priorities": []})
    assert created and created["eod"] is True
    latest = repo.latest_brief_snapshot(CTX, eod=True)
    assert latest is not None and isinstance(latest["headline"], str)


def test_cron_persists_a_brief():
    from app import jobs

    n = jobs.run_daily_brief(eod=False)
    assert n >= 1  # at least the seeded dev user
    snap = repo.latest_brief_snapshot(CTX, eod=False)
    assert snap is not None and "payload" in snap


def test_email_item_upsert_dedupes_on_gmail_id():
    gid = f"gmail-{_tag()}"
    first = repo.upsert_email_item(CTX, gid, "a@b.com", "Hello", "snippet", 40, None)
    assert first is not None and first["stake"] == 40
    # Re-sync the same message with a new stake -> updates in place, no duplicate.
    second = repo.upsert_email_item(CTX, gid, "a@b.com", "Hello", "snippet", 75, None)
    assert second["id"] == first["id"]
    assert second["stake"] == 75

    listed = repo.list_email_items(CTX)
    assert listed is not None and sum(1 for r in listed if r["gmail_id"] == gid) == 1


def test_note_vector_recall_via_knowledge_agent():
    from app.agents.knowledge import KnowledgeAgent

    ka = KnowledgeAgent()
    token = _tag()
    ka.add_note(CTX, body=f"The {token} migration plan covers pgvector indexing", title="Plan")
    hits = ka.recall(CTX, f"{token} pgvector")
    assert any(token in h["body"] for h in hits)


def test_memory_search_roundtrip():
    from app import embeddings

    token = _tag()
    repo.add_memory(CTX, "semantic", f"remember {token}: launch is in May",
                    embedding=embeddings.embed_text(f"{token} launch May"))
    rows = repo.search_memory(CTX, embeddings.embed_text(f"{token} launch"))
    assert rows is not None and any(token in r["content"] for r in rows)


def test_ask_pulls_from_notes():
    from app.agents import Orchestrator
    from app.agents.knowledge import KnowledgeAgent

    token = _tag()
    KnowledgeAgent().add_note(CTX, body=f"{token} board meeting moved to Friday", title="Board")
    res = Orchestrator().answer(CTX, f"{token} board meeting")
    assert res["sources"]["notes"]  # recalled via pgvector
    assert any(token in n["body"] for n in res["sources"]["notes"])


def test_migrate_is_idempotent():
    from app import migrate

    assert migrate.apply_all() > 0
    assert migrate.apply_all() > 0  # second run is safe (idempotent guards)
    # Seed tasks are NOT-EXISTS-guarded, so re-running never duplicates them.
    rows = repo.list_tasks(CTX)
    seed_count = sum(1 for r in (rows or []) if r.get("source") == "seed")
    assert seed_count == 2


def test_get_or_create_user_by_clerk_is_idempotent():
    clerk_id = f"user_{_tag()}"
    first = repo.get_or_create_user_by_clerk(clerk_id, settings.shai_dev_tenant_id, "Test User")
    second = repo.get_or_create_user_by_clerk(clerk_id, settings.shai_dev_tenant_id, "Test User")
    assert first and second and first["id"] == second["id"]
    assert first["clerk_id"] == clerk_id
