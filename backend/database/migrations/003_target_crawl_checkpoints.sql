-- Per-target crawl progress: posts + comment IDs for resume and incremental crawls

CREATE TABLE IF NOT EXISTS target_crawl_checkpoints (
    target_id UUID PRIMARY KEY REFERENCES target_accounts(id) ON DELETE CASCADE,
    platform platform_type NOT NULL,
    profile_username VARCHAR(255) NOT NULL,
    state JSONB NOT NULL DEFAULT '{}',
    posts_completed INTEGER NOT NULL DEFAULT 0,
    comments_indexed INTEGER NOT NULL DEFAULT 0,
    last_crawl_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_target_crawl_checkpoints_username
    ON target_crawl_checkpoints (profile_username);

ALTER TABLE monitoring_logs
    ADD COLUMN IF NOT EXISTS crawl_progress JSONB NOT NULL DEFAULT '{}';
