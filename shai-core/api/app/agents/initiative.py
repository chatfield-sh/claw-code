"""Initiative agent — advice on any initiative -> next-step tasks.

Was the hotel build's "Founder agent"; now generic. Works for any venture
because it reasons from the user's profile + the initiative's goal, not a
hardcoded industry.
"""

from __future__ import annotations

from ..claude import complete
from ..deps import RequestContext
from ..schemas import Task
from .base import Agent


class InitiativeAgent(Agent):
    name = "initiative_agent"

    def advise(self, ctx: RequestContext, name: str, goal: str) -> tuple[str, list[Task]]:
        """Return (advice, next_step_tasks)."""
        self.log(ctx, "advise", {"initiative": name})
        out = complete(
            ctx,
            system=(
                "Advise on an initiative. Return JSON: advice (string) and "
                "next_steps (list of short task titles)."
            ),
            user=f"Initiative: {name}\nGoal: {goal}",
            max_tokens=700,
        )
        if out:
            import json

            try:
                data = json.loads(out[out.index("{"): out.rindex("}") + 1])
                tasks = [Task(title=t, weight=20) for t in data.get("next_steps", [])]
                return data.get("advice", ""), tasks
            except (ValueError, TypeError):
                pass
        return (
            f"Clarify the single outcome that proves '{name}' is working, then work backward.",
            [Task(title=f"Define the success metric for {name}", weight=20)],
        )
