"""
Add pipeline_config and update phase enum for proactive pipeline architecture

Revision ID: add_pipeline_config
Created: 2025-10-17
Context7 Validated: Database migration best practices (trust score 8.7+)

This migration adds:
1. pipeline_config JSONB column to jobs table - flexible configuration storage
2. GIN index on pipeline_config for fast JSON queries
3. Updates phase default value from 'phase1_analysis' to 'configuring'
4. Migrates existing jobs to new phase naming (backwards compatibility)
"""

import sys
import os
from datetime import datetime, timezone

# Add parent directory to path to import database_manager
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from core.database_manager import PostgreSQLManager
import logging

logger = logging.getLogger(__name__)


def upgrade():
    """Add pipeline_config JSONB column and update phase enum"""

    db = PostgreSQLManager()

    try:
        with db.engine.connect() as conn:
            # Start transaction
            trans = conn.begin()

            try:
                logger.info("🔄 Starting migration: add_pipeline_config")

                # 1. Add pipeline_config JSONB column
                logger.info("Adding pipeline_config column to jobs table...")
                conn.execute(text("""
                    ALTER TABLE jobs
                    ADD COLUMN IF NOT EXISTS pipeline_config JSONB DEFAULT '{}'::jsonb
                """))

                # 2. Create GIN index for fast JSON queries
                logger.info("Creating GIN index on pipeline_config...")
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_jobs_pipeline_config
                    ON jobs USING gin(pipeline_config)
                """))

                # 3. Add comment for documentation
                logger.info("Adding column comment...")
                conn.execute(text("""
                    COMMENT ON COLUMN jobs.pipeline_config IS
                    'Proactive pipeline configuration and results (phase1, phase2, auto_flow, phase1_results)'
                """))

                # 4. Update phase default value for NEW jobs
                logger.info("Updating phase column default value...")
                conn.execute(text("""
                    ALTER TABLE jobs
                    ALTER COLUMN phase SET DEFAULT 'configuring'
                """))

                # 5. Migrate existing jobs to new phase naming (backwards compatibility)
                logger.info("Migrating existing jobs to new phase names...")

                # Map old phase names to new ones
                conn.execute(text("""
                    UPDATE jobs
                    SET phase = CASE phase
                        WHEN 'phase1_analysis' THEN 'phase1_running'
                        WHEN 'awaiting_selection' THEN 'awaiting_user_selection'
                        WHEN 'phase2_generation' THEN 'phase2_running'
                        ELSE phase  -- Keep 'completed', 'failed' as-is
                    END
                    WHERE phase IN ('phase1_analysis', 'awaiting_selection', 'phase2_generation')
                """))

                # Get count of migrated jobs
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM jobs
                    WHERE phase IN ('phase1_running', 'awaiting_user_selection', 'phase2_running')
                """))
                migrated_count = result.scalar()

                logger.info(f"   Migrated {migrated_count} jobs to new phase naming")

                # Commit transaction
                trans.commit()
                logger.info("✅ Migration completed successfully!")
                logger.info("""
                    ✅ Changes applied:
                    - Added pipeline_config JSONB column with GIN index
                    - Updated phase default to 'configuring' for new jobs
                    - Migrated {count} existing jobs to new phase names
                    - Backwards compatibility maintained
                """.format(count=migrated_count))

            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Migration failed, rolling back: {e}")
                raise

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        db.close()


def downgrade():
    """Rollback changes"""

    db = PostgreSQLManager()

    try:
        with db.engine.connect() as conn:
            # Start transaction
            trans = conn.begin()

            try:
                logger.info("🔄 Starting rollback: add_pipeline_config")

                # 1. Revert phase names to old values
                logger.info("Reverting phase names to old values...")
                conn.execute(text("""
                    UPDATE jobs
                    SET phase = CASE phase
                        WHEN 'phase1_running' THEN 'phase1_analysis'
                        WHEN 'awaiting_user_selection' THEN 'awaiting_selection'
                        WHEN 'phase2_running' THEN 'phase2_generation'
                        WHEN 'configuring' THEN 'phase1_analysis'  -- Map new state to old default
                        ELSE phase
                    END
                    WHERE phase IN ('phase1_running', 'awaiting_user_selection', 'phase2_running', 'configuring')
                """))

                # 2. Revert phase default
                logger.info("Reverting phase column default value...")
                conn.execute(text("""
                    ALTER TABLE jobs
                    ALTER COLUMN phase SET DEFAULT 'phase1_analysis'
                """))

                # 3. Drop GIN index
                logger.info("Dropping GIN index on pipeline_config...")
                conn.execute(text("DROP INDEX IF EXISTS idx_jobs_pipeline_config"))

                # 4. Drop pipeline_config column
                logger.info("Dropping pipeline_config column...")
                conn.execute(text("ALTER TABLE jobs DROP COLUMN IF EXISTS pipeline_config"))

                # Commit transaction
                trans.commit()
                logger.info("✅ Rollback completed successfully!")

            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Rollback failed, rolling back: {e}")
                raise

    except Exception as e:
        logger.error(f"❌ Rollback failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description='Database migration: add pipeline_config')
    parser.add_argument('action', choices=['upgrade', 'downgrade'],
                       help='Migration action to perform')

    args = parser.parse_args()

    if args.action == 'upgrade':
        upgrade()
    elif args.action == 'downgrade':
        downgrade()
