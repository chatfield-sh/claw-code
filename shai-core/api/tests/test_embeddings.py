"""Embeddings fallback: right shape, deterministic, semantically ordered."""

from __future__ import annotations

from app import embeddings


def _cos(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def test_embedding_dimension():
    assert len(embeddings.embed_text("hello world")) == embeddings.EMBED_DIM


def test_embedding_is_deterministic():
    assert embeddings.embed_text("alpha beta") == embeddings.embed_text("alpha beta")


def test_similar_text_is_closer_than_unrelated():
    base = embeddings.embed_text("quarterly revenue report")
    near = embeddings.embed_text("quarterly revenue numbers")
    far = embeddings.embed_text("cat dog elephant")
    assert _cos(base, near) > _cos(base, far)


def test_pgvector_literal_format():
    assert embeddings.to_pgvector([0.1, 0.2]) == "[0.1,0.2]"
