"""Meeting agent — summary + decisions + action items + drafted follow-up."""

from __future__ import annotations

from ..claude import complete
from ..deps import RequestContext
from .base import Agent


class MeetingAgent(Agent):
    name = "meeting_agent"

    def process(self, ctx: RequestContext, notes: str) -> dict:
        """Return {summary, decisions[], action_items[], follow_up}."""
        self.log(ctx, "process_notes")
        out = complete(
            ctx,
            system=(
                "Summarize meeting notes. Return JSON: summary, decisions (list), "
                "action_items (list), follow_up (a short drafted message)."
            ),
            user=notes[:6000],
            max_tokens=900,
        )
        if out:
            import json

            try:
                return json.loads(out[out.index("{"): out.rindex("}") + 1])
            except (ValueError, TypeError):
                pass
        # Heuristic fallback.
        lines = [ln.strip() for ln in notes.splitlines() if ln.strip()]
        return {
            "summary": " ".join(lines)[:280],
            "decisions": [],
            "action_items": [ln for ln in lines if ln.lower().startswith(("action", "todo"))],
            "follow_up": "Thanks all — recap and next steps below. [draft]",
        }
