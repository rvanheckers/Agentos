#!/usr/bin/env python3
"""
Dashboard Metrics Comparison Tool
=================================

Dit script vergelijkt de dashboard metrics met de werkelijke database data
om inconsistenties te identificeren en live data bronnen te valideren.
"""

import sys
import os
import json
import requests
from datetime import datetime, date
from typing import Dict, Any

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('../..'))

from core.database_manager import PostgreSQLManager, Job, Clip, ProcessingStep, SystemEvent, SystemConfig
from api.services.database_service import DatabaseService

class DashboardMetricsComparison:
    def __init__(self):
        self.db_manager = PostgreSQLManager()
        self.db_service = DatabaseService()
        self.api_base_url = "http://localhost:8001"
    
    def get_database_stats_direct(self) -> Dict[str, Any]:
        """Get direct database statistics"""
        print("📊 Getting direct database statistics...")
        
        with self.db_manager.get_session() as session:
            # Basic counts
            total_jobs = session.query(Job).count()
            total_clips = session.query(Clip).count()
            total_steps = session.query(ProcessingStep).count()
            total_events = session.query(SystemEvent).count()
            
            # Job status counts
            completed_jobs = session.query(Job).filter(Job.status == 'completed').count()
            failed_jobs = session.query(Job).filter(Job.status == 'failed').count()
            processing_jobs = session.query(Job).filter(Job.status == 'processing').count()
            pending_jobs = session.query(Job).filter(Job.status == 'pending').count()
            
            # Today's jobs
            today = date.today()
            from sqlalchemy import func
            today_jobs_query = session.query(Job).filter(func.date(Job.created_at) == today)
            today_total = today_jobs_query.count()
            today_completed = today_jobs_query.filter(Job.status == 'completed').count()
            today_processing = today_jobs_query.filter(Job.status == 'processing').count()
            today_pending = today_jobs_query.filter(Job.status.in_(['pending', 'queued'])).count()
            today_failed = today_jobs_query.filter(Job.status == 'failed').count()
            
            # Success rate calculation
            success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
            
            return {
                "total_jobs": total_jobs,
                "total_clips": total_clips,
                "total_processing_steps": total_steps,
                "total_system_events": total_events,
                "completed_jobs": completed_jobs,
                "failed_jobs": failed_jobs,
                "processing_jobs": processing_jobs,
                "pending_jobs": pending_jobs,
                "success_rate": round(success_rate, 1),
                "today_stats": {
                    "total": today_total,
                    "completed": today_completed,
                    "processing": today_processing,
                    "pending": today_pending,
                    "failed": today_failed
                }
            }
    
    def get_database_service_stats(self) -> Dict[str, Any]:
        """Get stats via DatabaseService"""
        print("🔧 Getting stats via DatabaseService...")
        
        try:
            stats = self.db_service.get_stats()
            today_jobs = self.db_service.get_today_jobs()
            analytics = self.db_service.get_analytics_data()
            
            return {
                "db_stats": stats,
                "today_jobs": today_jobs,
                "analytics": analytics
            }
        except Exception as e:
            print(f"❌ Error getting database service stats: {e}")
            return {}
    
    def get_dashboard_api_data(self) -> Dict[str, Any]:
        """Get data from dashboard SSOT API"""
        print("🌐 Getting data from dashboard SSOT API...")
        
        try:
            response = requests.get(f"{self.api_base_url}/api/admin/ssot", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ API returned status {response.status_code}")
                return {}
        except requests.exceptions.ConnectionError:
            print("❌ Could not connect to API - is the server running?")
            return {}
        except Exception as e:
            print(f"❌ Error getting dashboard API data: {e}")
            return {}
    
    def compare_metrics(self):
        """Compare all metrics sources"""
        print("🔍 Dashboard Metrics Comparison Report")
        print("=" * 60)
        
        # Get data from all sources
        direct_db = self.get_database_stats_direct()
        db_service = self.get_database_service_stats()
        api_data = self.get_dashboard_api_data()
        
        print("\n1. 📊 DIRECT DATABASE STATS")
        print("-" * 40)
        print(f"Total Jobs:           {direct_db['total_jobs']}")
        print(f"Total Clips:          {direct_db['total_clips']}")
        print(f"Total Steps:          {direct_db['total_processing_steps']}")
        print(f"Total Events:         {direct_db['total_system_events']}")
        print(f"Completed Jobs:       {direct_db['completed_jobs']}")
        print(f"Failed Jobs:          {direct_db['failed_jobs']}")
        print(f"Processing Jobs:      {direct_db['processing_jobs']}")
        print(f"Pending Jobs:         {direct_db['pending_jobs']}")
        print(f"Success Rate:         {direct_db['success_rate']}%")
        
        print(f"\nToday's Jobs:         {direct_db['today_stats']['total']}")
        print(f"- Completed:          {direct_db['today_stats']['completed']}")
        print(f"- Processing:         {direct_db['today_stats']['processing']}")
        print(f"- Pending:            {direct_db['today_stats']['pending']}")
        print(f"- Failed:             {direct_db['today_stats']['failed']}")
        
        print("\n2. 🔧 DATABASE SERVICE STATS")
        print("-" * 40)
        if db_service:
            stats = db_service.get('db_stats', {})
            today = db_service.get('today_jobs', {})
            analytics = db_service.get('analytics', {})
            
            print(f"Total Jobs:           {stats.get('total_jobs', 'N/A')}")
            print(f"Completed Jobs:       {stats.get('completed_jobs', 'N/A')}")
            print(f"Failed Jobs:          {stats.get('failed_jobs', 'N/A')}")
            print(f"Processing Jobs:      {stats.get('processing_jobs', 'N/A')}")
            print(f"Pending Jobs:         {stats.get('pending_jobs', 'N/A')}")
            print(f"Success Rate:         {stats.get('success_rate', 'N/A')}%")
            
            print(f"\nToday's Jobs:         {today.get('total_jobs', 'N/A')}")
            print(f"- Completed:          {today.get('completed', 'N/A')}")
            print(f"- Processing:         {today.get('processing', 'N/A')}")
            print(f"- Pending:            {today.get('pending', 'N/A')}")
            print(f"- Failed:             {today.get('failed', 'N/A')}")
            
            print(f"\nAnalytics:")
            print(f"- Success Rate:       {analytics.get('success_rate', 'N/A')}%")
            print(f"- Avg Processing:     {analytics.get('avg_processing_time', 'N/A')}s")
        else:
            print("❌ No data available")
        
        print("\n3. 🌐 DASHBOARD SSOT API DATA")
        print("-" * 40)
        if api_data:
            # Dashboard data
            dashboard = api_data.get('dashboard', {})
            
            # Workers data
            workers = dashboard.get('workers', {})
            print(f"Workers Total:        {workers.get('total', 'N/A')}")
            print(f"Workers Active:       {workers.get('active', 'N/A')}")
            print(f"Workers Idle:         {workers.get('idle', 'N/A')}")
            print(f"Workers Offline:      {workers.get('offline', 'N/A')}")
            
            # Queue data
            queue_data = dashboard.get('queue', {})
            print(f"\nQueue Pending:        {queue_data.get('pending', 'N/A')}")
            print(f"Queue Processing:     {queue_data.get('processing', 'N/A')}")
            print(f"Queue Completed:      {queue_data.get('completed_today', 'N/A')}")
            print(f"Queue Failed:         {queue_data.get('failed_today', 'N/A')}")
            
            # Jobs data  
            jobs_data = dashboard.get('jobs', {})
            print(f"\nJobs Today:           {jobs_data.get('total_today', 'N/A')}")
            print(f"Jobs Success Rate:    {jobs_data.get('success_rate', 'N/A')}%")
            print(f"Jobs Avg Duration:    {jobs_data.get('avg_duration', 'N/A')}s")
            
            # System data
            system = dashboard.get('system', {})
            print(f"\nSystem API Status:    {system.get('api_status', 'N/A')}")
            print(f"System DB Status:     {system.get('database_status', 'N/A')}")
            print(f"System Redis Status:  {system.get('redis_status', 'N/A')}")
            print(f"System CPU Usage:     {system.get('cpu_usage', 'N/A')}%")
            print(f"System Memory Usage:  {system.get('memory_usage', 'N/A')}%")
            print(f"System Disk Usage:    {system.get('disk_usage', 'N/A')}%")
            
            # Queue section data
            queue_section = api_data.get('queue', {})
            current_queue = queue_section.get('current_queue', {})
            print(f"\nQueue Section:")
            print(f"- Pending:            {current_queue.get('pending', 'N/A')}")
            print(f"- Processing:         {current_queue.get('processing', 'N/A')}")
            print(f"- Completed:          {current_queue.get('completed', 'N/A')}")
            print(f"- Failed:             {current_queue.get('failed', 'N/A')}")
            print(f"- Total:              {current_queue.get('total', 'N/A')}")
            
        else:
            print("❌ No API data available or API returned error")
            if api_data:
                print(f"API Status: {api_data.get('status', 'unknown')}")
        
        print("\n4. 🔍 DISCREPANCY ANALYSIS")
        print("-" * 40)
        
        discrepancies = []
        
        # Compare direct DB vs DB Service
        if db_service and db_service.get('db_stats'):
            db_stats = db_service['db_stats']
            
            if direct_db['total_jobs'] != db_stats.get('total_jobs', 0):
                discrepancies.append(f"Total jobs: Direct DB ({direct_db['total_jobs']}) vs DB Service ({db_stats.get('total_jobs')})")
            
            if direct_db['completed_jobs'] != db_stats.get('completed_jobs', 0):
                discrepancies.append(f"Completed jobs: Direct DB ({direct_db['completed_jobs']}) vs DB Service ({db_stats.get('completed_jobs')})")
            
            if abs(direct_db['success_rate'] - db_stats.get('success_rate', 0)) > 0.1:
                discrepancies.append(f"Success rate: Direct DB ({direct_db['success_rate']}%) vs DB Service ({db_stats.get('success_rate')}%)")
        
        # Compare with SSOT API
        if api_data:
            dashboard = api_data.get('dashboard', {})
            queue_section = api_data.get('queue', {})
            current_queue = queue_section.get('current_queue', {})
            
            # Compare total jobs
            if direct_db['total_jobs'] != current_queue.get('total', 0):
                discrepancies.append(f"Total jobs: Direct DB ({direct_db['total_jobs']}) vs SSOT API ({current_queue.get('total')})")
            
            # Compare job statuses
            if direct_db['completed_jobs'] != current_queue.get('completed', 0):
                discrepancies.append(f"Completed jobs: Direct DB ({direct_db['completed_jobs']}) vs SSOT API ({current_queue.get('completed')})")
                
            if direct_db['failed_jobs'] != current_queue.get('failed', 0):
                discrepancies.append(f"Failed jobs: Direct DB ({direct_db['failed_jobs']}) vs SSOT API ({current_queue.get('failed')})")
                
            if direct_db['processing_jobs'] != current_queue.get('processing', 0):
                discrepancies.append(f"Processing jobs: Direct DB ({direct_db['processing_jobs']}) vs SSOT API ({current_queue.get('processing')})")
                
            if direct_db['pending_jobs'] != current_queue.get('pending', 0):
                discrepancies.append(f"Pending jobs: Direct DB ({direct_db['pending_jobs']}) vs SSOT API ({current_queue.get('pending')})")
            
            # Compare success rate
            jobs_data = dashboard.get('jobs', {})
            api_success_rate = jobs_data.get('success_rate', 0)
            if abs(direct_db['success_rate'] - api_success_rate) > 0.1:
                discrepancies.append(f"Success rate: Direct DB ({direct_db['success_rate']}%) vs SSOT API ({api_success_rate}%)")
            
            # Compare today's jobs
            api_today_total = jobs_data.get('total_today', 0)
            if direct_db['today_stats']['total'] != api_today_total:
                discrepancies.append(f"Today's total jobs: Direct DB ({direct_db['today_stats']['total']}) vs SSOT API ({api_today_total})")
        
        if discrepancies:
            print("⚠️  Found discrepancies:")
            for i, discrepancy in enumerate(discrepancies, 1):
                print(f"   {i}. {discrepancy}")
        else:
            print("✅ No significant discrepancies found!")
        
        print("\n5. 🎯 RECOMMENDATIONS")
        print("-" * 40)
        
        recommendations = []
        
        if not api_data:
            recommendations.append("Start the API server to test dashboard endpoints")
        elif api_data.get('data', {}).get('workers', {}).get('is_mock_data'):
            recommendations.append("Workers data is mocked - check Celery connection")
        
        if discrepancies:
            recommendations.append("Fix data source inconsistencies identified above")
        
        if db_service.get('analytics', {}).get('avg_processing_time') == 125:
            recommendations.append("Implement real average processing time calculation from processing_steps table")
        
        if not recommendations:
            recommendations.append("All metrics sources are aligned and working correctly!")
        
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
        
        print(f"\n📊 Report completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def main():
    """Main function"""
    try:
        comparison = DashboardMetricsComparison()
        comparison.compare_metrics()
        
    except Exception as e:
        print(f"❌ Comparison failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()