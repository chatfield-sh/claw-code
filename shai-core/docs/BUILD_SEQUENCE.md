# Build Sequence (30 days)

Four sprints. Most of Core is the executive engine minus any vertical; the two
extra investments versus a hardcoded build are concentrated in **Week 1 (the
tenant seam)** and **Week 4 (the module pattern)**.

Tasks below are tagged `TODO(sprint-N)` in the code where stubs exist.

## Week 1 — Foundation + tenant seam
- **Day 1–2:** Monorepo, stack, Clerk auth, Postgres + pgvector, deploy
  hello-world. *(scaffolded: `docker-compose.yml`, `api/`, `web/`)*
- **Day 3:** 12-table schema **with `tenant_id` everywhere**; seed one tenant +
  your domain-neutral profile. *(scaffolded: `db/schema.sql`, `db/seed.sql`)*
- **Day 4:** Orchestrator + trust gate + audit log; Claude wired; tenant
  resolution in `get_current_user`. *(scaffolded: `agents/`, `trust.py`,
  `audit.py`, `deps.py`)*
- **Day 5:** Google OAuth (read + draft + calendar read); `/calendar/sync`.
  `TODO(sprint-1)`
- **Usable by Friday:** log in, see your real calendar; every query
  tenant-scoped.

## Week 2 — Email (the hook)
- **Day 6–10:** Email agent triage + draft → Gmail Drafts; Inbox screen;
  approve/edit/discard. **No send route.** *(scaffolded: `agents/email.py`,
  `routers/inbox.py`, `web/app/inbox`)* — Gmail Drafts push is `TODO(sprint-2)`.
- **Usable by Friday:** triage real mail, approve a SHAI draft, send from Gmail.

## Week 3 — Brief + tasks + loop
- **Day 11–15:** Task agent + Tasks screen; Brief builder + home screen; risk
  scan; EOD recap; nightly cron. *(scaffolded: `agents/brief.py`,
  `agents/task.py`, `routers/brief.py`, `routers/tasks.py`)* — real data wiring
  is `TODO(sprint-3)`.
- **Usable by Friday:** open SHAI to a real morning brief; daily loop closes.

## Week 4 — Module pattern + initiatives + notebook
- **Day 16–17:** Module contract + the generic module (parse/analyze/schema);
  Insights screen. *(scaffolded + tested: `modules/`, `routers/insights.py`)*
- **Day 18:** Meeting agent + note primitive + Notebook screen. *(scaffolded:
  `agents/meeting.py`, `routers/notebook.py`)*
- **Day 19:** Knowledge embed + ask-your-knowledge. `TODO(sprint-4)` (pgvector
  search in `agents/knowledge.py`).
- **Day 20:** Initiative agent + Initiatives screen; `/ask` routing.
  *(scaffolded: `agents/initiative.py`, `routers/initiatives.py`)*
- **Day 21–24:** Polish all six screens; tune the generic module on real data.
- **Day 25–30:** Daily-use shakedown. Run your real day. Fix friction only.

## The path from personal tool to product
1. Use it yourself (Days 1–30) — validate the habit on the hardest user.
2. Flip tenant isolation on (columns + scoping already exist).
3. Add billing + onboarding (Clerk + payments; signup creates tenant + profile).
4. Ship the generic product.
5. Add modules as wedges — hospitality becomes the first paid vertical module.
