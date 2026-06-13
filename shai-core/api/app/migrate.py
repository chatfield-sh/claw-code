"""Apply schema + seed — the container release step.

The schema is written with idempotent guards (CREATE ... IF NOT EXISTS, INSERT
... ON CONFLICT DO NOTHING), so running this on every deploy is safe. Each
statement runs in its own autocommit transaction: a failure (e.g. an extension
the platform already manages) is logged and skipped rather than aborting the
whole release.

    python -m app.migrate
"""

from __future__ import annotations

import logging
from pathlib import Path

from .config import settings

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None  # type: ignore[assignment]

log = logging.getLogger("shai.migrate")

# db/ sits next to app/ in the container image (/app/db) but one level up in the
# repo (shai-core/db). Resolve whichever exists.
_HERE = Path(__file__).resolve()
_DB_CANDIDATES = (_HERE.parent.parent / "db", _HERE.parent.parent.parent / "db")


def _db_dir() -> Path:
    for candidate in _DB_CANDIDATES:
        if candidate.exists():
            return candidate
    return _DB_CANDIDATES[0]


DB_DIR = _db_dir()


def _statements(sql: str) -> list[str]:
    # Strip `--` line comments first (they may contain ';' or ')'), then split on
    # ';'. Safe for this schema: no string literal contains '--', and there are
    # no dollar-quoted bodies. Keep it that way if you add functions/triggers
    # (or switch to applying the file with psql).
    stripped = []
    for line in sql.splitlines():
        idx = line.find("--")
        stripped.append(line if idx == -1 else line[:idx])
    return [s.strip() for s in "\n".join(stripped).split(";") if s.strip()]


def _apply_file(path: Path) -> int:
    if psycopg is None or not path.exists():
        return 0
    applied = 0
    with psycopg.connect(settings.database_url, autocommit=True) as conn:
        for stmt in _statements(path.read_text()):
            try:
                conn.execute(stmt)
                applied += 1
            except Exception as exc:  # noqa: BLE001 - idempotent; log + continue
                log.warning("migrate: skipped a statement: %s", exc)
    return applied


def apply_all() -> int:
    """Apply schema.sql then seed.sql. Returns the count of applied statements."""
    total = _apply_file(DB_DIR / "schema.sql")
    total += _apply_file(DB_DIR / "seed.sql")
    return total


def main() -> int:
    try:
        n = apply_all()
    except Exception as exc:  # noqa: BLE001 - never crash the container on migrate
        log.error("migrate failed: %s", exc)
        return 0
    print(f"migrate: applied {n} statement(s)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
