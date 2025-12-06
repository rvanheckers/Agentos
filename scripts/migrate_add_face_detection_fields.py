#!/usr/bin/env python3
"""
Database migration: Add face detection and smart cropping fields to clips table
"""

import sys
import os

# Add project root to path
sys.path.insert(0, '/mnt/c/Users/rober/OneDrive/Bureaublad/Projecten/01_Active_Development/AgentOS')

from core.database_pool import get_db_session
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_clips_table():
    """Add new face detection fields to clips table"""
    
    migrations = [
        """
        ALTER TABLE clips 
        ADD COLUMN IF NOT EXISTS original_video_path TEXT;
        """,
        """
        ALTER TABLE clips 
        ADD COLUMN IF NOT EXISTS faces_detected INTEGER;
        """,
        """
        ALTER TABLE clips 
        ADD COLUMN IF NOT EXISTS crop_method VARCHAR(50);
        """,
        """
        ALTER TABLE clips 
        ADD COLUMN IF NOT EXISTS processing_metadata TEXT;
        """
    ]
    
    try:
        with get_db_session() as session:
            logger.info("🗄️ Starting database migration for face detection fields...")
            
            for i, migration_sql in enumerate(migrations, 1):
                logger.info(f"Running migration {i}/4...")
                session.execute(text(migration_sql))
                logger.info(f"✅ Migration {i}/4 completed")
            
            session.commit()
            logger.info("✅ All migrations completed successfully!")
            
            # Verify new columns exist
            result = session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'clips' 
                AND column_name IN ('original_video_path', 'faces_detected', 'crop_method', 'processing_metadata')
                ORDER BY column_name;
            """))
            
            new_columns = [row[0] for row in result.fetchall()]
            logger.info(f"✅ Verified new columns: {new_columns}")
            
            if len(new_columns) == 4:
                logger.info("🎯 Migration successful - all 4 fields added!")
                return True
            else:
                logger.error(f"❌ Migration incomplete - only {len(new_columns)} fields added")
                return False
                
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = migrate_clips_table()
    sys.exit(0 if success else 1)