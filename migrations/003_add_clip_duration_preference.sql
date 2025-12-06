-- Migration: Add clip_duration_preference column to jobs table
-- Date: 2025-09-24
-- Description: Allows users to specify preferred clip duration (30s, 45s, 60s)

-- Add the new column with default value
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS clip_duration_preference INTEGER DEFAULT 30;

-- Add comment for documentation
COMMENT ON COLUMN jobs.clip_duration_preference IS 'User preferred clip duration in seconds (30, 45, or 60)';

-- Optional: Create index if we plan to query by this frequently
-- CREATE INDEX idx_jobs_clip_duration_preference ON jobs(clip_duration_preference);