"""Orchestrator — classify intent, route to a specialist, enforce trust, log.

The orchestrator is domain-neutral: it knows the *jobs*, not any industry. It
retrieves relevant memory, picks the right specialist, runs it behind the trust
gate, and records the action in the audit log.
"""

from __future__ import annotations

from enum import Enum

from ..audit import record
from ..deps import RequestContext
from .brief import BriefAgent
from .email import EmailAgent
from .initiative import InitiativeAgent
from .knowledge import KnowledgeAgent
from .meeting import MeetingAgent
from .module_agent import ModuleAgent
from .task import TaskAgent


class Intent(str, Enum):
    BRIEF = "brief"
    EMAIL = "email"
    TASK = "task"
    MEETING = "meeting"
    KNOWLEDGE = "knowledge"
    INITIATIVE = "initiative"
    MODULE = "module"


# Lightweight keyword routing for the scaffold.
# TODO(sprint-1): replace with a Claude classifier seeded from the profile.
_KEYWORDS: dict[Intent, tuple[str, ...]] = {
    Intent.BRIEF: ("brief", "morning", "recap", "eod", "today"),
    Intent.EMAIL: ("email", "inbox", "reply", "draft"),
    Intent.TASK: ("task", "todo", "priority", "rank"),
    Intent.MEETING: ("meeting", "notes", "transcript", "follow up"),
    Intent.KNOWLEDGE: ("note", "knowledge", "recall", "remember", "ask"),
    Intent.INITIATIVE: ("initiative", "venture", "project", "plan"),
    Intent.MODULE: ("insight", "data", "module", "analyze", "numbers"),
}


class Orchestrator:
    name = "orchestrator"

    def __init__(self) -> None:
        self.brief = BriefAgent()
        self.email = EmailAgent()
        self.task = TaskAgent()
        self.meeting = MeetingAgent()
        self.knowledge = KnowledgeAgent()
        self.initiative = InitiativeAgent()
        self.module = ModuleAgent()

    def classify(self, text: str) -> Intent:
        low = text.lower()
        for intent, words in _KEYWORDS.items():
            if any(w in low for w in words):
                return intent
        return Intent.MODULE  # default: treat freeform structured data as insight

    def route(self, ctx: RequestContext, text: str) -> Intent:
        """Classify + audit. Routers call the chosen agent directly."""
        intent = self.classify(text)
        record(ctx, self.name, "route", {"intent": intent.value})
        return intent
