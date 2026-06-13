"""Audit log helper. Every gated action and agent run is recorded (best-effort)."""

from __future__ import annotations

import json
import logging

from .db import get_conn
from .deps import RequestContext

log = logging.getLogger("shai.audit")


def record(ctx: RequestContext, actor: str, action: str, detail: dict | None = None) -> None:
    """Write an audit row. Falls back to logging if the DB is unavailable."""
    payload = detail or {}
    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO audit_log (tenant_id, user_id, actor, action, detail)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (ctx.tenant_id, ctx.user_id, actor, action, json.dumps(payload)),
            )
    except Exception:
        log.info("audit %s/%s by %s: %s", ctx.tenant_id, action, actor, payload)
