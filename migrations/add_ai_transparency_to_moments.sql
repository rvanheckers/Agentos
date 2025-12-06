-- Migration: Add AI Transparency columns to moments table
-- Purpose: Enable debug viewer to show Claude's reasoning for viral moment detection
-- Date: 2025-01-16
-- Contract: agent_contracts/job-debug-viewer/DEBUG_VIEWER_V2.md

-- Add reasoning column (Claude's explanation of why this moment is viral)
ALTER TABLE moments
ADD COLUMN IF NOT EXISTS reasoning TEXT;

-- Add engagement_drivers column (list of viral factors: emotional, surprising, quotable, etc.)
ALTER TABLE moments
ADD COLUMN IF NOT EXISTS engagement_drivers JSON DEFAULT '[]'::json;

-- Add index for faster filtering by engagement drivers
CREATE INDEX IF NOT EXISTS idx_moments_engagement_drivers ON moments USING gin (engagement_drivers);

-- Verification query
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'moments'
AND column_name IN ('reasoning', 'engagement_drivers')
ORDER BY column_name;
