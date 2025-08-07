#!/usr/bin/env python3
"""
Nuclear Database Reset - Drop & Recreate All Tables
===================================================
DESTRUCTIVE: All data will be lost!
Use only in development environment.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database_manager import PostgreSQLManager, Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def nuclear_reset():
    """Drop and recreate all database tables"""
    try:
        # Initialize database manager
        db = PostgreSQLManager()
        
        logger.info("🚨 NUCLEAR RESET: Dropping all tables...")
        
        # Drop all tables
        Base.metadata.drop_all(bind=db.engine)
        logger.info("💀 All tables dropped successfully")
        
        # Recreate all tables with current schema
        Base.metadata.create_all(bind=db.engine)
        logger.info("✅ All tables recreated with current schema")
        
        # Verify tables exist
        from sqlalchemy import text
        with db.engine.connect() as conn:
            result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
            tables = [row[0] for row in result]
            logger.info(f"📋 Created tables: {', '.join(tables)}")
        
        db.close()
        logger.info("🎉 Database reset complete! All schema issues resolved.")
        
    except Exception as e:
        logger.error(f"❌ Database reset failed: {e}")
        raise

if __name__ == "__main__":
    print("🚨 WARNING: This will DELETE ALL DATA in the database!")
    print("Press Enter to continue or Ctrl+C to abort...")
    input()
    
    nuclear_reset()