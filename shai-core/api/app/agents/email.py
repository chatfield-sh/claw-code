"""Email agent — triage by stake + draft replies in the user's voice (no-send).

The trust gate forbids sending. Drafts are staged (pushed to Gmail Drafts in
production) and the human approves + sends.
"""

from __future__ import annotations

from ..claude import complete
from ..deps import RequestContext
from ..trust import Action, require_approval
from .base import Agent


class EmailAgent(Agent):
    name = "email_agent"

    def triage(self, ctx: RequestContext, sender: str, subject: str, body: str) -> float:
        """Return a stake score 0-100. Heuristic fallback when Claude is absent."""
        # TODO(sprint-2): score against the user's priorities + contacts.
        out = complete(
            ctx,
            system="Rate how much this email needs the user, 0-100. Reply with only a number.",
            user=f"From: {sender}\nSubject: {subject}\n\n{body[:2000]}",
            max_tokens=8,
        )
        if out:
            try:
                return max(0.0, min(100.0, float(out.strip().split()[0])))
            except (ValueError, IndexError):
                pass
        return 50.0 if "?" in body else 25.0

    def draft_reply(self, ctx: RequestContext, sender: str, subject: str, body: str) -> str:
        assert require_approval(Action.SEND), "sending must always require approval"
        self.log(ctx, "draft_reply", {"to": sender, "subject": subject})
        out = complete(
            ctx,
            system="Draft a reply in the user's voice. Do not send; this is a draft.",
            user=f"From: {sender}\nSubject: {subject}\n\n{body[:2000]}",
            max_tokens=600,
        )
        return out or f"Hi,\n\nThanks for your note re: {subject}. [draft — set ANTHROPIC_API_KEY]\n\nBest,"
