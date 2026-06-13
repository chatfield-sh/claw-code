"""Knowledge agent — embed notes + recall on demand (ask-your-knowledge)."""

from __future__ import annotations

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
        """Vector search over this tenant's notes.

        TODO(sprint-4): `SELECT ... ORDER BY embedding <=> %s LIMIT k` filtered by
        tenant_id. Returns [] until embeddings are wired.
        """
        self.log(ctx, "recall", {"query": query[:120], "k": k})
        return []
