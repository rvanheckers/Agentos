-- Migration: Add job_processing_config table
-- Purpose: Store per-job configuration overrides for debug viewer re-run functionality
-- Priority: 3 (DEBUG_VIEWER_V2.md)
-- Date: 2025-10-16
-- Contract: agent_contracts/job-debug-viewer/DEBUG_VIEWER_V2.md

-- Create job_processing_config table for storing per-job configuration overrides
CREATE TABLE IF NOT EXISTS job_processing_config (
    job_id UUID PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster config lookups
CREATE INDEX IF NOT EXISTS idx_job_processing_config_job_id ON job_processing_config(job_id);

-- Index for JSONB queries (e.g., finding jobs with specific settings)
CREATE INDEX IF NOT EXISTS idx_job_processing_config_config ON job_processing_config USING gin (config);

-- Add table comment
COMMENT ON TABLE job_processing_config IS 'Per-job configuration overrides for debug viewer (development/admin only). Allows re-running pipeline steps with custom settings.';

-- Add column comments
COMMENT ON COLUMN job_processing_config.job_id IS 'Foreign key to jobs table. Deleted when job is deleted (CASCADE).';
COMMENT ON COLUMN job_processing_config.config IS 'JSONB configuration object. Example structure: {"user_preferences": {"target_len": 45, "crop_method": "face_based"}, "constraints_override": {"max_moments": 8}, "face_filters": {"enabled_faces": ["face_0", "face_2"]}}';
COMMENT ON COLUMN job_processing_config.created_at IS 'When this config was first created';
COMMENT ON COLUMN job_processing_config.updated_at IS 'When this config was last updated';

-- Example config structure:
-- {
--   "user_preferences": {
--     "target_len": 45,
--     "max_moments": 8,
--     "cluster_gap_s": 5.0,
--     "crop_method": "face_based",
--     "enable_cinematic_mode": true,
--     "face_confidence": 0.7,
--     "sample_interval": 2.0
--   },
--   "constraints_override": {
--     "max_moments": 8,
--     "cluster_gap_s": 5.0,
--     "min_conf": 0.25
--   },
--   "face_filters": {
--     "enabled_faces": ["face_0", "face_2"],
--     "primary_speaker": "face_0"
--   }
-- }

-- Verification query to check if table was created successfully
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'job_processing_config'
ORDER BY ordinal_position;
