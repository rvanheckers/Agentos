-- COMPLETE METADATA IMPLEMENTATION
-- Voegt ontbrekende kolommen toe voor volledige metadata support
-- Datum: 22 September 2025

-- Voeg ontbrekende kolommen toe aan jobs tabel
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS total_moments INTEGER DEFAULT 3;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS video_duration DECIMAL(10,2);

-- Performance indexes voor nieuwe kolommen
CREATE INDEX IF NOT EXISTS idx_jobs_total_moments ON jobs(total_moments) WHERE total_moments IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_jobs_video_duration ON jobs(video_duration) WHERE video_duration IS NOT NULL;

-- Update content_insights tabel om ontbrekende metadata velden toe te voegen
ALTER TABLE content_insights ADD COLUMN IF NOT EXISTS total_moments INTEGER;
ALTER TABLE content_insights ADD COLUMN IF NOT EXISTS video_duration_seconds DECIMAL(10,2);
ALTER TABLE content_insights ADD COLUMN IF NOT EXISTS processing_method VARCHAR(50);

-- Voeg index toe voor betere query performance
CREATE INDEX IF NOT EXISTS idx_insights_duration ON content_insights(video_duration_seconds) WHERE video_duration_seconds IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_insights_moments ON content_insights(total_moments) WHERE total_moments IS NOT NULL;

-- Voeg ook missing kolommen toe aan database manager model
-- (Deze worden automatisch opgepikt door SQLAlchemy)

COMMENT ON COLUMN jobs.total_moments IS 'Aantal gegenereerde video clips/momenten';
COMMENT ON COLUMN jobs.video_duration IS 'Video duur in seconden';
COMMENT ON COLUMN content_insights.total_moments IS 'Aantal clips voor marketing analytics';
COMMENT ON COLUMN content_insights.video_duration_seconds IS 'Video duur voor trend analyse';
COMMENT ON COLUMN content_insights.processing_method IS 'Gebruikte processing methode (ai_viral_analysis, fallback_no_transcript, etc)';