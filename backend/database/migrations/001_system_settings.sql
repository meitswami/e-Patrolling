-- Run once on Supabase SQL editor if system_settings table is missing
CREATE TABLE IF NOT EXISTS system_settings (
    key             VARCHAR(100) PRIMARY KEY,
    value           TEXT NOT NULL DEFAULT '',
    is_secret       BOOLEAN NOT NULL DEFAULT FALSE,
    updated_by      VARCHAR(36),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
