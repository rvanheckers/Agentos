#!/usr/bin/env python3
"""
Dashboard Data Validation Script
=================================
This script validates what the dashboard SHOULD show vs what it ACTUALLY shows
by checking all layers of the data flow.
"""

import json
import os
import requests
import sys
from datetime import datetime, timezone
from colorama import init, Fore, Style
from tabulate import tabulate

# Add project to path - portable approach
# Fallback order: 1) PROJECT_ROOT env var -> 2) relative discovery -> 3) skip
project_path = None

# Try environment variable first
if 'PROJECT_ROOT' in os.environ:
    project_path = os.environ['PROJECT_ROOT']
elif 'PYTHONPATH' in os.environ and os.environ['PYTHONPATH']:
    # Use first path from PYTHONPATH if available
    project_path = os.environ['PYTHONPATH'].split(os.pathsep)[0]
else:
    # Fallback: compute relative to script location
    # Assume script is in project root, so use directory containing this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_path = script_dir

# Add to sys.path only if path exists and not already present
if project_path and os.path.exists(project_path) and project_path not in sys.path:
    sys.path.append(project_path)

# Initialize colorama for colored output
init(autoreset=True)

class DashboardValidator:
    def __init__(self):
        self.api_url = "http://localhost:8001/api/admin/ssot"
        self.results = {}
        
    def run_full_validation(self):
        """Run complete validation of dashboard data flow"""
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}📊 DASHBOARD DATA VALIDATION - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.CYAN}{'='*80}\n")
        
        # Step 1: Check Backend Services
        self.check_backend_services()
        
        # Step 2: Check API Response
        self.check_api_response()
        
        # Step 3: Validate Data Consistency
        self.validate_data_consistency()
        
        # Step 4: Generate Report
        self.generate_report()
        
    def check_backend_services(self):
        """Check what backend services are calculating"""
        print(f"{Fore.YELLOW}1️⃣  BACKEND SERVICES CHECK{Style.RESET_ALL}")
        print("-" * 40)
        
        try:
            from services.queue_service import QueueService
            from services.admin_data_manager import AdminDataManager
            from api.services.database_service import DatabaseService
            
            # Check QueueService
            queue_service = QueueService()
            queue_status = queue_service.get_queue_status(is_admin=True)
            
            print(f"{Fore.GREEN}✓ QueueService.get_queue_status():{Style.RESET_ALL}")
            print(f"  completed_today: {queue_status.get('completed_today', 'MISSING')}")
            print(f"  failed_today: {queue_status.get('failed_today', 'MISSING')}")
            print(f"  pending: {queue_status.get('pending', 'MISSING')}")
            print(f"  processing: {queue_status.get('processing', 'MISSING')}")
            
            self.results['queue_service'] = queue_status
            
            # Check AdminDataManager
            admin_data = AdminDataManager()
            queue_summary = admin_data._get_queue_summary()
            
            print(f"\n{Fore.GREEN}✓ AdminDataManager._get_queue_summary():{Style.RESET_ALL}")
            print(f"  completed_today: {queue_summary.get('completed_today', 'MISSING')}")
            print(f"  failed_today: {queue_summary.get('failed_today', 'MISSING')}")
            
            self.results['admin_manager'] = queue_summary
            
            # Check raw database
            db_service = DatabaseService()
            all_jobs = db_service.get_jobs(limit=100)
            
            # Count today's jobs
            today = datetime.now(timezone.utc).date()
            today_completed = 0
            today_failed = 0
            
            for job in all_jobs:
                job_date = None
                if job.get('created_at'):
                    try:
                        date_str = job['created_at'].split('T')[0]
                        job_date = datetime.fromisoformat(date_str).date()
                    except:
                        pass
                
                if job_date == today:
                    if job['status'] == 'completed':
                        today_completed += 1
                    elif job['status'] == 'failed':
                        today_failed += 1
            
            print(f"\n{Fore.GREEN}✓ Database (raw count):{Style.RESET_ALL}")
            print(f"  Today's completed: {today_completed}")
            print(f"  Today's failed: {today_failed}")
            print(f"  Total jobs in DB: {len(all_jobs)}")
            
            self.results['database'] = {
                'today_completed': today_completed,
                'today_failed': today_failed,
                'total_jobs': len(all_jobs)
            }
            
        except Exception as e:
            print(f"{Fore.RED}✗ Backend check failed: {e}{Style.RESET_ALL}")
            
    def check_api_response(self):
        """Check what the API is returning"""
        print(f"\n{Fore.YELLOW}2️⃣  API RESPONSE CHECK{Style.RESET_ALL}")
        print("-" * 40)
        
        try:
            response = requests.get(self.api_url, timeout=10)
            data = response.json()
            
            # Extract relevant data
            dashboard = data.get('dashboard', {})
            queue = dashboard.get('queue', {})
            jobs = dashboard.get('jobs', {})
            
            print(f"{Fore.GREEN}✓ API Response (http://localhost:8001/api/admin/ssot):{Style.RESET_ALL}")
            print(f"  dashboard.queue.completed_today: {queue.get('completed_today', 'MISSING')}")
            print(f"  dashboard.queue.failed_today: {queue.get('failed_today', 'MISSING')}")
            print(f"  dashboard.jobs.total_today: {jobs.get('total_today', 'MISSING')}")
            print(f"  dashboard.jobs.success_rate: {jobs.get('success_rate', 'MISSING')}")
            
            self.results['api_response'] = {
                'queue': queue,
                'jobs': jobs
            }
            
            # Check for missing fields
            missing_fields = []
            if 'completed_today' not in queue:
                missing_fields.append('queue.completed_today')
            if 'failed_today' not in queue:
                missing_fields.append('queue.failed_today')
            if 'total_today' not in jobs:
                missing_fields.append('jobs.total_today')
                
            if missing_fields:
                print(f"\n{Fore.RED}⚠️  Missing fields in API response:{Style.RESET_ALL}")
                for field in missing_fields:
                    print(f"  - {field}")
                    
        except Exception as e:
            print(f"{Fore.RED}✗ API check failed: {e}{Style.RESET_ALL}")
            
    def validate_data_consistency(self):
        """Check if data is consistent across layers"""
        print(f"\n{Fore.YELLOW}3️⃣  DATA CONSISTENCY CHECK{Style.RESET_ALL}")
        print("-" * 40)
        
        inconsistencies = []
        
        # Compare queue_service vs admin_manager
        if 'queue_service' in self.results and 'admin_manager' in self.results:
            qs_completed = self.results['queue_service'].get('completed_today')
            am_completed = self.results['admin_manager'].get('completed_today')
            
            if qs_completed != am_completed:
                inconsistencies.append({
                    'field': 'completed_today',
                    'queue_service': qs_completed,
                    'admin_manager': am_completed
                })
                
        # Compare admin_manager vs api_response
        if 'admin_manager' in self.results and 'api_response' in self.results:
            am_completed = self.results['admin_manager'].get('completed_today')
            api_completed = self.results['api_response']['queue'].get('completed_today')
            
            if am_completed != api_completed:
                inconsistencies.append({
                    'field': 'completed_today',
                    'admin_manager': am_completed,
                    'api_response': api_completed
                })
                
        if inconsistencies:
            print(f"{Fore.RED}❌ Found {len(inconsistencies)} inconsistencies:{Style.RESET_ALL}")
            for inc in inconsistencies:
                print(f"\n  Field: {inc['field']}")
                for key, value in inc.items():
                    if key != 'field':
                        print(f"    {key}: {value}")
        else:
            print(f"{Fore.GREEN}✅ All data is consistent across layers!{Style.RESET_ALL}")
            
    def generate_report(self):
        """Generate final report with what UI should show"""
        print(f"\n{Fore.YELLOW}4️⃣  FINAL REPORT - WHAT UI SHOULD SHOW{Style.RESET_ALL}")
        print("-" * 40)
        
        if 'api_response' in self.results:
            queue = self.results['api_response']['queue']
            jobs = self.results['api_response']['jobs']
            
            completed_today = queue.get('completed_today', 0)
            failed_today = queue.get('failed_today', 0)
            total_today = jobs.get('total_today', 0)
            success_rate = jobs.get('success_rate', 0)
            
            print(f"\n{Fore.CYAN}📊 Dashboard 'Today's Jobs' Card Should Show:{Style.RESET_ALL}")
            print(f"  Title: Today's Jobs")
            print(f"  Value: {total_today}")
            print(f"  Description: {success_rate:.0f}% success ({completed_today}/{total_today} completed today)")
            
            print(f"\n{Fore.CYAN}📊 Expected vs Actual:{Style.RESET_ALL}")
            
            # Create comparison table
            table_data = [
                ["Metric", "Backend Says", "API Returns", "UI Should Show", "Status"],
                ["Completed Today", 
                 self.results.get('database', {}).get('today_completed', '?'),
                 completed_today,
                 f"{completed_today}/{total_today}",
                 "✅" if completed_today == self.results.get('database', {}).get('today_completed', 0) else "❌"],
                ["Failed Today",
                 self.results.get('database', {}).get('today_failed', '?'),
                 failed_today,
                 failed_today,
                 "✅" if failed_today == self.results.get('database', {}).get('today_failed', 0) else "❌"],
                ["Success Rate",
                 f"{self.calculate_success_rate()}%",
                 f"{success_rate}%",
                 f"{success_rate}%",
                 "✅" if abs(success_rate - self.calculate_success_rate()) < 1 else "❌"]
            ]
            
            print(tabulate(table_data, headers="firstrow", tablefmt="grid"))
            
            # Save results to file
            self.save_results()
            
    def calculate_success_rate(self):
        """Calculate what success rate should be"""
        if 'database' in self.results:
            completed = self.results['database'].get('today_completed', 0)
            failed = self.results['database'].get('today_failed', 0)
            total_finished = completed + failed
            if total_finished > 0:
                return round((completed / total_finished) * 100)
        return 0
        
    def save_results(self):
        """Save validation results to file"""
        filename = f"dashboard_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        print(f"\n{Fore.GREEN}📁 Results saved to: {filename}{Style.RESET_ALL}")

def main():
    validator = DashboardValidator()
    validator.run_full_validation()
    
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}To test UI display, open your browser and check if it matches above values")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")

if __name__ == "__main__":
    main()
