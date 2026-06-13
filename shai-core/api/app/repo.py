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

from . import embeddings, security
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
def get_or_create_tenant(tenant_id: str, name: str) -> dict | None:
    """Ensure a tenant row exists (one per Clerk org/user). None if DB is down."""
    existing = _one("SELECT * FROM tenant WHERE id=%s", (tenant_id,))
    if existing:
        return existing
    return _one(
        "INSERT INTO tenant (id, name) VALUES (%s, %s) "
        "ON CONFLICT (id) DO NOTHING RETURNING *",
        (tenant_id, name),
    )


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


# ---- Profile (role/goals/comms drive role-aware prompting) -----------------
def get_user_profile(ctx: RequestContext) -> dict | None:
    return _one(
        "SELECT id, tenant_id, name, role, goals, comms_style FROM user_profile "
        "WHERE id=%s AND tenant_id=%s",
        (ctx.user_id, ctx.tenant_id),
    )


def update_user_profile(ctx: RequestContext, *, name: str | None = None,
                        role: str | None = None, goals: list[str] | None = None,
                        comms_style: str | None = None) -> dict | None:
    """Update only the provided fields (COALESCE keeps the rest)."""
    return _one(
        """
        UPDATE user_profile SET
            name = COALESCE(%s, name),
            role = COALESCE(%s, role),
            goals = COALESCE(%s, goals),
            comms_style = COALESCE(%s, comms_style)
        WHERE id=%s AND tenant_id=%s
        RETURNING id, tenant_id, name, role, goals, comms_style
        """,
        (name, role, json.dumps(goals) if goals is not None else None,
         comms_style, ctx.user_id, ctx.tenant_id),
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
                tags: list[str] | None = None,
                embedding: list[float] | None = None) -> dict | None:
    vec = embeddings.to_pgvector(embedding) if embedding else None
    return _one(
        """
        INSERT INTO note (tenant_id, user_id, title, body, tags, embedding)
        VALUES (%s, %s, %s, %s, %s, %s::vector) RETURNING *
        """,
        (ctx.tenant_id, ctx.user_id, title, body, tags or [], vec),
    )


def search_notes(ctx: RequestContext, query: str, k: int = 5) -> list[dict] | None:
    """Text search. Tenant-scoped. Used as a recall fallback."""
    return _fetch(
        """
        SELECT id, title, body, tags FROM note
        WHERE tenant_id=%s AND (body ILIKE %s OR coalesce(title,'') ILIKE %s)
        ORDER BY created_at DESC LIMIT %s
        """,
        (ctx.tenant_id, f"%{query}%", f"%{query}%", k),
    )


def search_notes_vector(ctx: RequestContext, embedding: list[float],
                        k: int = 5) -> list[dict] | None:
    """Semantic recall over this tenant's embedded notes (pgvector cosine)."""
    return _fetch(
        """
        SELECT id, title, body, tags FROM note
        WHERE tenant_id=%s AND embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector LIMIT %s
        """,
        (ctx.tenant_id, embeddings.to_pgvector(embedding), k),
    )


# ---- Memory (4 tiers, embedded) -------------------------------------------
def add_memory(ctx: RequestContext, tier: str, content: str,
               embedding: list[float] | None = None) -> dict | None:
    vec = embeddings.to_pgvector(embedding) if embedding else None
    return _one(
        """
        INSERT INTO memory (tenant_id, user_id, tier, content, embedding)
        VALUES (%s, %s, %s, %s, %s::vector) RETURNING *
        """,
        (ctx.tenant_id, ctx.user_id, tier, content, vec),
    )


def search_memory(ctx: RequestContext, embedding: list[float], k: int = 5,
                  tiers: tuple[str, ...] | None = None) -> list[dict] | None:
    """Semantic recall over this tenant's memory, optionally filtered by tier."""
    if tiers:
        return _fetch(
            """
            SELECT id, tier, content FROM memory
            WHERE tenant_id=%s AND embedding IS NOT NULL AND tier = ANY(%s)
            ORDER BY embedding <=> %s::vector LIMIT %s
            """,
            (ctx.tenant_id, list(tiers), embeddings.to_pgvector(embedding), k),
        )
    return _fetch(
        """
        SELECT id, tier, content FROM memory
        WHERE tenant_id=%s AND embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector LIMIT %s
        """,
        (ctx.tenant_id, embeddings.to_pgvector(embedding), k),
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


# ---- Email items (ingestion) ----------------------------------------------
def upsert_email_item(ctx: RequestContext, gmail_id: str, sender: str | None,
                      subject: str | None, snippet: str | None, stake: float,
                      received_at: Any) -> dict | None:
    """Insert or update a synced inbox message (dedupe on tenant + gmail_id)."""
    return _one(
        """
        INSERT INTO email_item
            (tenant_id, user_id, gmail_id, sender, subject, snippet, stake, status, received_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'triaged', %s)
        ON CONFLICT (tenant_id, gmail_id) DO UPDATE SET
            sender=EXCLUDED.sender, subject=EXCLUDED.subject,
            snippet=EXCLUDED.snippet, stake=EXCLUDED.stake
        RETURNING *
        """,
        (ctx.tenant_id, ctx.user_id, gmail_id, sender, subject, snippet, stake, received_at),
    )


def list_email_items(ctx: RequestContext, limit: int = 50) -> list[dict] | None:
    return _fetch(
        "SELECT * FROM email_item WHERE tenant_id=%s ORDER BY stake DESC, received_at DESC "
        "NULLS LAST LIMIT %s",
        (ctx.tenant_id, limit),
    )


# ---- Google credentials + calendar sync -----------------------------------
def store_google_credential(ctx: RequestContext, access_token: str,
                            refresh_token: str | None, scope: str | None,
                            expires_at: Any) -> dict | None:
    # Tokens are encrypted at rest; the DB never holds plaintext.
    row = _one(
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
        (ctx.tenant_id, ctx.user_id, security.encrypt(access_token),
         security.encrypt(refresh_token), scope, expires_at),
    )
    return _decrypt_credential(row)


def get_google_credential(ctx: RequestContext) -> dict | None:
    row = _one(
        "SELECT * FROM google_credential WHERE tenant_id=%s AND user_id=%s",
        (ctx.tenant_id, ctx.user_id),
    )
    return _decrypt_credential(row)


def _decrypt_credential(row: dict | None) -> dict | None:
    """Return the row with token columns decrypted for use by the caller."""
    if not row:
        return row
    row = dict(row)
    row["access_token"] = security.decrypt(row.get("access_token"))
    row["refresh_token"] = security.decrypt(row.get("refresh_token"))
    return row


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


# ---- Audit log (viewer) ----------------------------------------------------
def list_audit(ctx: RequestContext, limit: int = 100) -> list[dict] | None:
    return _fetch(
        "SELECT actor, action, detail, created_at FROM audit_log "
        "WHERE tenant_id=%s ORDER BY created_at DESC LIMIT %s",
        (ctx.tenant_id, limit),
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
def create_risk_item(ctx: RequestContext, title: str, severity: str = "amber",
                     detail: str | None = None) -> dict | None:
    """Create a risk, deduped on an open risk with the same title."""
    return _one(
        """
        INSERT INTO risk_item (tenant_id, user_id, title, severity, detail)
        SELECT %s, %s, %s, %s, %s
        WHERE NOT EXISTS (
            SELECT 1 FROM risk_item
            WHERE tenant_id=%s AND title=%s AND resolved=false
        )
        RETURNING *
        """,
        (ctx.tenant_id, ctx.user_id, title, severity, detail, ctx.tenant_id, title),
    )


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
