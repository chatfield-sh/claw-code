"""Module agent — the only agent that touches a domain.

It loads whatever module is active and runs parse -> analyze through the stable
Module contract. The domain lives entirely inside the loaded module; this agent
(and all of Core) stays domain-neutral.
"""

from __future__ import annotations

from ..deps import RequestContext
from ..modules import get_module
from ..schemas import AnalyzeResponse
from .base import Agent


class ModuleAgent(Agent):
    name = "module_agent"

    def run(self, ctx: RequestContext, raw_input: str, module_key: str = "generic",
            label: str | None = None) -> AnalyzeResponse:
        module = get_module(module_key)
        record_ = module.parse(ctx, raw_input, label=label)
        insight = module.analyze(ctx, record_)
        self.log(ctx, "analyze", {"module": module.key, "label": label})
        return AnalyzeResponse(record=record_, insight=insight)
