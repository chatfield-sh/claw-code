# Deploy

SHAI Core ships as two images — `api` (FastAPI) and `web` (Next.js standalone) —
plus a Postgres + pgvector database. The API container applies the schema on
startup (idempotent), so deploying is: provision a database, set secrets, ship
the two images.

## Run the full stack locally (Docker)

```bash
cd shai-core
cp .env.example .env            # optional: add keys
docker compose --profile full up --build
# web  -> http://localhost:3000
# api  -> http://localhost:8000/docs
```

The `full` profile starts `db + api + web`. Without it, `docker compose up -d db`
starts only the database (the dev workflow). The API runs `python -m app.migrate`
before serving, which applies `db/schema.sql` + `db/seed.sql`.

## Build the images individually

```bash
# API — build context is shai-core/ so the image carries db/ for migration
docker build -f api/Dockerfile -t shai-api .

# Web — NEXT_PUBLIC_API_BASE is inlined at build time
docker build -t shai-web --build-arg NEXT_PUBLIC_API_BASE=https://api.example.com ./web
```

> **Build-time caveat:** `NEXT_PUBLIC_API_BASE` is baked into the web bundle at
> build time (that's how Next inlines `NEXT_PUBLIC_*`). Build the web image with
> the API's public URL, not at runtime.

## Managed deploy (Render blueprint)

[`render.yaml`](../render.yaml) provisions Postgres + the two services in one
blueprint. Point Render at it, then set the `sync: false` secrets
(`ANTHROPIC_API_KEY`, `CLERK_SECRET_KEY`, `GOOGLE_CLIENT_ID/SECRET`) and
`NEXT_PUBLIC_API_BASE` (the `shai-api` URL) in the dashboard. `DATABASE_URL` is
wired automatically from the managed database.

The same images run anywhere that takes a container (Fly, Railway, Cloud Run,
ECS, a VM). The only hard requirements are a Postgres with `pgvector` and the
env vars in [`.env.example`](../.env.example).

## Migration behavior

`app/migrate.py` runs every statement in its own autocommit transaction and logs
+ skips failures, because the schema is idempotent (`CREATE ... IF NOT EXISTS`,
`INSERT ... ON CONFLICT DO NOTHING`). If your platform pre-manages the `vector`
extension, the `CREATE EXTENSION` line is skipped harmlessly. Run it standalone
with `python -m app.migrate`.

## Production config guard

Set `SHAI_ENV=prod`. The API then **refuses to start** if `SHAI_SECRET_KEY` is
missing/default or if Clerk is enabled (`CLERK_SECRET_KEY`) without
`CLERK_ISSUER` — failing closed rather than running insecurely. Logs are emitted
as structured JSON (one object per line; set `LOG_LEVEL`), and every response
carries an `X-Request-ID`. Recorded actions are viewable (tenant-scoped) at
`GET /audit`.

## Single-user vs. multi-tenant

The seed creates one tenant + the dev profile, which single-user mode resolves
to (see `deps.get_current_user`). With Clerk configured, real users are
provisioned from their token on first request; flip tenant isolation on when you
commercialize (see the build sequence). The nightly brief cron
([OPERATIONS.md](./OPERATIONS.md)) should run as a scheduled job against the same
database.
