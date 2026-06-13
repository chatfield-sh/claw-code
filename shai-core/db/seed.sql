-- SHAI Core — development seed.
-- One tenant, one domain-neutral profile. IDs match .env.example so the API can
-- resolve a dev user when Clerk is absent.

INSERT INTO tenant (id, name, plan)
VALUES ('00000000-0000-0000-0000-000000000001', 'Chris (personal)', 'free')
ON CONFLICT (id) DO NOTHING;

INSERT INTO user_profile (id, tenant_id, name, role, goals, comms_style)
VALUES (
    '00000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000001',
    'Chris Hatfield',
    'founder',                       -- set to anything; agents adapt via profile
    '["protect daily unprompted opens", "validate the executive habit"]',
    'direct, warm, concise'
)
ON CONFLICT (id) DO NOTHING;

-- A couple of generic seed rows so the screens render with content. Guarded by
-- NOT EXISTS so re-running this file (e.g. the container migrate step on every
-- start) does not duplicate them.
INSERT INTO task (tenant_id, user_id, title, weight, status, source)
SELECT v.tenant_id, v.user_id, v.title, v.weight, 'open', 'seed'
FROM (VALUES
    ('00000000-0000-0000-0000-000000000001'::uuid,
     '00000000-0000-0000-0000-000000000002'::uuid,
     'Run a real day through SHAI Core', 80::numeric),
    ('00000000-0000-0000-0000-000000000001'::uuid,
     '00000000-0000-0000-0000-000000000002'::uuid,
     'Wire the generic module to real data', 60::numeric)
) AS v(tenant_id, user_id, title, weight)
WHERE NOT EXISTS (
    SELECT 1 FROM task WHERE source = 'seed' AND task.tenant_id = v.tenant_id
);
