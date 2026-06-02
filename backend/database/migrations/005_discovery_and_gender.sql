-- ============================================================
-- Migration 005: Auto-Discovery & Gender field
-- Adds gender to target_accounts and discovered_targets table
-- ============================================================

-- Add gender field to target_accounts
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'target_accounts' AND column_name = 'gender'
    ) THEN
        ALTER TABLE target_accounts ADD COLUMN gender VARCHAR(20) DEFAULT 'unknown';
    END IF;
END $$;

-- Add bio field to target_accounts (for region inference from bio)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'target_accounts' AND column_name = 'bio'
    ) THEN
        ALTER TABLE target_accounts ADD COLUMN bio TEXT;
    END IF;
END $$;

-- ============================================================
-- DISCOVERED_TARGETS — auto-discovered accounts from platforms
-- Female, Blue-tick, 10K+ followers — daily auto-crawl result
-- ============================================================

CREATE TABLE IF NOT EXISTS discovered_targets (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Profile data
    platform            platform_type NOT NULL,
    username            VARCHAR(255) NOT NULL,
    display_name        VARCHAR(255),
    profile_url         TEXT NOT NULL,
    avatar_url          TEXT,
    bio                 TEXT,

    -- Discovery criteria match
    follower_count      BIGINT NOT NULL DEFAULT 0,
    is_verified         BOOLEAN NOT NULL DEFAULT FALSE,
    gender              VARCHAR(20) NOT NULL DEFAULT 'female',

    -- Region inferred from bio/profile
    inferred_region     VARCHAR(255),
    region_confidence   FLOAT,
    region_raw          TEXT,           -- raw text used for region inference

    -- Discovery metadata
    discovered_on       DATE NOT NULL DEFAULT CURRENT_DATE,
    discovery_run_id    UUID,           -- groups targets found in same run
    discovery_criteria  JSONB DEFAULT '{}',  -- snapshot of criteria used

    -- Conversion to monitored target
    converted_to_target_id UUID REFERENCES target_accounts(id) ON DELETE SET NULL,
    converted_at        TIMESTAMP WITH TIME ZONE,
    is_converted        BOOLEAN NOT NULL DEFAULT FALSE,
    is_dismissed        BOOLEAN NOT NULL DEFAULT FALSE,
    dismissed_reason    TEXT,

    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

    UNIQUE(username, platform, discovered_on)
);

CREATE INDEX IF NOT EXISTS idx_discovered_platform   ON discovered_targets(platform);
CREATE INDEX IF NOT EXISTS idx_discovered_date        ON discovered_targets(discovered_on DESC);
CREATE INDEX IF NOT EXISTS idx_discovered_region      ON discovered_targets(inferred_region);
CREATE INDEX IF NOT EXISTS idx_discovered_converted   ON discovered_targets(is_converted);
CREATE INDEX IF NOT EXISTS idx_discovered_run         ON discovered_targets(discovery_run_id);
CREATE INDEX IF NOT EXISTS idx_discovered_followers   ON discovered_targets(follower_count DESC);

-- ============================================================
-- DISCOVERY_RUNS — audit trail for each daily discovery run
-- ============================================================

CREATE TABLE IF NOT EXISTS discovery_runs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_date        DATE NOT NULL DEFAULT CURRENT_DATE,
    platforms       TEXT[] DEFAULT '{}',
    total_found     INTEGER NOT NULL DEFAULT 0,
    total_converted INTEGER NOT NULL DEFAULT 0,
    status          VARCHAR(50) NOT NULL DEFAULT 'pending',   -- pending | running | completed | failed
    error_message   TEXT,
    criteria        JSONB DEFAULT '{}',
    started_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMP WITH TIME ZONE,
    triggered_by    VARCHAR(50) DEFAULT 'scheduler'           -- scheduler | manual
);

CREATE INDEX IF NOT EXISTS idx_discovery_runs_date ON discovery_runs(run_date DESC);
