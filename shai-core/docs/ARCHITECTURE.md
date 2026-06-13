# Architecture

SHAI Core is one engine with a library of modules. The engine is domain-neutral;
every vertical is a module that plugs into a stable contract. This is what lets a
personal tool become a product without a teardown.

```
┌──────────────────────────────────────────────────────────────┐
│                    SHAI CORE  (domain-neutral)                 │
│  Brief · Tasks · Email · Meetings · Knowledge · Initiatives    │
│  Orchestrator · Memory (4 tiers) · Trust gate · Audit log      │
│  Auth (tenant-aware) · Google connectors                       │
└───────────────────────────────┬──────────────────────────────┘
                                │  Module API (parse/analyze/schema)
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
   generic insight        Hotel (later)          Real-estate (later)
```

## Stack

| Layer | Choice | Where |
| --- | --- | --- |
| Web | Next.js (App Router) | `web/` |
| API | FastAPI | `api/` |
| DB | Postgres 16 + pgvector | `db/` + docker-compose |
| Auth | Clerk (tenant-aware) | `api/app/deps.py` |
| Agents | Claude | `api/app/claude.py`, `api/app/agents/` |
| Connectors | Google (read + draft + calendar read) | TODO sprint-1/2 |

## The three seams that make Core a product

1. **The tenant seam — `api/app/deps.py`.** `get_current_user` is the ONE place
   that resolves `(tenant_id, user_id)`. Every table has `tenant_id` and every
   query filters by it. Going multi-tenant is flipping resolution here, not a
   rewrite. See [§3.2 of the spec].

2. **The Module contract — `api/app/modules/base.py`.** `parse` / `analyze` /
   `schema`. The only place a domain may live. Core ships with the generic
   module; verticals register against the same three functions. See
   [MODULE_CONTRACT.md](./MODULE_CONTRACT.md).

3. **The trust gate — `api/app/trust.py`.** Read / analyze / draft are free;
   send and external mutations are staged for human approval. The safety model
   is universal, not hospitality-specific.

## Agents

One orchestrator routes to domain-neutral specialists. Role-awareness comes from
the user's **profile** (role, goals, comms style), injected via
`claude.role_preamble` — never from hardcoded industry logic. Set the profile to
"RDO" and it behaves like the original hotel build; set it to anything else and
it adapts.

| Agent | Scope |
| --- | --- |
| Orchestrator | classify intent, retrieve memory, route, enforce trust, log |
| Brief | morning brief + EOD recap + risk scan |
| Email | triage by stake + draft (no-send) |
| Task | extract + rank by weight from any source |
| Meeting | summary + decisions + action items + follow-up draft |
| Knowledge | embed + recall over notes |
| Initiative | advice on any initiative → next-step tasks |
| Module | loads the active module; runs parse/analyze. **Domain lives only here.** |

## Data model

12 domain-neutral tables, every one carrying `tenant_id` (dormant). The two
generic module tables (`module_record`, `module_insight`) replace the three
hotel-specific ones (`property`, `metric_snapshot`, `ops_insight`). Full DDL in
[`db/schema.sql`](../db/schema.sql).

## Offline-friendly by design

With no `ANTHROPIC_API_KEY` and no database, the API still runs: agents and the
generic module fall back to deterministic heuristics. This keeps the scaffold
runnable and the test suite hermetic.
