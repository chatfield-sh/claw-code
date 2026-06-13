"""Task agent — extract + rank tasks by weight from any source."""

from __future__ import annotations

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
        """Pull action items from free text. TODO(sprint-3): Claude extraction."""
        self.log(ctx, "extract_tasks")
        tasks: list[Task] = []
        for line in source_text.splitlines():
            s = line.strip().lstrip("-*•").strip()
            if s.lower().startswith(("todo", "action", "[ ]")) or s.endswith(":"):
                tasks.append(Task(title=s, weight=10))
        return tasks
