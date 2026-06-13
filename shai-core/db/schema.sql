-- SHAI Core — database schema
-- 12 domain-neutral tables. Every table carries tenant_id (dormant: one tenant
-- today, but every query already filters by it). Two generic module tables
-- (module_record / module_insight) replace the three hotel-specific ones.
--
-- Postgres 16 + pgvector.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "vector";     -- embeddings

-- ---------------------------------------------------------------------------
-- The multi-tenant seam (one row for now)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenant (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text NOT NULL,              -- 'Chris (personal)' for now
    plan        text NOT NULL DEFAULT 'free', -- free | pro (dormant)
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Identity + profile (drives role-awareness instead of hardcoded industry)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_profile (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid NOT NULL REFERENCES tenant(id),
    clerk_id    text UNIQUE,                -- external auth subject (nullable in dev)
    name        text NOT NULL,
    role        text,                       -- 'founder', 'RDO', 'operator', ...
    goals       jsonb NOT NULL DEFAULT '[]',
    comms_style text,                       -- voice/tone seed for drafting
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS contact (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid NOT NULL REFERENCES tenant(id),
    user_id     uuid NOT NULL REFERENCES user_profile(id),
    name        text NOT NULL,
    email       text,
    org         text,
    notes       text,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Tasks (weight = generic stake, not just $)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS task (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid NOT NULL REFERENCES tenant(id),
    user_id     uuid NOT NULL REFERENCES user_profile(id),
    title       text NOT NULL,
    detail      text,
    weight      numeric NOT NULL DEFAULT 0, -- generic importance/impact
    status      text NOT NULL DEFAULT 'open', -- open | doing | blocked | done
    owner       text,
    blocked_by  uuid REFERENCES task(id),
    contact_id  uuid REFERENCES contact(id),
    source      text,                        -- where it was captured from
    due         date,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Email (triage + draft, no-send)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS email_item (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid NOT NULL REFERENCES tenant(id),
    user_id     uuid NOT NULL REFERENCES user_profile(id),
    gmail_id    text,
    sender      text,
    subject     text,
    snippet     text,
    stake       numeric NOT NULL DEFAULT 0,  -- triage priority
    status      text NOT NULL DEFAULT 'unread', -- unread | triaged | drafted | archived
    received_at timestamptz,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS draft_reply (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid NOT NULL REFERENCES tenant(id),
    email_item_id uuid NOT NULL REFERENCES email_item(id),
    body        text NOT NULL,
    gmail_draft_id text,                     -- pushed to Gmail Drafts; user sends
    status      text NOT NULL DEFAULT 'pending', -- pending | pushed | discarded
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Calendar + meetings
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS calendar_event (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid NOT NULL REFERENCES tenant(id),
    user_id     uuid NOT NULL REFERENCES user_profile(id),
    google_id   text,
    title       text NOT NULL,
    starts_at   timestamptz,
    ends_at     timestamptz,
    location    text,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS meeting (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid NOT NULL REFERENCES tenant(id),
    user_id     uuid NOT NULL REFERENCES user_profile(id),
    title       text NOT NULL,
    raw_notes   text,                        -- pasted notes / transcript
    summary     text,
    decisions   jsonb NOT NULL DEFAULT '[]',
    follow_up   text,                        -- drafted follow-up message
    occurred_at timestamptz,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Initiatives (was 'venture') — one workspace per initiative
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS initiative (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid NOT NULL REFERENCES tenant(id),
    user_id     uuid NOT NULL REFERENCES user_profile(id),
    name        text NOT NULL,
    goal        text,
    status      text NOT NULL DEFAULT 'active', -- active | paused | done
    next_steps  jsonb NOT NULL DEFAULT '[]',
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Knowledge / notes (embedded recall)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS note (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid NOT NULL REFERENCES tenant(id),
    user_id     uuid NOT NULL REFERENCES user_profile(id),
    title       text,
    body        text NOT NULL,
    tags        text[] NOT NULL DEFAULT '{}',
    embedding   vector(1536),                -- ask-your-knowledge
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Generic module tables (replace property / metric_snapshot / ops_insight)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS module_record (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid NOT NULL REFERENCES tenant(id),
    user_id     uuid NOT NULL REFERENCES user_profile(id),
    module_key  text NOT NULL DEFAULT 'generic', -- 'generic' | 'hotel' | ...
    label       text,                        -- 'Q2 numbers', 'Unit 4', ...
    period      date,
    data        jsonb NOT NULL DEFAULT '{}', -- parsed fields, shape per module
    raw_ref     text,                        -- pointer to the upload
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS module_insight (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       uuid NOT NULL REFERENCES tenant(id),
    module_record_id uuid NOT NULL REFERENCES module_record(id),
    module_key      text NOT NULL DEFAULT 'generic',
    headline        text,
    narrative       text,
    impact          numeric,                 -- generic weight (was dollar_impact)
    impact_unit     text,                    -- '$' | '%' | 'pts' | null
    action          text,
    severity        text,                    -- green | amber | red
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Risk radar
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS risk_item (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid NOT NULL REFERENCES tenant(id),
    user_id     uuid NOT NULL REFERENCES user_profile(id),
    title       text NOT NULL,
    severity    text NOT NULL DEFAULT 'amber', -- green | amber | red
    detail      text,
    resolved    boolean NOT NULL DEFAULT false,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Memory (4 tiers, embedded)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS memory (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid NOT NULL REFERENCES tenant(id),
    user_id     uuid NOT NULL REFERENCES user_profile(id),
    tier        text NOT NULL,               -- profile | episodic | semantic | working
    content     text NOT NULL,
    embedding   vector(1536),
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Google OAuth credentials (per user; tokens for Gmail + Calendar)
-- NOTE: stored as-is for the scaffold. Encrypt at rest before production.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS google_credential (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     uuid NOT NULL REFERENCES tenant(id),
    user_id       uuid NOT NULL REFERENCES user_profile(id),
    access_token  text NOT NULL,
    refresh_token text,
    scope         text,
    expires_at    timestamptz,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, user_id)
);

-- ---------------------------------------------------------------------------
-- Audit log (every gated action)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid NOT NULL REFERENCES tenant(id),
    user_id     uuid REFERENCES user_profile(id),
    actor       text NOT NULL,               -- 'orchestrator', 'email_agent', ...
    action      text NOT NULL,
    detail      jsonb NOT NULL DEFAULT '{}',
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Tenant-scoped indexes (every hot path filters by tenant_id first)
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_task_tenant       ON task(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_email_tenant      ON email_item(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_calendar_tenant   ON calendar_event(tenant_id, starts_at);
CREATE INDEX IF NOT EXISTS idx_meeting_tenant    ON meeting(tenant_id);
CREATE INDEX IF NOT EXISTS idx_initiative_tenant ON initiative(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_note_tenant       ON note(tenant_id);
CREATE INDEX IF NOT EXISTS idx_modrec_tenant     ON module_record(tenant_id, module_key);
CREATE INDEX IF NOT EXISTS idx_modins_tenant     ON module_insight(tenant_id, module_key);
CREATE INDEX IF NOT EXISTS idx_risk_tenant       ON risk_item(tenant_id, resolved);
CREATE INDEX IF NOT EXISTS idx_memory_tenant     ON memory(tenant_id, tier);
CREATE INDEX IF NOT EXISTS idx_audit_tenant      ON audit_log(tenant_id, created_at);
