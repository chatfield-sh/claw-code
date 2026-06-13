"""Agents: one orchestrator + domain-neutral specialists.

Role-awareness comes from the user's profile (injected via ``claude.role_preamble``),
never from hardcoded industry logic. The only agent that touches a domain is the
Module agent, and only through the Module contract.
"""

from .orchestrator import Orchestrator

__all__ = ["Orchestrator"]
