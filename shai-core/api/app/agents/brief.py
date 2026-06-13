"""Brief agent — morning brief + EOD recap + risk scan."""

from __future__ import annotations

from datetime import datetime, timezone

from ..deps import RequestContext
from ..schemas import BriefResponse
from .base import Agent


class BriefAgent(Agent):
    name = "brief_agent"

    def build(self, ctx: RequestContext, *, eod: bool = False) -> BriefResponse:
        # TODO(sprint-3): pull real calendar/inbox/tasks/risks for this tenant and
        # let Claude assemble the narrative. Scaffold returns a structured stub.
        self.log(ctx, "eod_recap" if eod else "morning_brief")
        headline = (
            "End of day: here's what closed and what's still open."
            if eod
            else "Good morning. Here's what needs you today."
        )
        return BriefResponse(
            generated_at=datetime.now(timezone.utc),
            headline=headline,
            priorities=["Run a real day through SHAI Core"],
            calendar=[],
            inbox_needs_you=[],
            tasks_due=[],
            risks=[],
            eod=eod,
        )
