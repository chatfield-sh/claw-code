"""Tenant-scoped persistence.

Every function filters by ``ctx.tenant_id`` — the multi-tenant seam is enforced
at the query layer, not bolted on later. All reads degrade to ``None`` when the
database is unavailable (so callers can fall back to seed/empty), and writes
degrade to returning the input unsaved. This keeps the API bootable and the
tests hermetic without a database.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from .db import get_conn
from .deps import RequestContext

log = logging.getLogger("shai.repo")


def _fetch(sql: str, params: tuple) -> list[dict] | None:
    """Run a SELECT. Returns rows, or None if the DB is unavailable."""
    try:
        with get_conn() as conn:
            return list(conn.execute(sql, params).fetchall())
    except Exception as exc:  # noqa: BLE001 - degrade on any DB error
        log.debug("repo fetch unavailable: %s", exc)
        return None


def _one(sql: str, params: tuple) -> dict | None:
    rows = _fetch(sql, params)
    return rows[0] if rows else None


# ---- Identity (used by the tenant seam) -----------------------------------
def get_or_create_user_by_clerk(clerk_id: str, tenant_id: str, name: str) -> dict | None:
    """Resolve a Clerk subject to a user_profile, provisioning on first sight.

    Takes a raw tenant_id (not a RequestContext) because it runs *during*
    identity resolution, before a context exists. Returns None if the DB is down.
    """
    existing = _one(
        "SELECT * FROM user_profile WHERE clerk_id=%s AND tenant_id=%s",
        (clerk_id, tenant_id),
    )
    if existing:
        return existing
    return _one(
        """
        INSERT INTO user_profile (tenant_id, clerk_id, name, role)
        VALUES (%s, %s, %s, 'operator') RETURNING *
        """,
        (tenant_id, clerk_id, name),
    )


# ---- Tasks ----------------------------------------------------------------
def list_tasks(ctx: RequestContext, status: str | None = None) -> list[dict] | None:
    if status:
        return _fetch(
            "SELECT * FROM task WHERE tenant_id=%s AND status=%s ORDER BY weight DESC",
            (ctx.tenant_id, status),
        )
    return _fetch(
        "SELECT * FROM task WHERE tenant_id=%s ORDER BY weight DESC", (ctx.tenant_id,)
    )


def create_task(ctx: RequestContext, title: str, weight: float = 0,
                detail: str | None = None, source: str | None = None,
                due: Any = None) -> dict | None:
    return _one(
        """
        INSERT INTO task (tenant_id, user_id, title, detail, weight, source, due)
        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *
        """,
        (ctx.tenant_id, ctx.user_id, title, detail, weight, source, due),
    )


def set_task_status(ctx: RequestContext, task_id: str, status: str) -> dict | None:
    return _one(
        "UPDATE task SET status=%s WHERE id=%s AND tenant_id=%s RETURNING *",
        (status, task_id, ctx.tenant_id),
    )


# ---- Notes / knowledge ----------------------------------------------------
def create_note(ctx: RequestContext, body: str, title: str | None = None,
                tags: list[str] | None = None) -> dict | None:
    return _one(
        """
        INSERT INTO note (tenant_id, user_id, title, body, tags)
        VALUES (%s, %s, %s, %s, %s) RETURNING *
        """,
        (ctx.tenant_id, ctx.user_id, title, body, tags or []),
    )


def search_notes(ctx: RequestContext, query: str, k: int = 5) -> list[dict] | None:
    """Text search fallback until embeddings land (sprint-4). Tenant-scoped."""
    return _fetch(
        """
        SELECT id, title, body, tags FROM note
        WHERE tenant_id=%s AND (body ILIKE %s OR coalesce(title,'') ILIKE %s)
        ORDER BY created_at DESC LIMIT %s
        """,
        (ctx.tenant_id, f"%{query}%", f"%{query}%", k),
    )


# ---- Initiatives ----------------------------------------------------------
def list_initiatives(ctx: RequestContext) -> list[dict] | None:
    return _fetch(
        "SELECT * FROM initiative WHERE tenant_id=%s ORDER BY created_at DESC",
        (ctx.tenant_id,),
    )


def create_initiative(ctx: RequestContext, name: str, goal: str | None = None) -> dict | None:
    return _one(
        """
        INSERT INTO initiative (tenant_id, user_id, name, goal)
        VALUES (%s, %s, %s, %s) RETURNING *
        """,
        (ctx.tenant_id, ctx.user_id, name, goal),
    )


# ---- Meetings -------------------------------------------------------------
def create_meeting(ctx: RequestContext, title: str, raw_notes: str, summary: str | None,
                   decisions: list, follow_up: str | None) -> dict | None:
    return _one(
        """
        INSERT INTO meeting (tenant_id, user_id, title, raw_notes, summary, decisions, follow_up)
        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *
        """,
        (ctx.tenant_id, ctx.user_id, title, raw_notes, summary,
         json.dumps(decisions), follow_up),
    )


# ---- Module records / insights -------------------------------------------
def create_module_record(ctx: RequestContext, module_key: str, label: str | None,
                         data: dict, raw_ref: str | None = None) -> dict | None:
    return _one(
        """
        INSERT INTO module_record (tenant_id, user_id, module_key, label, data, raw_ref)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING *
        """,
        (ctx.tenant_id, ctx.user_id, module_key, label, json.dumps(data), raw_ref),
    )


def create_module_insight(ctx: RequestContext, module_record_id: str, module_key: str,
                          insight: dict) -> dict | None:
    return _one(
        """
        INSERT INTO module_insight
            (tenant_id, module_record_id, module_key, headline, narrative,
             impact, impact_unit, action, severity)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *
        """,
        (ctx.tenant_id, module_record_id, module_key, insight.get("headline"),
         insight.get("narrative"), insight.get("impact"), insight.get("impact_unit"),
         insight.get("action"), insight.get("severity")),
    )


# ---- Google credentials + calendar sync -----------------------------------
def store_google_credential(ctx: RequestContext, access_token: str,
                            refresh_token: str | None, scope: str | None,
                            expires_at: Any) -> dict | None:
    return _one(
        """
        INSERT INTO google_credential
            (tenant_id, user_id, access_token, refresh_token, scope, expires_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (tenant_id, user_id) DO UPDATE SET
            access_token=EXCLUDED.access_token,
            refresh_token=COALESCE(EXCLUDED.refresh_token, google_credential.refresh_token),
            scope=EXCLUDED.scope, expires_at=EXCLUDED.expires_at, updated_at=now()
        RETURNING *
        """,
        (ctx.tenant_id, ctx.user_id, access_token, refresh_token, scope, expires_at),
    )


def get_google_credential(ctx: RequestContext) -> dict | None:
    return _one(
        "SELECT * FROM google_credential WHERE tenant_id=%s AND user_id=%s",
        (ctx.tenant_id, ctx.user_id),
    )


def upsert_calendar_event(ctx: RequestContext, google_id: str, title: str,
                          starts_at: Any, ends_at: Any, location: str | None) -> dict | None:
    return _one(
        """
        INSERT INTO calendar_event
            (tenant_id, user_id, google_id, title, starts_at, ends_at, location)
        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *
        """,
        (ctx.tenant_id, ctx.user_id, google_id, title, starts_at, ends_at, location),
    )


# ---- Brief snapshots (nightly cron) ---------------------------------------
def create_brief_snapshot(ctx: RequestContext, eod: bool, headline: str | None,
                          payload: dict) -> dict | None:
    return _one(
        """
        INSERT INTO brief_snapshot (tenant_id, user_id, eod, headline, payload)
        VALUES (%s, %s, %s, %s, %s) RETURNING *
        """,
        (ctx.tenant_id, ctx.user_id, eod, headline, json.dumps(payload, default=str)),
    )


def latest_brief_snapshot(ctx: RequestContext, eod: bool | None = None) -> dict | None:
    if eod is None:
        return _one(
            "SELECT * FROM brief_snapshot WHERE tenant_id=%s AND user_id=%s "
            "ORDER BY created_at DESC LIMIT 1",
            (ctx.tenant_id, ctx.user_id),
        )
    return _one(
        "SELECT * FROM brief_snapshot WHERE tenant_id=%s AND user_id=%s AND eod=%s "
        "ORDER BY created_at DESC LIMIT 1",
        (ctx.tenant_id, ctx.user_id, eod),
    )


def all_active_user_contexts() -> list[dict] | None:
    """Every (tenant_id, user_id, profile) — used by the cron to fan out."""
    return _fetch(
        "SELECT id AS user_id, tenant_id, role, goals, comms_style FROM user_profile",
        (),
    )


# ---- Brief aggregation ----------------------------------------------------
def open_risks(ctx: RequestContext) -> list[dict] | None:
    return _fetch(
        "SELECT title, severity FROM risk_item WHERE tenant_id=%s AND resolved=false "
        "ORDER BY created_at DESC",
        (ctx.tenant_id,),
    )


def upcoming_events(ctx: RequestContext, limit: int = 5) -> list[dict] | None:
    return _fetch(
        "SELECT title, starts_at FROM calendar_event WHERE tenant_id=%s "
        "AND starts_at >= now() ORDER BY starts_at LIMIT %s",
        (ctx.tenant_id, limit),
    )


def inbox_needs_you(ctx: RequestContext, limit: int = 5) -> list[dict] | None:
    return _fetch(
        "SELECT sender, subject FROM email_item WHERE tenant_id=%s "
        "AND status IN ('unread','triaged') ORDER BY stake DESC LIMIT %s",
        (ctx.tenant_id, limit),
    )
