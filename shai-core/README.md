# SHAI Core

**The Domain-Neutral Executive Operating System.**
One build. You use it now. It becomes the product later.

> No industry baked in · Pluggable modules · Multi-tenant-ready
>
> Build profile (locked): personal use today · commercial product tomorrow ·
> single-user, multi-tenant-ready.

SHAI Core is an executive second brain that is useful to any operator, founder,
or executive — with **no vertical baked into the spine**. The brief, tasks,
email, meetings, knowledge, and initiatives are all domain-neutral. Anything
industry-specific lives in exactly one place: a pluggable **Module** (Job 7).

This directory is a standalone monorepo. It is checked into the `claw-code`
repository for convenience, but it has no dependency on the surrounding Rust
workspace and can be lifted into its own repository as-is.

## What this is — and isn't

| SHAI Core IS | SHAI Core IS NOT |
| --- | --- |
| A domain-neutral executive second brain | A hotel system with the hotel parts hidden |
| Useful to any operator, founder, or executive | Tied to RevPAR, NOI, STR, or any vertical metric |
| Single-user now, multi-tenant-ready by design | Multi-tenant today (deferred, not designed out) |
| The clean engine modules plug back into | A second, competing codebase |

## Architecture at a glance

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

Core ships with the **generic insight module** only. Verticals are added later
*without touching Core*.

- **Stack:** Next.js (web) · FastAPI (api) · Postgres + pgvector · Clerk (auth)
  · Claude (agents) · Google (connectors).
- **The seam that matters:** the [Module contract](./docs/MODULE_CONTRACT.md) —
  `parse` / `analyze` / `schema`.
- **The cheap insurance:** `tenant_id` on every table from day one (dormant).

See [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) for the full picture and
[`docs/BUILD_SEQUENCE.md`](./docs/BUILD_SEQUENCE.md) for the 30-day plan.

## Repository layout

```
shai-core/
├── api/            FastAPI backend — agents, modules, the tenant seam
├── web/            Next.js frontend — the six screens
├── db/             schema.sql (12 tables, tenant_id everywhere) + seed.sql
└── docs/           architecture, module contract, build sequence
```

## Quick start

Bring up Postgres + pgvector and the API:

```bash
cd shai-core
cp .env.example .env            # fill in keys (works without them in dev)
docker compose up -d db         # Postgres 16 + pgvector
make db-init                    # apply db/schema.sql + db/seed.sql

cd api
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload   # http://localhost:8000/docs
```

The web app:

```bash
cd shai-core/web
npm install
npm run dev                     # http://localhost:3000
```

> The API runs **offline-friendly**: with no `ANTHROPIC_API_KEY` set, the
> generic module and agents fall back to a deterministic heuristic so the
> scaffold is runnable and testable without external services.

## Tests

```bash
cd shai-core/api
pip install -r requirements.txt
pytest                          # module contract + smoke tests
```

## Status

The structural seams are real and wired:

- **Persistence** — tenant-scoped CRUD in `api/app/repo.py`; brief/tasks/notebook/
  initiatives/insights read and write real rows (and degrade to empty offline).
- **Auth** — Clerk JWT verification in `api/app/auth.py` + the tenant seam in
  `deps.py` (dev-identity fallback when Clerk is unset).
- **Google connectors** — OAuth + Gmail (read + compose-only drafts) + Calendar
  read in `api/app/google.py` and `routers/google.py`. No send scope, ever.

Set `ANTHROPIC_API_KEY`, `CLERK_SECRET_KEY`, and `GOOGLE_CLIENT_ID/SECRET` to
light these up; without them the app still boots and the suite stays hermetic.
Remaining work (embeddings, token refresh, cron, deploy) is tagged
`TODO(sprint-N)` against [the build sequence](./docs/BUILD_SEQUENCE.md).
