-- ============================================================
-- Migration 008: discovery_schedules table
-- The DiscoverySchedule ORM model (models_discovery.py) had no
-- migration, so GET /api/v1/discovery/schedule returned 500
-- ("relation discovery_schedules does not exist").
-- ============================================================

CREATE TABLE IF NOT EXISTS discovery_schedules (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "interval"  VARCHAR(50) NOT NULL DEFAULT 'daily',   -- manual | daily | weekly | every_6h | custom
    custom_cron VARCHAR(100),
    enabled     BOOLEAN NOT NULL DEFAULT TRUE,
    options     JSONB DEFAULT '{}',
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Seed a DISABLED schedule on first creation. Without any row, the
-- scheduler's _daily_discovery_job treats "no schedule" as "run daily",
-- which would silently start auto-discovery the moment this table exists.
-- Enable it from the Discovery page when wanted. Idempotent: only inserts
-- when the table is empty, so it never overrides a saved schedule.
INSERT INTO discovery_schedules ("interval", enabled)
SELECT 'manual', FALSE
WHERE NOT EXISTS (SELECT 1 FROM discovery_schedules);
