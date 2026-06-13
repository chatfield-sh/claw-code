"""Brief agent — morning brief + EOD recap + risk scan.

Reads real tenant-scoped rows via the repo when the database is available, and
falls back to a structured stub otherwise so the screen always renders.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .. import repo
from ..deps import RequestContext
from ..schemas import BriefResponse
from .base import Agent


class BriefAgent(Agent):
    name = "brief_agent"

    def build(self, ctx: RequestContext, *, eod: bool = False) -> BriefResponse:
        self.log(ctx, "eod_recap" if eod else "morning_brief")

        tasks = repo.list_tasks(ctx, status=None)
        risks = repo.open_risks(ctx)
        events = repo.upcoming_events(ctx)
        inbox = repo.inbox_needs_you(ctx)

        # repo returns None when the DB is unavailable -> use empty stubs.
        open_tasks = [t for t in (tasks or []) if t["status"] in ("open", "doing", "blocked")]
        priorities = [t["title"] for t in open_tasks[:3]] or ["Run a real day through SHAI Core"]
        tasks_due = [t["title"] for t in open_tasks if t.get("due")][:5]

        headline = (
            "End of day: here's what closed and what's still open."
            if eod
            else "Good morning. Here's what needs you today."
        )
        return BriefResponse(
            generated_at=datetime.now(timezone.utc),
            headline=headline,
            priorities=priorities,
            calendar=[e["title"] for e in (events or [])],
            inbox_needs_you=[f"{i['sender']}: {i['subject']}" for i in (inbox or [])],
            tasks_due=tasks_due,
            risks=[f"{r['severity'].upper()}: {r['title']}" for r in (risks or [])],
            eod=eod,
        )
