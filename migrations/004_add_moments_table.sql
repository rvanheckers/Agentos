-- Migration: Add moments table for user selection workflow
-- Date: 2025-10-16
-- Description: Adds moments table, phase tracking to jobs, and moment_id to clips

-- 1. Create moments table
CREATE TABLE IF NOT EXISTS moments (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    moment_index INTEGER NOT NULL,
    start_time DOUBLE PRECISION NOT NULL,
    end_time DOUBLE PRECISION NOT NULL,
    duration DOUBLE PRECISION NOT NULL,
    description TEXT,
    sentence_text TEXT,
    keywords JSON,
    viral_score INTEGER,
    is_selected BOOLEAN DEFAULT FALSE,
    selected_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_moments_job_id ON moments(job_id);
CREATE INDEX IF NOT EXISTS idx_moments_is_selected ON moments(is_selected);
CREATE INDEX IF NOT EXISTS idx_moments_created_at ON moments(created_at);
CREATE INDEX IF NOT EXISTS idx_moments_index ON moments(moment_index);

-- Add comments for documentation
COMMENT ON TABLE moments IS 'Detected viral moments before clip generation (user selection workflow)';
COMMENT ON COLUMN moments.moment_index IS 'Moment sequence number (0, 1, 2, 3, 4)';
COMMENT ON COLUMN moments.is_selected IS 'Whether user selected this moment for clip generation';
COMMENT ON COLUMN moments.viral_score IS 'AI-calculated virality score (0-100)';

-- 3. Add phase column to jobs
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS phase VARCHAR(50) DEFAULT 'phase1_analysis';
CREATE INDEX IF NOT EXISTS idx_jobs_phase ON jobs(phase);

COMMENT ON COLUMN jobs.phase IS 'Workflow phase: phase1_analysis, awaiting_selection, phase2_generation, completed, failed';

-- 4. Add moment_id to clips
ALTER TABLE clips ADD COLUMN IF NOT EXISTS moment_id UUID REFERENCES moments(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_clips_moment_id ON clips(moment_id);

COMMENT ON COLUMN clips.moment_id IS 'Link to source moment (for clips generated from user selection)';
