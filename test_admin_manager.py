#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from services.admin_data_manager import AdminDataManager

def main():
    print("🔍 Testing AdminDataManager direct...")
    
    manager = AdminDataManager()
    
    # Test _get_jobs_summary directly
    jobs_summary = manager._get_jobs_summary()
    print(f"📊 _get_jobs_summary() returned:")
    print(f"  - total_today: {jobs_summary.get('total_today', 'N/A')}")
    print(f"  - success_rate: {jobs_summary.get('success_rate', 'N/A')}")
    print(f"  - recent_jobs count: {len(jobs_summary.get('recent_jobs', []))}")
    
    # Test jobs_service direct
    job_stats = manager.jobs_service.get_job_statistics(is_admin=True)
    print(f"📈 jobs_service.get_job_statistics(is_admin=True):")
    print(f"  - total_jobs: {job_stats.get('total_jobs', 'N/A')}")
    print(f"  - todays_jobs: {job_stats.get('todays_jobs', 'N/A')}")
    
if __name__ == "__main__":
    main()