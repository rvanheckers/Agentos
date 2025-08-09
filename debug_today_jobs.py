#!/usr/bin/env python3
"""
Debug script voor Today's Jobs issue
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from services.jobs_service import JobsService
from core.database_manager import PostgreSQLManager
from datetime import date
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    print("🔍 Debugging Today's Jobs issue...")

    try:
        # Initialize services
        db = PostgreSQLManager()
        jobs_service = JobsService(db)

        print(f"📅 Today's date: {date.today()}")

        # Test get_todays_jobs directly
        todays_jobs = jobs_service.get_todays_jobs(is_admin=True)
        print(f"📋 get_todays_jobs() returned: {len(todays_jobs)} jobs")

        for job in todays_jobs[:3]:  # Show first 3
            print(f"  - {str(job['id'])[:8]}... | {job['status']} | {job['created_at']}")

        # Test get_job_statistics
        stats = jobs_service.get_job_statistics(is_admin=True)
        print("📊 get_job_statistics() returned:")
        print(f"  - Total jobs: {stats.get('total_jobs', 'N/A')}")
        print(f"  - Todays jobs: {stats.get('todays_jobs', 'N/A')}")
        print(f"  - Success rate: {stats.get('success_rate', 'N/A')}%")

        # Manual database check
        with db.get_session() as session:
            from core.database_manager import Job
            from sqlalchemy import func

            # Count today's jobs manually
            today = date.today()
            manual_count = session.query(Job).filter(func.date(Job.created_at) == today).count()
            print(f"🔍 Manual database query: {manual_count} jobs today")

            # Get some sample jobs to inspect
            sample_jobs = session.query(Job).filter(func.date(Job.created_at) == today).limit(3).all()
            print("📝 Sample jobs from today:")
            for job in sample_jobs:
                print(f"  - {str(job.id)[:8]}... | {job.status} | {job.created_at} | Type: {type(job.created_at)}")

    except Exception as e:
        logger.error(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
