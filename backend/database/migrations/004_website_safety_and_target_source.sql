-- Website safety intake (public form) vs admin-created targets

DO $$ BEGIN
    CREATE TYPE target_source AS ENUM ('admin_panel', 'website_intake');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE website_request_status AS ENUM ('pending', 'reviewed', 'converted', 'dismissed');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

ALTER TABLE target_accounts
    ADD COLUMN IF NOT EXISTS source target_source NOT NULL DEFAULT 'admin_panel';

ALTER TABLE target_accounts
    ADD COLUMN IF NOT EXISTS website_request_id UUID;

CREATE TABLE IF NOT EXISTS website_safety_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_name VARCHAR(255),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    profile_entries JSONB NOT NULL DEFAULT '[]',
    state VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    message TEXT,
    status website_request_status NOT NULL DEFAULT 'pending',
    admin_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_website_safety_requests_status ON website_safety_requests(status);
CREATE INDEX IF NOT EXISTS idx_website_safety_requests_created ON website_safety_requests(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_target_accounts_source ON target_accounts(source);
