"""Brief agent — morning brief + EOD recap + risk scan.

Reads real tenant-scoped rows via the repo when the database is available, and
composes the headline with Claude from the actual day's data (falling back to a
static line offline). Always returns a structured BriefResponse so the screen
renders regardless of DB/Claude availability.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .. import repo
from ..claude import complete
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
        calendar = [e["title"] for e in (events or [])]
        inbox_lines = [f"{i['sender']}: {i['subject']}" for i in (inbox or [])]
        risk_lines = [f"{r['severity'].upper()}: {r['title']}" for r in (risks or [])]

        headline = self._headline(ctx, eod, priorities, calendar, inbox_lines, risk_lines)

        return BriefResponse(
            generated_at=datetime.now(timezone.utc),
            headline=headline,
            priorities=priorities,
            calendar=calendar,
            inbox_needs_you=inbox_lines,
            tasks_due=tasks_due,
            risks=risk_lines,
            eod=eod,
        )

    def _headline(self, ctx: RequestContext, eod: bool, priorities: list[str],
                  calendar: list[str], inbox: list[str], risks: list[str]) -> str:
        kind = "end-of-day recap" if eod else "morning brief"
        out = complete(
            ctx,
            system=(
                f"Write a single-sentence {kind} headline for an executive. Be "
                "specific to the data; no preamble, no markdown. One sentence."
            ),
            user=(
                f"Priorities: {priorities}\nCalendar: {calendar}\n"
                f"Inbox needs you: {inbox}\nRisks: {risks}"
            ),
            max_tokens=80,
        )
        if out:
            return out.strip().split("\n")[0]
        return (
            "End of day: here's what closed and what's still open."
            if eod
            else "Good morning. Here's what needs you today."
        )
