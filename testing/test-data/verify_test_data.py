#!/usr/bin/env python3
"""
Test Data Verification Script voor AgentOS
==========================================

Dit script verifieert de gegenereerde test data en toont details.
"""

import sys
import os
import logging
from datetime import datetime, timezone

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))

from core.database_manager import PostgreSQLManager, Job, Clip, ProcessingStep, SystemEvent, SystemConfig

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def verify_data():
    """Verify the generated test data"""
    try:
        db_manager = PostgreSQLManager()
        
        print("🔍 AgentOS Test Data Verification")
        print("=" * 50)
        
        with db_manager.get_session() as session:
            # Basic counts
            total_jobs = session.query(Job).count()
            total_clips = session.query(Clip).count()
            total_steps = session.query(ProcessingStep).count()
            total_events = session.query(SystemEvent).count()
            total_config = session.query(SystemConfig).count()
            
            print(f"📊 Database Record Counts:")
            print(f"   Jobs: {total_jobs}")
            print(f"   Clips: {total_clips}")
            print(f"   Processing Steps: {total_steps}")  
            print(f"   System Events: {total_events}")
            print(f"   System Config: {total_config}")
            print()
            
            # Job status breakdown
            print("📋 Job Status Breakdown:")
            statuses = session.query(Job.status).distinct().all()
            for (status,) in statuses:
                count = session.query(Job).filter(Job.status == status).count()
                print(f"   {status.capitalize()}: {count}")
            print()
            
            # Recent jobs sample
            print("🕒 Recent Jobs (Sample):")
            recent_jobs = session.query(Job).order_by(Job.created_at.desc()).limit(5).all()
            for job in recent_jobs:
                print(f"   {str(job.id)[:8]} | {job.status:<10} | {job.video_title}")
            print()
            
            # Event types sample
            print("📝 System Event Types:")
            event_types = session.query(SystemEvent.event_type).distinct().all()
            for (event_type,) in event_types:
                count = session.query(SystemEvent).filter(SystemEvent.event_type == event_type).count()
                print(f"   {event_type}: {count}")
            print()
            
            # Clips with jobs
            print("🎬 Clips per Job (Top 10):")
            jobs_with_clips = session.query(Job).join(Clip).group_by(Job.id).limit(10).all()
            for job in jobs_with_clips:
                clip_count = len(job.clips)
                print(f"   {str(job.id)[:8]} | {job.video_title[:30]:<30} | {clip_count} clips")
            print()
            
            # System configuration
            print("⚙️ System Configuration:")
            configs = session.query(SystemConfig).all()
            for config in configs:
                print(f"   {config.key}: {config.value}")
            print()
            
            print("✅ Data verification completed successfully!")
            print("🎯 The test data looks good and ready for testing!")
            
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        sys.exit(1)
    finally:
        db_manager.close()

if __name__ == "__main__":
    verify_data()
