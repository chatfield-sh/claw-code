# Operations

## The daily loop (nightly cron)

`app/jobs.py` generates a brief for every active user and persists it as a
`brief_snapshot`, so the Brief screen opens to something generated *for* you
rather than computed only on demand. It fans out per `user_profile`, so it is
tenant-aware from day one.

```bash
# one-off
cd shai-core/api && . .venv/bin/activate
python -m app.jobs morning   # morning brief
python -m app.jobs eod       # end-of-day recap
```

Schedule it with cron (server local time):

```cron
# 06:30 morning brief, 18:30 EOD recap
30 6  * * *  cd /srv/shai/api && . .venv/bin/activate && python -m app.jobs morning
30 18 * * *  cd /srv/shai/api && . .venv/bin/activate && python -m app.jobs eod
```

Fetch the latest generated brief over HTTP:

```
GET /brief/latest          # most recent snapshot
GET /brief/latest?eod=true # most recent EOD recap
```

`GET /brief` still builds one on demand. When the DB is unavailable the cron
falls back to the dev identity and the snapshot write is skipped; the brief is
still generated.

## Intelligence

The Brief headline and task extraction are Claude-driven when `ANTHROPIC_API_KEY`
is set, with deterministic fallbacks otherwise (which is what the headlines above
show in a keyless run). Set the key to upgrade the prose without any code change.

## Database lifecycle

```bash
make db-up      # start Postgres + pgvector (docker compose)
make db-init    # apply schema.sql + seed.sql
make db-reset   # drop + recreate, then seed
```

`CREATE EXTENSION vector` requires a superuser (the pgvector image's default user
qualifies; most managed Postgres allowlist `vector`). Encrypt `google_credential`
tokens at rest before production.
