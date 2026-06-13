"""Base class for specialist agents."""

from __future__ import annotations

from ..audit import record
from ..deps import RequestContext


class Agent:
    """A specialist agent. Domain-neutral; reads role from the profile."""

    name: str = "agent"

    def log(self, ctx: RequestContext, action: str, detail: dict | None = None) -> None:
        record(ctx, self.name, action, detail)
