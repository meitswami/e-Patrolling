-- ============================================================
-- Migration 006: Evidence Verification columns
-- Adds verification_status, verified_at, verified_by to evidence_reports
-- ============================================================

-- Add verification_status column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'evidence_reports' AND column_name = 'verification_status'
    ) THEN
        ALTER TABLE evidence_reports ADD COLUMN verification_status VARCHAR(20);
    END IF;
END $$;

-- Add verified_at column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'evidence_reports' AND column_name = 'verified_at'
    ) THEN
        ALTER TABLE evidence_reports ADD COLUMN verified_at TIMESTAMPTZ;
    END IF;
END $$;

-- Add verified_by column
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'evidence_reports' AND column_name = 'verified_by'
    ) THEN
        ALTER TABLE evidence_reports ADD COLUMN verified_by UUID REFERENCES users(id);
    END IF;
END $$;

-- Add index on verification_status for the unverified queue query
CREATE INDEX IF NOT EXISTS idx_evidence_verification_status ON evidence_reports(verification_status);
