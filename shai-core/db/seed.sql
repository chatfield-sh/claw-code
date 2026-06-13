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

-- A couple of generic seed rows so the screens render with content.
INSERT INTO task (tenant_id, user_id, title, weight, status, source)
VALUES
    ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002',
     'Run a real day through SHAI Core', 80, 'open', 'seed'),
    ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002',
     'Wire the generic module to real data', 60, 'open', 'seed')
ON CONFLICT DO NOTHING;
