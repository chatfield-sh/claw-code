"""The Module contract is the architectural seam — exercise it directly.

These run offline (no Claude key) via the generic module's heuristic fallback.
"""

from __future__ import annotations

from app.deps import RequestContext
from app.modules.registry import available_modules, get_module
from app.schemas import ModuleInsight, ModuleRecord, ModuleSchema

CTX = RequestContext(tenant_id="t", user_id="u")


def test_core_ships_only_generic_module():
    assert available_modules() == ["generic"]


def test_generic_parse_columnar():
    mod = get_module("generic")
    rec = mod.parse(CTX, "metric,value\nrevenue,1200\ncost,800", label="Q2")
    assert isinstance(rec, ModuleRecord)
    assert rec.data["columns"] == ["metric", "value"]
    assert ["revenue", "1200"] in rec.data["rows"]
    assert rec.label == "Q2"


def test_generic_parse_keyvalue():
    mod = get_module("generic")
    rec = mod.parse(CTX, "occupancy: 82%\nadr: 145")
    assert rec.data["occupancy"] == "82%"
    assert rec.data["adr"] == "145"


def test_generic_analyze_heuristic_surfaces_largest_number():
    mod = get_module("generic")
    rec = mod.parse(CTX, "revenue,1200\ncost,800", label="Q2")
    insight = mod.analyze(CTX, rec)
    assert isinstance(insight, ModuleInsight)
    assert insight.impact == 1200
    assert insight.severity in {"green", "amber", "red"}


def test_generic_analyze_no_numbers_is_green():
    mod = get_module("generic")
    rec = mod.parse(CTX, "note: kickoff went well")
    insight = mod.analyze(CTX, rec)
    assert insight.severity == "green"
    assert insight.impact is None


def test_schema_shape():
    schema = get_module("generic").schema()
    assert isinstance(schema, ModuleSchema)
    assert schema.module_key == "generic"
    assert any(f.name == "label" for f in schema.fields)


def test_unknown_module_falls_back_to_generic():
    assert get_module("nonexistent").key == "generic"
