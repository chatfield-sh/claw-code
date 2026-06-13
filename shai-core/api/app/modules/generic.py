"""The generic insight module — ships with Core, assumes no industry.

`parse` accepts any delimited table (CSV / TSV / markdown-ish) or key:value
lines and stores them as fields. `analyze` asks Claude to summarize what
changed, flag what matters, and suggest one action — and falls back to a
deterministic heuristic when Claude is unavailable so the scaffold is runnable
and testable offline.
"""

from __future__ import annotations

import json
import re

from ..claude import complete
from ..deps import RequestContext
from ..schemas import FieldDef, ModuleInsight, ModuleRecord, ModuleSchema
from .base import Module

_NUMBER = re.compile(r"-?\d[\d,]*\.?\d*")
_TABLE_DELIMS = ("\t", "|", ",")


def _split_table_row(line: str) -> list[str]:
    if "\t" in line:
        return [c.strip() for c in line.split("\t")]
    if "|" in line:
        return [c.strip() for c in line.strip("|").split("|")]
    return [c.strip() for c in line.split(",")]


class GenericModule(Module):
    key = "generic"
    title = "Generic insight"

    def parse(self, ctx: RequestContext, raw_input: str, label: str | None = None) -> ModuleRecord:
        lines = [ln for ln in raw_input.splitlines() if ln.strip()]
        data: dict[str, object] = {}

        # A table needs an explicit column delimiter (tab/pipe/comma) on most
        # lines; otherwise `key: value` lines must not be mistaken for a 2-col
        # table. Tables take precedence so a CSV with colons still parses right.
        is_table = sum(any(d in ln for d in _TABLE_DELIMS) for ln in lines) >= max(2, len(lines) - 1)

        if is_table and len(lines) >= 2:
            rows = [_split_table_row(ln) for ln in lines]
            data["columns"] = rows[0]
            data["rows"] = rows[1:]
        else:
            for ln in lines:
                if ":" in ln:
                    k, _, v = ln.partition(":")
                    data[k.strip()] = v.strip()
        return ModuleRecord(module_key=self.key, label=label, data=data)

    def analyze(self, ctx: RequestContext, record: ModuleRecord) -> ModuleInsight:
        rendered = json.dumps(record.data, default=str)[:4000]
        out = complete(
            ctx,
            system=(
                "You read a table of structured data and return a tight executive "
                "read. Respond ONLY as compact JSON with keys: headline, narrative, "
                "impact (number or null), impact_unit ('$','%','pts', or null), "
                "action, severity ('green'|'amber'|'red'). No industry assumptions."
            ),
            user=f"Label: {record.label or 'untitled'}\nData: {rendered}",
            max_tokens=600,
        )
        if out:
            try:
                payload = json.loads(out[out.index("{"): out.rindex("}") + 1])
                return ModuleInsight(module_key=self.key, **payload)
            except (ValueError, TypeError):
                pass  # fall through to heuristic
        return self._heuristic(record)

    def _heuristic(self, record: ModuleRecord) -> ModuleInsight:
        """Deterministic offline read: surface the largest number present."""
        blob = json.dumps(record.data, default=str)
        nums = [float(n.replace(",", "")) for n in _NUMBER.findall(blob)]
        biggest = max(nums, default=None)
        label = record.label or "this data"
        if biggest is None:
            return ModuleInsight(
                module_key=self.key,
                headline=f"Captured {label}",
                narrative="No numeric signal detected; stored as reference.",
                severity="green",
            )
        return ModuleInsight(
            module_key=self.key,
            headline=f"{label}: largest figure is {biggest:,.0f}",
            narrative=(
                f"Parsed {len(nums)} numeric values. The standout figure is "
                f"{biggest:,.0f}. (Heuristic read — set ANTHROPIC_API_KEY for the "
                "full analysis.)"
            ),
            impact=biggest,
            impact_unit=None,
            action="Review the standout figure and confirm whether it needs action.",
            severity="amber" if biggest else "green",
        )

    def schema(self) -> ModuleSchema:
        return ModuleSchema(
            module_key=self.key,
            title=self.title,
            fields=[
                FieldDef(name="label", label="Label", kind="text"),
                FieldDef(name="period", label="Period", kind="date"),
                FieldDef(name="data", label="Parsed data", kind="text"),
            ],
        )
