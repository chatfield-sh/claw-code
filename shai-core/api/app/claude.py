"""Claude client wrapper.

A single chokepoint for all model calls so every agent shares the same model
config, system-prompt assembly, and offline fallback. When no API key is set,
``complete`` returns ``None`` and callers fall back to deterministic heuristics —
this keeps the scaffold runnable and the tests hermetic.
"""

from __future__ import annotations

from .config import settings
from .deps import RequestContext

try:
    import anthropic
except ImportError:  # anthropic optional until keys are wired
    anthropic = None  # type: ignore[assignment]

_client = None


def _get_client():
    global _client
    if _client is None and anthropic is not None and settings.has_claude:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def role_preamble(ctx: RequestContext) -> str:
    """Role-awareness comes from the profile, never from a hardcoded vertical."""
    goals = "; ".join(ctx.goals) if ctx.goals else "their stated priorities"
    return (
        f"You assist a {ctx.role} who values {goals}. "
        f"Write in a {ctx.comms_style} voice. "
        "Stay domain-neutral: do not assume any specific industry."
    )


def complete(
    ctx: RequestContext,
    system: str,
    user: str,
    *,
    max_tokens: int = 1024,
) -> str | None:
    """Run a single-turn completion. Returns None when Claude is unavailable."""
    client = _get_client()
    if client is None:
        return None
    msg = client.messages.create(
        model=settings.shai_model,
        max_tokens=max_tokens,
        system=f"{role_preamble(ctx)}\n\n{system}",
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in msg.content if block.type == "text")
