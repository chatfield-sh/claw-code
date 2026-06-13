"""Knowledge agent — embed notes + recall on demand (ask-your-knowledge)."""

from __future__ import annotations

from .. import repo
from ..deps import RequestContext
from .base import Agent


class KnowledgeAgent(Agent):
    name = "knowledge_agent"

    def embed(self, ctx: RequestContext, text: str) -> list[float] | None:
        """Return an embedding for storage in note.embedding / memory.embedding.

        TODO(sprint-4): call the embeddings provider. Returns None in the scaffold
        so callers store the note text and defer vectorization.
        """
        self.log(ctx, "embed_note", {"chars": len(text)})
        return None

    def recall(self, ctx: RequestContext, query: str, k: int = 5) -> list[dict]:
        """Recall over this tenant's notes.

        Today: tenant-scoped text search (`repo.search_notes`), which is genuinely
        useful without embeddings. TODO(sprint-4): swap for vector search
        (`ORDER BY embedding <=> %s`) once `embed` populates note.embedding.
        """
        self.log(ctx, "recall", {"query": query[:120], "k": k})
        rows = repo.search_notes(ctx, query, k)
        return [dict(r) for r in (rows or [])]
