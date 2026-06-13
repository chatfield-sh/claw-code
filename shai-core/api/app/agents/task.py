"""Task agent — extract + rank tasks by weight from any source."""

from __future__ import annotations

import json

from ..claude import complete
from ..deps import RequestContext
from ..schemas import Task
from .base import Agent


class TaskAgent(Agent):
    name = "task_agent"

    def rank(self, ctx: RequestContext, tasks: list[Task]) -> list[Task]:
        """Rank by weight (desc), open before done. Pure + deterministic."""
        self.log(ctx, "rank_tasks", {"count": len(tasks)})
        order = {"open": 0, "doing": 0, "blocked": 1, "done": 2}
        return sorted(tasks, key=lambda t: (order.get(t.status, 0), -t.weight))

    def extract(self, ctx: RequestContext, source_text: str) -> list[Task]:
        """Pull action items from free text. Claude-driven, heuristic fallback."""
        self.log(ctx, "extract_tasks")
        out = complete(
            ctx,
            system=(
                "Extract concrete action items from the text. Return JSON: a list "
                'of objects {"title": str, "weight": number 0-100}. No prose.'
            ),
            user=source_text[:6000],
            max_tokens=600,
        )
        if out:
            try:
                data = json.loads(out[out.index("["): out.rindex("]") + 1])
                return [Task(title=d["title"], weight=float(d.get("weight", 10))) for d in data]
            except (ValueError, KeyError, TypeError):
                pass  # fall through to heuristic
        return self._heuristic_extract(source_text)

    @staticmethod
    def _heuristic_extract(source_text: str) -> list[Task]:
        tasks: list[Task] = []
        for line in source_text.splitlines():
            s = line.strip().lstrip("-*•").strip()
            if s.lower().startswith(("todo", "action", "[ ]")) or s.endswith(":"):
                tasks.append(Task(title=s, weight=10))
        return tasks
