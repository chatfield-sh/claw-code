"""The migration entrypoint never crashes and splits SQL correctly."""

from __future__ import annotations

from app import migrate


def test_main_returns_zero_even_without_db():
    # With a DB it applies the schema; without one it logs and returns 0.
    assert migrate.main() == 0


def test_statement_splitter_drops_blanks():
    assert migrate._statements("create a; create b; ; ") == ["create a", "create b"]
