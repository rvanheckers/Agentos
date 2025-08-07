#!/usr/bin/env python3
"""
Deep Metrics Analysis voor AgentOS Dashboard
===========================================

Dit script analyseert de discrepanties in metrics berekeningen
en identificeert waar de verschillen vandaan komen.
"""

import sys
import os
from datetime import datetime, date, timezone, timedelta
from typing import Dict, Any

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('../..'))

from core.database_manager import PostgreSQLManager, Job, Clip, ProcessingStep, SystemEvent
from sqlalchemy import func

class DeepMetricsAnalysis:
    def __init__(self):
        self.db_manager = PostgreSQLManager()
    
    def analyze_success_rate_calculations(self):
        """Analyze different success rate calculation methods"""
        print("🔍 Success Rate Calculation Analysis")
        print("=" * 50)
        
        with self.db_manager.get_session() as session:
            # Method 1: All time success rate (what direct DB uses)
            total_jobs = session.query(Job).count()
            completed_jobs = session.query(Job).filter(Job.status == 'completed').count()
            failed_jobs = session.query(Job).filter(Job.status == 'failed').count()
            
            # All time success rate
            all_time_success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
            
            print(f"📊 ALL TIME SUCCESS RATE:")
            print(f"   Total jobs: {total_jobs}")
            print(f"   Completed: {completed_jobs}")
            print(f"   Failed: {failed_jobs}")
            print(f"   Success Rate: {all_time_success_rate:.2f}%")
            
            # Method 2: Last 100 jobs success rate (what db_manager.get_stats uses)
            last_100_jobs = session.query(Job).order_by(Job.created_at.desc()).limit(100).all()
            if last_100_jobs:
                completed_count = sum(1 for job in last_100_jobs if job.status == 'completed')
                last_100_success_rate = (completed_count / len(last_100_jobs)) * 100
            else:
                last_100_success_rate = 0
                
            print(f"\n📊 LAST 100 JOBS SUCCESS RATE:")
            print(f"   Jobs analyzed: {len(last_100_jobs)}")
            print(f"   Completed: {completed_count if last_100_jobs else 0}")
            print(f"   Success Rate: {last_100_success_rate:.2f}%")
            
            # Method 3: Last 30 days success rate (what SSOT API might use)
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            recent_jobs = session.query(Job).filter(Job.created_at >= thirty_days_ago).all()
            
            if recent_jobs:
                recent_completed = sum(1 for job in recent_jobs if job.status == 'completed')
                recent_success_rate = (recent_completed / len(recent_jobs)) * 100
            else:
                recent_completed = 0
                recent_success_rate = 0
                
            print(f"\n📊 LAST 30 DAYS SUCCESS RATE:")
            print(f"   Jobs analyzed: {len(recent_jobs)}")
            print(f"   Completed: {recent_completed}")
            print(f"   Success Rate: {recent_success_rate:.2f}%")
            
            # Method 4: Only completed + failed jobs (excluding pending/processing)
            finished_jobs = session.query(Job).filter(Job.status.in_(['completed', 'failed'])).all()
            if finished_jobs:
                finished_completed = sum(1 for job in finished_jobs if job.status == 'completed')
                finished_success_rate = (finished_completed / len(finished_jobs)) * 100
            else:
                finished_completed = 0 
                finished_success_rate = 0
                
            print(f"\n📊 FINISHED JOBS ONLY SUCCESS RATE:")
            print(f"   Finished jobs: {len(finished_jobs)}")
            print(f"   Completed: {finished_completed}")
            print(f"   Success Rate: {finished_success_rate:.2f}%")
            
            return {
                'all_time': all_time_success_rate,
                'last_100': last_100_success_rate,
                'last_30_days': recent_success_rate,
                'finished_only': finished_success_rate
            }
    
    def analyze_job_status_distribution(self):
        """Analyze job status distribution"""
        print("\n🔍 Job Status Distribution Analysis")
        print("=" * 50)
        
        with self.db_manager.get_session() as session:
            # Get all statuses
            status_counts = session.query(Job.status, func.count(Job.id)).group_by(Job.status).all()
            
            total_jobs = sum(count for _, count in status_counts)
            
            print(f"📊 JOB STATUS BREAKDOWN:")
            for status, count in status_counts:
                percentage = (count / total_jobs * 100) if total_jobs > 0 else 0
                print(f"   {status.capitalize():<12}: {count:>3} ({percentage:>5.1f}%)")
            
            print(f"\n   Total Jobs: {total_jobs}")
            
            # Check for any unusual statuses
            expected_statuses = {'pending', 'processing', 'completed', 'failed'}
            actual_statuses = {status for status, _ in status_counts}
            
            unexpected = actual_statuses - expected_statuses
            if unexpected:
                print(f"\n⚠️  Unexpected statuses found: {unexpected}")
            
            missing = expected_statuses - actual_statuses
            if missing:
                print(f"\n⚠️  Expected statuses missing: {missing}")
    
    def analyze_timestamp_patterns(self):
        """Analyze timestamp patterns to understand today's job discrepancy"""
        print("\n🔍 Timestamp Pattern Analysis")
        print("=" * 50)
        
        with self.db_manager.get_session() as session:
            # Check what dates we have jobs for
            job_dates = session.query(
                func.date(Job.created_at).label('job_date'),
                func.count(Job.id).label('count')
            ).group_by(func.date(Job.created_at)).order_by(func.date(Job.created_at).desc()).limit(10).all()
            
            print(f"📊 JOBS BY DATE (Last 10 days):")
            today = date.today()
            
            for job_date, count in job_dates:
                if job_date == today:
                    print(f"   {job_date} (TODAY): {count} jobs ⭐")
                else:
                    days_ago = (today - job_date).days
                    print(f"   {job_date} ({days_ago} days ago): {count} jobs")
            
            # Check timezone issues
            print(f"\n🕐 TIMEZONE ANALYSIS:")
            print(f"   Current UTC time: {datetime.now(timezone.utc)}")
            print(f"   Current local date: {date.today()}")
            
            # Get some sample timestamps
            sample_jobs = session.query(Job).order_by(Job.created_at.desc()).limit(5).all()
            print(f"\n📅 SAMPLE TIMESTAMPS:")
            for job in sample_jobs:
                print(f"   {job.id}: {job.created_at} (UTC)")
                local_date = job.created_at.date() if job.created_at else None
                print(f"      -> Date: {local_date}")
    
    def analyze_database_service_calculations(self):
        """Analyze how DatabaseService calculates metrics"""
        print("\n🔍 Database Service Calculation Analysis")
        print("=" * 50)
        
        # Import and test the database service directly
        from api.services.database_service import DatabaseService
        
        db_service = DatabaseService()
        
        # Get stats the same way the service does
        stats = db_service.get_stats()
        analytics = db_service.get_analytics_data()
        today_jobs = db_service.get_today_jobs()
        
        print(f"📊 DATABASE SERVICE METRICS:")
        print(f"   get_stats() success_rate: {stats.get('success_rate', 'N/A')}%")
        print(f"   get_analytics_data() success_rate: {analytics.get('success_rate', 'N/A')}%")
        print(f"   Today's jobs: {today_jobs.get('total_jobs', 'N/A')}")
        
        # Show what get_stats actually returns
        print(f"\n📊 FULL get_stats() RESULT:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
    
    def analyze_ssot_api_source(self):
        """Analyze where SSOT API gets its 81.71% success rate"""
        print("\n🔍 SSOT API Success Rate Source Analysis") 
        print("=" * 50)
        
        # The SSOT API shows 81.71% - let's see where this comes from
        # Look at the admin_ssot.py route implementation
        
        try:
            from api.routes.admin_ssot import router
            print("📊 SSOT API route found - checking implementation...")
            
            # Since we can't easily trace the exact calculation, let's try different approaches
            with self.db_manager.get_session() as session:
                # Test various calculation methods that might result in 81.71%
                
                # Method 1: Exclude very recent jobs (maybe incomplete)
                one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
                older_jobs = session.query(Job).filter(Job.created_at < one_day_ago).all()
                
                if older_jobs:
                    older_completed = sum(1 for job in older_jobs if job.status == 'completed')
                    older_success = (older_completed / len(older_jobs)) * 100
                    print(f"   Jobs older than 1 day: {len(older_jobs)}, Success: {older_success:.2f}%")
                
                # Method 2: Weight by some factor
                completed_jobs = session.query(Job).filter(Job.status == 'completed').count()
                total_jobs = session.query(Job).count()
                
                # Maybe it's using a different denominator?
                processing_and_completed = session.query(Job).filter(
                    Job.status.in_(['completed', 'failed', 'processing'])
                ).count()
                
                if processing_and_completed > 0:
                    weighted_success = (completed_jobs / processing_and_completed) * 100
                    print(f"   Completed / (Completed + Failed + Processing): {weighted_success:.2f}%")
                
                # Method 3: Maybe it's a running average or cached value
                print(f"   Direct calculation gives: {(completed_jobs/total_jobs)*100:.2f}%")
                print(f"   SSOT API shows: 81.71%")
                print(f"   Difference: {81.71 - (completed_jobs/total_jobs)*100:.2f} percentage points")
                
        except Exception as e:
            print(f"   Could not analyze SSOT route directly: {e}")
    
    def run_complete_analysis(self):
        """Run all analysis methods"""
        print("🔍 AgentOS Dashboard Metrics Deep Analysis")
        print("=" * 60)
        
        success_rates = self.analyze_success_rate_calculations()
        self.analyze_job_status_distribution()
        self.analyze_timestamp_patterns()
        self.analyze_database_service_calculations()
        self.analyze_ssot_api_source()
        
        print("\n📊 SUMMARY OF FINDINGS")
        print("=" * 50)
        
        print(f"Success Rate Variations:")
        for method, rate in success_rates.items():
            print(f"   {method.replace('_', ' ').title()}: {rate:.2f}%")
        
        print(f"\nKey Issues Identified:")
        if abs(success_rates['all_time'] - success_rates['last_100']) > 1:
            print(f"   • Different time ranges affect success rate significantly")
        
        print(f"   • SSOT API (81.71%) vs Direct DB ({success_rates['all_time']:.2f}%) = {81.71 - success_rates['all_time']:.2f}pp difference")
        print(f"   • This suggests SSOT API uses a different calculation method")
        print(f"   • No jobs today - all test data is from previous days")
        
        print(f"\nRecommendations:")
        print(f"   1. Standardize success rate calculation across all endpoints")
        print(f"   2. Document which time range/method each endpoint uses")
        print(f"   3. Consider generating some test data for today to test 'today' metrics")
        print(f"   4. Investigate SSOT API calculation to understand 81.71% source")

def main():
    """Main function"""
    try:
        analyzer = DeepMetricsAnalysis()
        analyzer.run_complete_analysis()
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()