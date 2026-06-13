"""Thin Postgres access layer.

Connections are lazy: if the database is unreachable (e.g. running tests or the
scaffold without docker), ``get_conn`` raises and callers that can degrade do so.
Every query in the app is expected to filter by ``tenant_id`` — that is the
multi-tenant seam, dormant today but enforced from day one.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # psycopg optional until the DB is wired
    psycopg = None  # type: ignore[assignment]
    dict_row = None  # type: ignore[assignment]

from .config import settings


@contextmanager
def get_conn() -> Iterator["psycopg.Connection"]:
    """Yield a dict-row connection. Raises if psycopg/DB is unavailable."""
    if psycopg is None:
        raise RuntimeError("psycopg is not installed; database access unavailable")
    conn = psycopg.connect(settings.database_url, row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def db_available() -> bool:
    """Best-effort check used by health + routers that can return seed data."""
    if psycopg is None:
        return False
    try:
        with get_conn() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False
