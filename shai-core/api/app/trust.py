"""Trust gate.

Universal safety model: SHAI Core never performs an outbound/irreversible action
(send email, modify a calendar, etc.) on its own. Such actions are *staged* and
require explicit human approval. Drafting, reading, and analysis are allowed.
"""

from __future__ import annotations

from enum import Enum


class Action(str, Enum):
    READ = "read"            # always allowed
    ANALYZE = "analyze"      # always allowed
    DRAFT = "draft"          # allowed: produces a staged artifact
    SEND = "send"            # gated: requires human approval
    MUTATE_EXTERNAL = "mutate_external"  # gated: calendar/Gmail writes, etc.


_ALWAYS_ALLOWED = {Action.READ, Action.ANALYZE, Action.DRAFT}


def is_allowed(action: Action) -> bool:
    """Return True if the agent may perform the action without human approval."""
    return action in _ALWAYS_ALLOWED


def require_approval(action: Action) -> bool:
    """Return True if the action must be staged for human approval."""
    return not is_allowed(action)
