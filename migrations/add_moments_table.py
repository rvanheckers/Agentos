"""
Add moments table for user selection workflow

Revision ID: add_moments_table
Created: 2025-10-16

This migration adds:
1. moments table - stores detected viral moments before clip generation
2. phase column to jobs table - tracks workflow phase
3. moment_id column to clips table - links clips to their source moment
"""

import sys
import os
from datetime import datetime, timezone
import uuid

# Add parent directory to path to import database_manager
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from core.database_manager import PostgreSQLManager
import logging

logger = logging.getLogger(__name__)


def upgrade():
    """Add moments table and update jobs/clips tables"""

    db = PostgreSQLManager()

    try:
        with db.engine.connect() as conn:
            # Start transaction
            trans = conn.begin()

            try:
                logger.info("🔄 Starting migration: add_moments_table")

                # 1. Create moments table
                logger.info("Creating moments table...")
                conn.execute(text("""
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
                    )
                """))

                # 2. Add indexes for performance
                logger.info("Creating indexes on moments table...")
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_moments_job_id ON moments(job_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_moments_is_selected ON moments(is_selected)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_moments_created_at ON moments(created_at)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_moments_index ON moments(moment_index)"))

                # 3. Add phase column to jobs
                logger.info("Adding phase column to jobs table...")
                conn.execute(text("""
                    ALTER TABLE jobs
                    ADD COLUMN IF NOT EXISTS phase VARCHAR(50) DEFAULT 'phase1_analysis'
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_jobs_phase ON jobs(phase)"))

                # 4. Add moment_id to clips
                logger.info("Adding moment_id column to clips table...")
                conn.execute(text("""
                    ALTER TABLE clips
                    ADD COLUMN IF NOT EXISTS moment_id UUID REFERENCES moments(id) ON DELETE SET NULL
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_clips_moment_id ON clips(moment_id)"))

                # Commit transaction
                trans.commit()
                logger.info("✅ Migration completed successfully!")

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
                logger.info("🔄 Starting rollback: add_moments_table")

                # Remove in reverse order
                logger.info("Dropping clips.moment_id column...")
                conn.execute(text("DROP INDEX IF EXISTS idx_clips_moment_id"))
                conn.execute(text("ALTER TABLE clips DROP COLUMN IF EXISTS moment_id"))

                logger.info("Dropping jobs.phase column...")
                conn.execute(text("DROP INDEX IF EXISTS idx_jobs_phase"))
                conn.execute(text("ALTER TABLE jobs DROP COLUMN IF EXISTS phase"))

                logger.info("Dropping moments table...")
                conn.execute(text("DROP INDEX IF EXISTS idx_moments_index"))
                conn.execute(text("DROP INDEX IF EXISTS idx_moments_created_at"))
                conn.execute(text("DROP INDEX IF EXISTS idx_moments_is_selected"))
                conn.execute(text("DROP INDEX IF EXISTS idx_moments_job_id"))
                conn.execute(text("DROP TABLE IF EXISTS moments"))

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

    parser = argparse.ArgumentParser(description='Database migration: add moments table')
    parser.add_argument('action', choices=['upgrade', 'downgrade'],
                       help='Migration action to perform')

    args = parser.parse_args()

    if args.action == 'upgrade':
        upgrade()
    elif args.action == 'downgrade':
        downgrade()
