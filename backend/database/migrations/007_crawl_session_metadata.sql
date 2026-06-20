-- Persist live crawl activity, system specs, and performance data per crawl session

ALTER TABLE monitoring_logs
    ADD COLUMN IF NOT EXISTS crawl_mode VARCHAR(32);

ALTER TABLE monitoring_logs
    ADD COLUMN IF NOT EXISTS session_data JSONB NOT NULL DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_logs_target_started
    ON monitoring_logs (target_id, started_at DESC);
