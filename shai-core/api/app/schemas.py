"""Shared Pydantic models for request/response payloads."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


# ---- Module contract DTOs -------------------------------------------------
class ModuleRecord(BaseModel):
    """A parsed structured record (output of Module.parse)."""

    module_key: str = "generic"
    label: str | None = None
    period: date | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    raw_ref: str | None = None


class ModuleInsight(BaseModel):
    """A module's read of a record (output of Module.analyze)."""

    module_key: str = "generic"
    headline: str
    narrative: str
    impact: float | None = None
    impact_unit: str | None = None  # '$' | '%' | 'pts' | None
    action: str | None = None
    severity: str = "green"  # green | amber | red


class FieldDef(BaseModel):
    """One field in a module's schema() (UI display hint)."""

    name: str
    label: str
    kind: str = "text"  # text | number | date | currency | percent


class ModuleSchema(BaseModel):
    module_key: str
    title: str
    fields: list[FieldDef] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    """Insights screen: paste/upload any structured data."""

    module_key: str = "generic"
    label: str | None = None
    raw_input: str


class AnalyzeResponse(BaseModel):
    record: ModuleRecord
    insight: ModuleInsight


# ---- Brief / tasks --------------------------------------------------------
class BriefResponse(BaseModel):
    generated_at: datetime
    headline: str
    priorities: list[str] = Field(default_factory=list)
    calendar: list[str] = Field(default_factory=list)
    inbox_needs_you: list[str] = Field(default_factory=list)
    tasks_due: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    eod: bool = False


class Task(BaseModel):
    id: str | None = None
    title: str
    detail: str | None = None
    weight: float = 0
    status: str = "open"
    owner: str | None = None
    due: date | None = None
