"""The Module contract — the one architectural seam that makes Core sellable.

A Module is anything that implements three functions. That is the entire
extensibility model, small on purpose:

    parse(raw_input)  -> ModuleRecord   turn pasted/uploaded data into fields
    analyze(record)   -> ModuleInsight  headline/narrative/impact/action/severity
    schema()          -> ModuleSchema   tell the UI how to render this data

The generic module shipped with Core implements all three with no domain
assumptions. A vertical (hotel, real-estate, ...) is a new Module registered
against the same contract — Core never changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..deps import RequestContext
from ..schemas import ModuleInsight, ModuleRecord, ModuleSchema


class Module(ABC):
    """Base class every module implements. ``key`` namespaces stored rows."""

    key: str = "generic"
    title: str = "Generic insight"

    @abstractmethod
    def parse(self, ctx: RequestContext, raw_input: str, label: str | None = None) -> ModuleRecord:
        """Turn raw pasted/uploaded data into a structured record."""

    @abstractmethod
    def analyze(self, ctx: RequestContext, record: ModuleRecord) -> ModuleInsight:
        """Return the module's read: what changed, what matters, what to do."""

    @abstractmethod
    def schema(self) -> ModuleSchema:
        """Field definitions + display hints for the UI."""
