"""Orchestrator — classify intent, route to a specialist, enforce trust, log.

The orchestrator is domain-neutral: it knows the *jobs*, not any industry. It
retrieves relevant memory, picks the right specialist, runs it behind the trust
gate, and records the action in the audit log.
"""

from __future__ import annotations

from enum import Enum

from .. import embeddings, repo
from ..audit import record
from ..claude import complete
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

    def retrieve_memory(self, ctx: RequestContext, query: str, k: int = 5) -> list[str]:
        """Semantic recall over the user's memory tiers (for prompt enrichment)."""
        rows = repo.search_memory(ctx, embeddings.embed_text(query), k)
        return [r["content"] for r in (rows or [])]

    def answer(self, ctx: RequestContext, query: str) -> dict:
        """End-to-end /ask: classify, retrieve memory + notes, compose an answer.

        This is where memory is retrieved *into the prompt*: recalled notes and
        memories become Claude's context. Falls back to returning the recalled
        snippets when Claude is unavailable.
        """
        intent = self.route(ctx, query)
        notes = self.knowledge.recall(ctx, query)
        memory = self.retrieve_memory(ctx, query)
        context = "\n".join(
            [f"- {m}" for m in memory] + [f"- {n.get('body', '')}" for n in notes]
        )
        out = complete(
            ctx,
            system=(
                "Answer the user's question using ONLY the provided context from "
                "their notes and memory. If the context is empty or insufficient, "
                "say so plainly. Be concise."
            ),
            user=f"Question: {query}\n\nContext:\n{context or '(none)'}",
            max_tokens=500,
        )
        answer = out or (
            "Here's what I found in your notes/memory:\n" + (context or "(nothing relevant)")
        )
        return {
            "intent": intent.value,
            "answer": answer,
            "sources": {"notes": notes, "memory": memory},
        }
