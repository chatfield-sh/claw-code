"""Knowledge agent — embed notes + recall on demand (ask-your-knowledge).

Notes are embedded on write and recalled with pgvector cosine search (falling
back to text search when no DB is available). Writing a note also lays down a
semantic memory, so the memory tier accumulates from real activity.
"""

from __future__ import annotations

from .. import embeddings, repo
from ..deps import RequestContext
from .base import Agent


class KnowledgeAgent(Agent):
    name = "knowledge_agent"

    def embed(self, ctx: RequestContext, text: str) -> list[float]:
        """Return an embedding for storage in note/memory."""
        self.log(ctx, "embed", {"chars": len(text)})
        return embeddings.embed_text(text)

    def add_note(self, ctx: RequestContext, body: str, title: str | None = None,
                 tags: list[str] | None = None) -> dict | None:
        """Embed + store a note, and lay down a semantic memory of it."""
        vector = embeddings.embed_text((title or "") + "\n" + body)
        note = repo.create_note(ctx, body, title=title, tags=tags, embedding=vector)
        repo.add_memory(ctx, "semantic", (title + ": " if title else "") + body, embedding=vector)
        return note

    def recall(self, ctx: RequestContext, query: str, k: int = 5) -> list[dict]:
        """Semantic recall over notes, with a text-search fallback."""
        self.log(ctx, "recall", {"query": query[:120], "k": k})
        vector = embeddings.embed_text(query)
        rows = repo.search_notes_vector(ctx, vector, k)
        if rows is None:  # DB unavailable
            rows = repo.search_notes(ctx, query, k)
        return [dict(r) for r in (rows or [])]
