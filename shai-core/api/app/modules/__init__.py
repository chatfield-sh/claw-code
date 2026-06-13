"""Pluggable modules. Everything domain-specific lives here — and nowhere else."""

from .base import Module
from .registry import get_module, register_module

__all__ = ["Module", "get_module", "register_module"]
