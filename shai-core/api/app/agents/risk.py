"""Risk agent — derive risk_item rows from the tenant's live data.

Domain-neutral signals: overdue/blocked tasks and unanswered high-stake email.
Risks are deduped (one open risk per title), so a daily scan converges rather
than piling up duplicates. The Brief screen reads open risks, so this is what
populates the risk radar.
"""

from __future__ import annotations

from datetime import date

from .. import repo
from ..deps import RequestContext
from .base import Agent


class RiskAgent(Agent):
    name = "risk_agent"

    def scan(self, ctx: RequestContext) -> list[dict]:
        """Scan data, persist new risks, and return the ones created this run."""
        self.log(ctx, "risk_scan")
        created: list[dict] = []

        today = date.today()
        for t in repo.list_tasks(ctx) or []:
            if t["status"] == "blocked":
                created.append(self._add(ctx, f"Blocked task: {t['title']}", "amber"))
            elif t.get("due") and t["due"] < today and t["status"] != "done":
                created.append(self._add(ctx, f"Overdue task: {t['title']}", "red"))

        for e in repo.inbox_needs_you(ctx) or []:
            created.append(
                self._add(ctx, f"Unanswered high-stake email from {e['sender']}", "amber")
            )

        return [c for c in created if c]

    def _add(self, ctx: RequestContext, title: str, severity: str) -> dict | None:
        return repo.create_risk_item(ctx, title, severity)
