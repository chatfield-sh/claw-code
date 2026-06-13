"""Embeddings — pluggable provider with a deterministic local fallback.

Claude has no embeddings API, so this calls an OpenAI-compatible endpoint when
``EMBED_API_KEY`` is set, and otherwise produces a deterministic hashed
bag-of-words vector. The fallback is not semantically rich, but it makes the
pgvector recall path fully functional offline and keeps tests hermetic. Both
paths emit ``EMBED_DIM`` (1536) floats to match the schema's vector(1536).
"""

from __future__ import annotations

import hashlib
import logging
import math
import re

import httpx

from .config import settings

log = logging.getLogger("shai.embeddings")

EMBED_DIM = 1536
_TOKEN = re.compile(r"[a-z0-9]+")


def _fallback(text: str) -> list[float]:
    vec = [0.0] * EMBED_DIM
    for tok in _TOKEN.findall(text.lower()):
        idx = int(hashlib.md5(tok.encode()).hexdigest(), 16) % EMBED_DIM
        vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _remote(text: str) -> list[float]:
    resp = httpx.post(
        f"{settings.embed_api_base}/embeddings",
        headers={"Authorization": f"Bearer {settings.embed_api_key}"},
        json={"model": settings.embed_model, "input": text},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def embed_text(text: str) -> list[float]:
    """Return an embedding for the text. Never raises; falls back locally."""
    if settings.embed_api_key:
        try:
            return _remote(text)
        except Exception as exc:  # noqa: BLE001 - degrade to local fallback
            log.warning("embeddings provider failed, using fallback: %s", exc)
    return _fallback(text)


def to_pgvector(embedding: list[float]) -> str:
    """Format an embedding as a pgvector literal: '[0.1,0.2,...]'."""
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"
