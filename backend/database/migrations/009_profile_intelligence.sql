-- ============================================================
-- Migration 009: Profile Intelligence
-- Per-subject knowledge record (the MONITORED account's own public
-- profile) plus an append-only change history, so the platform can show
-- "was X, now Y" over time — a politician who switched party, an
-- influencer who switched brand, a changed bio or verification status.
--
-- This tracks the subject being protected, NOT the people who comment.
-- ============================================================

CREATE TABLE IF NOT EXISTS target_profile_knowledge (
    target_id       UUID PRIMARY KEY REFERENCES target_accounts(id) ON DELETE CASCADE,
    display_name    TEXT,
    bio             TEXT,
    follower_count  BIGINT,
    following_count BIGINT,
    posts_count     INTEGER,
    is_verified     BOOLEAN,
    is_private      BOOLEAN,
    -- Reserved for public-figure context (public office/brand affiliations,
    -- sourced from public records). Only populated for targets explicitly
    -- marked as public figures, empty otherwise.
    public_facts    JSONB NOT NULL DEFAULT '{}',
    first_seen_at   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS target_profile_changes (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    target_id  UUID NOT NULL REFERENCES target_accounts(id) ON DELETE CASCADE,
    field      VARCHAR(64) NOT NULL,        -- display_name | bio | is_verified | is_private | <public_fact key>
    old_value  TEXT,
    new_value  TEXT,
    source     VARCHAR(32) NOT NULL DEFAULT 'crawl',   -- crawl | manual | enrichment
    changed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tpc_target_time
    ON target_profile_changes(target_id, changed_at DESC);
