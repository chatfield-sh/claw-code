# The Module Contract

> The one architectural move that matters. It's what lets Core stay
> domain-neutral while still doing the high-value insight work — and it's how
> every future vertical becomes a plug-in instead of a rebuild.

A Module is anything that implements three functions. That is the entire
extensibility model, small on purpose.

```python
class Module:
    key: str    # 'generic' | 'hotel' | 'realestate' ...
    title: str

    def parse(self, ctx, raw_input, label=None) -> ModuleRecord:
        """Turn pasted/uploaded data into stored fields (jsonb)."""

    def analyze(self, ctx, record) -> ModuleInsight:
        """headline · narrative · impact/weight · action · severity.
        (Uses Claude with the module's domain prompt.)"""

    def schema(self) -> ModuleSchema:
        """Field definitions + display hints — tells the UI how to render."""
```

Defined in [`api/app/modules/base.py`](../api/app/modules/base.py).

## What ships with Core

Exactly one module: the **generic insight module**
([`generic.py`](../api/app/modules/generic.py)). It does all three with no domain
assumptions:

- `parse` accepts CSV / TSV / markdown tables or `key: value` lines.
- `analyze` asks Claude to "summarize what changed, flag what matters, suggest an
  action" — and falls back to a deterministic heuristic offline.
- `schema` exposes label / period / data for the Insights screen.

## Adding a vertical later (without touching Core)

```python
# api/app/modules/hotel.py
from .base import Module

class HotelModule(Module):
    key = "hotel"
    title = "Hotel performance"

    def parse(self, ctx, raw_input, label=None): ...   # STR/PMS export -> fields
    def analyze(self, ctx, record): ...                # RevPAR/NOI commentary
    def schema(self): ...                              # property-aware display

# register it — this is the ONLY change Core sees:
from .registry import register_module
register_module(HotelModule())
```

The Insights screen, the Module agent, the storage tables, and every other part
of Core are unchanged. The domain is quarantined inside the module.

## Storage

- `module_record` — the parsed record (`data` jsonb, `module_key`, `label`,
  `period`, `raw_ref`).
- `module_insight` — the read (`headline`, `narrative`, `impact`, `impact_unit`,
  `action`, `severity`).

Both carry `tenant_id` and are namespaced by `module_key`, so multiple modules
coexist without collision.
