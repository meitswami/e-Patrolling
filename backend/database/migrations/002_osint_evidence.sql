-- OSINT fields on accused profiles + permalink preservation on evidence

ALTER TABLE accused_profiles ADD COLUMN IF NOT EXISTS bio TEXT;
ALTER TABLE accused_profiles ADD COLUMN IF NOT EXISTS avatar_hash VARCHAR(64);
ALTER TABLE accused_profiles ADD COLUMN IF NOT EXISTS osint_data JSONB DEFAULT '{}';
ALTER TABLE accused_profiles ADD COLUMN IF NOT EXISTS osint_updated_at TIMESTAMPTZ;

ALTER TABLE evidence_reports ADD COLUMN IF NOT EXISTS comment_url TEXT;
ALTER TABLE evidence_reports ADD COLUMN IF NOT EXISTS platform_comment_id VARCHAR(255);
ALTER TABLE evidence_reports ADD COLUMN IF NOT EXISTS post_id VARCHAR(255);
ALTER TABLE evidence_reports ADD COLUMN IF NOT EXISTS permalink_snapshot JSONB DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_accused_avatar_hash ON accused_profiles(avatar_hash) WHERE avatar_hash IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_accused_display_name_lower ON accused_profiles((lower(display_name))) WHERE display_name IS NOT NULL;
