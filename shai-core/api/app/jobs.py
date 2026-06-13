"""Scheduled jobs — the nightly cron that closes the daily loop.

`run_daily_brief(eod=False)` at morning and `eod=True` at night generate a brief
for every active user, persist it as a brief_snapshot, and (best-effort) record
the run in the audit log. The Brief screen then opens to a brief that was
generated for you, rather than computed only on demand.

Fan-out is tenant-aware from day one: it iterates every user_profile and builds
a per-user RequestContext, so going multi-tenant needs no change here.

Run from cron:

    # crontab — 06:30 morning brief, 18:30 EOD recap (server local time)
    30 6  * * *  cd /srv/shai/api && . .venv/bin/activate && python -m app.jobs morning
    30 18 * * *  cd /srv/shai/api && . .venv/bin/activate && python -m app.jobs eod
"""

from __future__ import annotations

import sys

from . import ingest, repo
from .agents.brief import BriefAgent
from .audit import record
from .config import settings
from .deps import RequestContext

_brief = BriefAgent()


def _contexts() -> list[RequestContext]:
    """Every active user's context. Falls back to the dev identity with no DB."""
    rows = repo.all_active_user_contexts()
    if not rows:
        return [
            RequestContext(
                tenant_id=settings.shai_dev_tenant_id,
                user_id=settings.shai_dev_user_id,
                role="founder",
            )
        ]
    return [
        RequestContext(
            tenant_id=str(r["tenant_id"]),
            user_id=str(r["user_id"]),
            role=r.get("role") or "operator",
            goals=tuple(r.get("goals") or ()),
            comms_style=r.get("comms_style") or "direct, concise",
        )
        for r in rows
    ]


def run_daily_brief(eod: bool = False) -> int:
    """Generate + persist a brief for every active user. Returns the count."""
    count = 0
    for ctx in _contexts():
        brief = _brief.build(ctx, eod=eod)
        repo.create_brief_snapshot(ctx, eod, brief.headline, brief.model_dump())
        record(ctx, "cron", "daily_brief", {"eod": eod})
        count += 1
    return count


def run_sync() -> dict:
    """Ingest Gmail + calendar for every connected user. Safe with none connected."""
    emails = events = 0
    for ctx in _contexts():
        emails += ingest.sync_inbox(ctx)
        events += ingest.sync_calendar(ctx)
        if emails or events:
            record(ctx, "cron", "ingest", {"emails": emails, "events": events})
    return {"emails": emails, "events": events}


def main(argv: list[str]) -> int:
    mode = (argv[1] if len(argv) > 1 else "morning").lower()
    if mode == "sync":
        result = run_sync()
        print(f"synced {result['emails']} email(s), {result['events']} event(s)")
        return 0
    if mode not in {"morning", "eod"}:
        print("usage: python -m app.jobs [morning|eod|sync]", file=sys.stderr)
        return 2
    n = run_daily_brief(eod=(mode == "eod"))
    print(f"generated {n} {mode} brief(s)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv))
