-- PRIVACY-COMPLIANT METADATA MIGRATION
-- Removes PII, adds metadata structure, implements auto-cleanup

-- Add metadata columns
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS content_type VARCHAR(20) DEFAULT 'spoken';
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS analysis_mode VARCHAR(50) DEFAULT 'ai_viral_analysis';
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS viral_score INTEGER;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS youtube_title TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS keywords TEXT[];

-- Privacy & compliance columns
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS session_hash VARCHAR(64);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS content_fingerprint VARCHAR(64);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '7 days';
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS storage_tier VARCHAR(20) DEFAULT 'temporary';
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE;

-- Remove PII columns if they exist
ALTER TABLE jobs DROP COLUMN IF EXISTS youtube_uploader CASCADE;
ALTER TABLE jobs DROP COLUMN IF EXISTS youtube_description CASCADE;
ALTER TABLE jobs DROP COLUMN IF EXISTS transcript_text CASCADE;

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_jobs_content_analysis ON jobs(content_type, analysis_mode);
CREATE INDEX IF NOT EXISTS idx_jobs_viral_score ON jobs(viral_score DESC) WHERE viral_score IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_jobs_expires_at ON jobs(expires_at) WHERE is_deleted = FALSE;
CREATE INDEX IF NOT EXISTS idx_jobs_session_hash ON jobs(session_hash);
CREATE INDEX IF NOT EXISTS idx_jobs_fingerprint ON jobs(content_fingerprint);

-- Anonymous marketing insights table
CREATE TABLE IF NOT EXISTS content_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_fingerprint VARCHAR(64) NOT NULL,
    processed_date DATE DEFAULT CURRENT_DATE,
    content_category VARCHAR(50),
    viral_score INTEGER,
    engagement_score DECIMAL(3,2),
    optimal_clip_timestamps JSONB,
    detected_trends TEXT[],
    audience_segment VARCHAR(50),
    platform_performance JSONB,
    region VARCHAR(2),
    device_category VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_insights_fingerprint ON content_insights(content_fingerprint);
CREATE INDEX IF NOT EXISTS idx_insights_category ON content_insights(content_category);
CREATE INDEX IF NOT EXISTS idx_insights_date ON content_insights(processed_date);

-- Add metadata to processing_steps
ALTER TABLE processing_steps ADD COLUMN IF NOT EXISTS transcript_segments JSONB;
ALTER TABLE processing_steps ADD COLUMN IF NOT EXISTS viral_moments JSONB;

-- Auto-cleanup function
CREATE OR REPLACE FUNCTION auto_mark_expired_jobs()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE jobs SET is_deleted = TRUE
    WHERE expires_at < NOW() AND is_deleted = FALSE;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for auto-cleanup (runs on any job insert)
DROP TRIGGER IF EXISTS trigger_auto_cleanup ON jobs;
CREATE TRIGGER trigger_auto_cleanup
AFTER INSERT ON jobs
FOR EACH STATEMENT
EXECUTE FUNCTION auto_mark_expired_jobs();