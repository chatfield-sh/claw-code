"""Module registry. Core ships with the generic module; verticals register here.

Adding a vertical later (hotel, real-estate, ...) is a single
``register_module(HotelModule())`` call — Core code never changes.
"""

from __future__ import annotations

from .base import Module
from .generic import GenericModule

_REGISTRY: dict[str, Module] = {}


def register_module(module: Module) -> None:
    _REGISTRY[module.key] = module


def get_module(key: str = "generic") -> Module:
    """Return the active module, defaulting to the generic insight module."""
    return _REGISTRY.get(key) or _REGISTRY["generic"]


def available_modules() -> list[str]:
    return sorted(_REGISTRY)


# Core ships with exactly one module.
register_module(GenericModule())
