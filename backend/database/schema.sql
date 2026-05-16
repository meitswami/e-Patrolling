-- ============================================================
-- PATROL — PostgreSQL Database Schema
-- ============================================================
-- Version: 1.0.0
-- Description: Complete schema for PATROL cyber intelligence platform
-- 
-- Tables:
--   users, target_accounts, crawled_comments, ai_results,
--   evidence_reports, accused_profiles, repeat_offenders,
--   monitoring_logs, region_scores, dashboard_events
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For full-text search

-- ============================================================
-- ENUM TYPES
-- ============================================================

CREATE TYPE platform_type AS ENUM (
    'instagram', 'facebook', 'twitter', 'threads', 'telegram', 'whatsapp'
);

CREATE TYPE severity_level AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');

CREATE TYPE language_type AS ENUM ('hindi', 'english', 'hinglish', 'unknown');

CREATE TYPE user_role AS ENUM ('ADMIN', 'ANALYST', 'VIEWER');

CREATE TYPE offender_status AS ENUM ('SUSPECTED', 'CONFIRMED', 'ESCALATED', 'REPORTED');

CREATE TYPE report_status AS ENUM ('PENDING', 'GENERATING', 'READY', 'FAILED');


-- ============================================================
-- USERS (Admin/Analyst accounts)
-- ============================================================

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    name            VARCHAR(255) NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    role            user_role NOT NULL DEFAULT 'ANALYST',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at   TIMESTAMP WITH TIME ZONE,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);


-- ============================================================
-- TARGET ACCOUNTS (Women influencers being monitored)
-- ============================================================

CREATE TABLE target_accounts (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username            VARCHAR(255) NOT NULL,
    display_name        VARCHAR(255),
    platform            platform_type NOT NULL,
    profile_url         TEXT NOT NULL,
    avatar_url          TEXT,
    follower_count      BIGINT,
    is_verified         BOOLEAN DEFAULT FALSE,
    
    -- Monitoring config
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    monitoring_enabled  BOOLEAN NOT NULL DEFAULT TRUE,
    crawl_interval_sec  INTEGER NOT NULL DEFAULT 300,
    last_crawled_at     TIMESTAMP WITH TIME ZONE,
    
    -- Region inference
    inferred_region     VARCHAR(255),
    region_confidence   FLOAT,
    
    -- Metadata
    added_by            UUID REFERENCES users(id),
    notes               TEXT,
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    UNIQUE(username, platform)
);

CREATE INDEX idx_target_platform ON target_accounts(platform);
CREATE INDEX idx_target_active ON target_accounts(is_active, monitoring_enabled);
CREATE INDEX idx_target_username ON target_accounts(username);


-- ============================================================
-- ACCUSED PROFILES (Unique offender profiles across platforms)
-- ============================================================

CREATE TABLE accused_profiles (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform            platform_type NOT NULL,
    username            VARCHAR(255) NOT NULL,
    display_name        VARCHAR(255),
    profile_url         TEXT NOT NULL,
    avatar_url          TEXT,
    follower_count      BIGINT,
    following_count     BIGINT,
    is_verified         BOOLEAN DEFAULT FALSE,
    account_age_days    INTEGER,
    
    -- Threat metrics (updated on each new incident)
    total_incidents     INTEGER NOT NULL DEFAULT 0,
    critical_count      INTEGER NOT NULL DEFAULT 0,
    high_count          INTEGER NOT NULL DEFAULT 0,
    avg_severity_score  FLOAT NOT NULL DEFAULT 0.0,
    max_risk_score      INTEGER NOT NULL DEFAULT 0,
    
    -- Status
    status              offender_status NOT NULL DEFAULT 'SUSPECTED',
    is_repeat_offender  BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Region
    inferred_region     VARCHAR(255),
    region_confidence   FLOAT,
    
    first_seen_at       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_seen_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    UNIQUE(username, platform)
);

CREATE INDEX idx_accused_platform ON accused_profiles(platform);
CREATE INDEX idx_accused_repeat ON accused_profiles(is_repeat_offender);
CREATE INDEX idx_accused_status ON accused_profiles(status);
CREATE INDEX idx_accused_risk ON accused_profiles(max_risk_score DESC);


-- ============================================================
-- CRAWLED COMMENTS (Raw data from social media)
-- ============================================================

CREATE TABLE crawled_comments (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_hash        VARCHAR(64) NOT NULL UNIQUE,  -- SHA256 for dedup
    
    -- Platform info
    platform            platform_type NOT NULL,
    post_url            TEXT NOT NULL,
    post_id             VARCHAR(255),
    comment_id          VARCHAR(255),
    comment_url         TEXT,
    
    -- Content
    text                TEXT NOT NULL,
    language            language_type NOT NULL DEFAULT 'unknown',
    
    -- Relations
    target_id           UUID REFERENCES target_accounts(id),
    accused_id          UUID REFERENCES accused_profiles(id),
    
    -- Raw platform data
    platform_timestamp  TIMESTAMP WITH TIME ZONE,
    raw_data            JSONB DEFAULT '{}',
    
    -- Processing status
    is_processed        BOOLEAN NOT NULL DEFAULT FALSE,
    processed_at        TIMESTAMP WITH TIME ZONE,
    
    crawled_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_comments_platform ON crawled_comments(platform);
CREATE INDEX idx_comments_target ON crawled_comments(target_id);
CREATE INDEX idx_comments_accused ON crawled_comments(accused_id);
CREATE INDEX idx_comments_processed ON crawled_comments(is_processed);
CREATE INDEX idx_comments_crawled_at ON crawled_comments(crawled_at DESC);
-- Full text search index
CREATE INDEX idx_comments_fts ON crawled_comments USING gin(to_tsvector('english', text));
-- Trigram index for partial word search
CREATE INDEX idx_comments_trgm ON crawled_comments USING gin(text gin_trgm_ops);


-- ============================================================
-- AI RESULTS (Classification output per comment)
-- ============================================================

CREATE TABLE ai_results (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    comment_id          UUID NOT NULL REFERENCES crawled_comments(id) ON DELETE CASCADE,
    
    -- Detection flags
    is_abusive          BOOLEAN NOT NULL DEFAULT FALSE,
    is_sexual_harassment BOOLEAN NOT NULL DEFAULT FALSE,
    is_rape_threat      BOOLEAN NOT NULL DEFAULT FALSE,
    is_stalking         BOOLEAN NOT NULL DEFAULT FALSE,
    is_hate_speech      BOOLEAN NOT NULL DEFAULT FALSE,
    is_threat           BOOLEAN NOT NULL DEFAULT FALSE,
    is_bullying         BOOLEAN NOT NULL DEFAULT FALSE,
    is_doxxing          BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Scores
    confidence_score    FLOAT NOT NULL DEFAULT 0.0,   -- 0.0 to 1.0
    toxicity_score      FLOAT NOT NULL DEFAULT 0.0,   -- 0.0 to 1.0
    severity_score      INTEGER NOT NULL DEFAULT 0,   -- 0 to 100
    risk_score          INTEGER NOT NULL DEFAULT 0,   -- 0 to 100 (composite)
    
    -- Classification
    severity_level      severity_level NOT NULL DEFAULT 'LOW',
    detected_language   language_type NOT NULL DEFAULT 'unknown',
    
    -- Keyword matches
    matched_keywords    TEXT[] DEFAULT '{}',
    
    -- Entities detected (NER)
    detected_entities   JSONB DEFAULT '{}',
    
    -- Model info
    model_used          VARCHAR(100),
    model_version       VARCHAR(50),
    
    processed_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_comment ON ai_results(comment_id);
CREATE INDEX idx_ai_abusive ON ai_results(is_abusive);
CREATE INDEX idx_ai_severity ON ai_results(severity_level);
CREATE INDEX idx_ai_risk_score ON ai_results(risk_score DESC);


-- ============================================================
-- EVIDENCE REPORTS (Packaged evidence for legal use)
-- ============================================================

CREATE TABLE evidence_reports (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evidence_id         VARCHAR(20) NOT NULL UNIQUE,  -- Human-readable ID: EVD-2024-001234
    
    -- Relations
    comment_id          UUID REFERENCES crawled_comments(id),
    ai_result_id        UUID REFERENCES ai_results(id),
    target_id           UUID REFERENCES target_accounts(id),
    accused_id          UUID REFERENCES accused_profiles(id),
    
    -- Platform data (snapshot at time of capture)
    platform            platform_type NOT NULL,
    post_url            TEXT,
    comment_text        TEXT NOT NULL,
    comment_timestamp   TIMESTAMP WITH TIME ZONE,
    
    -- Severity snapshot
    severity_level      severity_level NOT NULL,
    risk_score          INTEGER NOT NULL,
    
    -- Screenshot
    screenshot_path     TEXT,
    screenshot_hash     VARCHAR(64),  -- SHA256 integrity check
    
    -- Evidence metadata
    capture_timestamp   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    captured_by_user    UUID REFERENCES users(id),  -- NULL = auto-captured
    
    -- Legal metadata
    chain_of_custody    JSONB DEFAULT '{}',
    notes               TEXT,
    is_escalated        BOOLEAN NOT NULL DEFAULT FALSE,
    escalated_at        TIMESTAMP WITH TIME ZONE,
    
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_evidence_target ON evidence_reports(target_id);
CREATE INDEX idx_evidence_accused ON evidence_reports(accused_id);
CREATE INDEX idx_evidence_severity ON evidence_reports(severity_level);
CREATE INDEX idx_evidence_platform ON evidence_reports(platform);
CREATE INDEX idx_evidence_created ON evidence_reports(created_at DESC);
CREATE INDEX idx_evidence_escalated ON evidence_reports(is_escalated);


-- ============================================================
-- REPEAT OFFENDERS (Profiles with ≥3 incidents)
-- ============================================================

CREATE TABLE repeat_offenders (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    accused_id          UUID NOT NULL UNIQUE REFERENCES accused_profiles(id),
    
    -- Offense metrics
    total_offenses      INTEGER NOT NULL DEFAULT 0,
    targets_harassed    INTEGER NOT NULL DEFAULT 0,  -- Unique target count
    platforms_used      platform_type[] DEFAULT '{}',
    
    -- Severity breakdown
    critical_count      INTEGER NOT NULL DEFAULT 0,
    high_count          INTEGER NOT NULL DEFAULT 0,
    medium_count        INTEGER NOT NULL DEFAULT 0,
    low_count           INTEGER NOT NULL DEFAULT 0,
    
    -- Timeline
    first_offense_at    TIMESTAMP WITH TIME ZONE,
    last_offense_at     TIMESTAMP WITH TIME ZONE,
    
    -- Status
    status              offender_status NOT NULL DEFAULT 'CONFIRMED',
    priority_score      INTEGER NOT NULL DEFAULT 0,  -- For ranking
    
    flagged_by          UUID REFERENCES users(id),
    flagged_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_repeat_accused ON repeat_offenders(accused_id);
CREATE INDEX idx_repeat_priority ON repeat_offenders(priority_score DESC);
CREATE INDEX idx_repeat_status ON repeat_offenders(status);


-- ============================================================
-- MONITORING LOGS (Crawler audit trail)
-- ============================================================

CREATE TABLE monitoring_logs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    target_id           UUID REFERENCES target_accounts(id),
    platform            platform_type NOT NULL,
    
    -- Crawl results
    comments_found      INTEGER NOT NULL DEFAULT 0,
    comments_new        INTEGER NOT NULL DEFAULT 0,
    abusive_detected    INTEGER NOT NULL DEFAULT 0,
    critical_detected   INTEGER NOT NULL DEFAULT 0,
    
    -- Performance
    duration_seconds    FLOAT,
    pages_crawled       INTEGER DEFAULT 0,
    
    -- Status
    success             BOOLEAN NOT NULL DEFAULT TRUE,
    error_message       TEXT,
    
    started_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_logs_target ON monitoring_logs(target_id);
CREATE INDEX idx_logs_platform ON monitoring_logs(platform);
CREATE INDEX idx_logs_started ON monitoring_logs(started_at DESC);


-- ============================================================
-- REGION SCORES (Geographic intelligence)
-- ============================================================

CREATE TABLE region_scores (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    accused_id          UUID NOT NULL REFERENCES accused_profiles(id),
    
    -- Region hierarchy (India-specific)
    city                VARCHAR(255),
    district            VARCHAR(255),
    state               VARCHAR(255),
    country             VARCHAR(100) NOT NULL DEFAULT 'India',
    
    -- Coordinates
    latitude            FLOAT,
    longitude           FLOAT,
    
    -- Confidence
    confidence          FLOAT NOT NULL DEFAULT 0.0,
    detection_signals   JSONB DEFAULT '{}',  -- bio_keywords, hashtags, etc.
    
    detected_at         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_region_accused ON region_scores(accused_id);
CREATE INDEX idx_region_state ON region_scores(state);
CREATE INDEX idx_region_city ON region_scores(city);


-- ============================================================
-- DASHBOARD EVENTS (Pre-aggregated for fast dashboard)
-- ============================================================

CREATE TABLE dashboard_events (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type          VARCHAR(100) NOT NULL,
    
    -- Time bucket (for time-series aggregation)
    hour_bucket         TIMESTAMP WITH TIME ZONE NOT NULL,  -- Truncated to hour
    
    -- Dimensions
    platform            platform_type,
    severity_level      severity_level,
    region              VARCHAR(255),
    
    -- Metrics
    event_count         INTEGER NOT NULL DEFAULT 1,
    
    -- Metadata
    metadata            JSONB DEFAULT '{}',
    created_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_dash_event_type ON dashboard_events(event_type);
CREATE INDEX idx_dash_hour ON dashboard_events(hour_bucket DESC);
CREATE INDEX idx_dash_platform ON dashboard_events(platform);
CREATE INDEX idx_dash_severity ON dashboard_events(severity_level);
CREATE INDEX idx_dash_region ON dashboard_events(region);


-- ============================================================
-- GENERATED REPORTS (Export tracking)
-- ============================================================

CREATE TABLE generated_reports (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_type         VARCHAR(50) NOT NULL,  -- 'excel', 'pdf', 'json'
    status              report_status NOT NULL DEFAULT 'PENDING',
    
    -- Filters applied
    filters             JSONB DEFAULT '{}',
    
    -- File
    file_path           TEXT,
    file_size_bytes     BIGINT,
    
    requested_by        UUID REFERENCES users(id),
    requested_at        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at        TIMESTAMP WITH TIME ZONE,
    error_message       TEXT
);

CREATE INDEX idx_reports_user ON generated_reports(requested_by);
CREATE INDEX idx_reports_status ON generated_reports(status);
CREATE INDEX idx_reports_requested ON generated_reports(requested_at DESC);


-- ============================================================
-- UPDATE TRIGGERS (auto-update updated_at columns)
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_targets_updated_at BEFORE UPDATE ON target_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_accused_updated_at BEFORE UPDATE ON accused_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_repeat_updated_at BEFORE UPDATE ON repeat_offenders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ============================================================
-- SEED: Default admin user
-- Password: Patrol@2024! (bcrypt hash)
-- ============================================================
-- NOTE: This is seeded by scripts/seed_db.py, not here,
-- because we need bcrypt hashing from Python.


-- ============================================================
-- SYSTEM SETTINGS (admin panel — overrides .env at runtime)
-- ============================================================

CREATE TABLE IF NOT EXISTS system_settings (
    key             VARCHAR(100) PRIMARY KEY,
    value           TEXT NOT NULL DEFAULT '',
    is_secret       BOOLEAN NOT NULL DEFAULT FALSE,
    updated_by      VARCHAR(36),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);


-- ============================================================
-- VIEWS (for convenience)
-- ============================================================

-- Dashboard summary view
CREATE VIEW v_dashboard_summary AS
SELECT
    (SELECT COUNT(*) FROM target_accounts WHERE is_active = TRUE) AS active_targets,
    (SELECT COUNT(*) FROM evidence_reports WHERE created_at > NOW() - INTERVAL '24 hours') AS evidence_24h,
    (SELECT COUNT(*) FROM evidence_reports WHERE severity_level = 'CRITICAL') AS critical_total,
    (SELECT COUNT(*) FROM repeat_offenders WHERE status = 'CONFIRMED') AS repeat_offenders,
    (SELECT COUNT(*) FROM evidence_reports) AS total_evidence;

-- Recent high-severity evidence with joined data
CREATE VIEW v_recent_evidence AS
SELECT
    er.id,
    er.evidence_id,
    er.platform,
    er.comment_text,
    er.severity_level,
    er.risk_score,
    er.capture_timestamp,
    er.screenshot_path,
    ta.username AS target_username,
    ap.username AS accused_username,
    ap.is_verified AS accused_verified,
    ap.is_repeat_offender
FROM evidence_reports er
LEFT JOIN target_accounts ta ON er.target_id = ta.id
LEFT JOIN accused_profiles ap ON er.accused_id = ap.id
ORDER BY er.capture_timestamp DESC;