#!/usr/bin/env python3
"""
🧪 Jobs & Queue Testing Script
Hergebruikt bestaande Python test scripts om Jobs & Queue functionality te testen
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import subprocess
import requests
import json

def print_section(title):
    print(f"\n{'='*50}")
    print(f"🧪 {title}")
    print('='*50)

def test_jobs_queue_ssot():
    """Test SSOT endpoint specifiek voor Jobs & Queue data"""
    print_section("SSOT API - Jobs & Queue Data")
    
    try:
        response = requests.get("http://localhost:8001/api/admin/ssot", timeout=10)
        data = response.json()
        
        # Check jobs data
        jobs_data = data.get('dashboard', {}).get('jobs', {})
        recent_jobs = jobs_data.get('recent_jobs', [])
        print(f"✅ Recent jobs: {len(recent_jobs)} jobs found")
        
        # Check queue data 
        queue_data = data.get('dashboard', {}).get('queue', {})
        print(f"✅ Queue stats: {queue_data.get('pending', 0)} pending, {queue_data.get('processing', 0)} processing")
        
        # Check queue detail
        queue_detail = data.get('queue', {})
        job_history = queue_detail.get('job_history', [])
        print(f"✅ Job history: {len(job_history)} total jobs")
        
        # Test job structure
        if recent_jobs:
            job = recent_jobs[0]
            required_fields = ['id', 'status', 'created_at', 'progress']
            missing = [f for f in required_fields if f not in job]
            if not missing:
                print(f"✅ Job structure: All required fields present")
                print(f"   Sample: {job['id']} ({job['status']})")
            else:
                print(f"❌ Job structure: Missing {missing}")
        
        return True
        
    except Exception as e:
        print(f"❌ SSOT test failed: {e}")
        return False

def run_existing_tests():
    """Run bestaande test scripts die relevant zijn voor Jobs & Queue"""
    
    # Test SSOT performance (bevat queue data testing)
    print_section("SSOT Performance Test (includes Queue)")
    try:
        result = subprocess.run([
            sys.executable, "test_ssot_performance.py"
        ], cwd="../..", capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ SSOT Performance test passed")
            # Show relevant output
            lines = result.stdout.split('\n')
            for line in lines:
                if 'SSOT' in line or 'queue' in line.lower() or 'job' in line.lower():
                    print(f"   {line}")
        else:
            print(f"❌ SSOT Performance test failed")
            print(f"   Error: {result.stderr}")
    except Exception as e:
        print(f"❌ Could not run SSOT performance test: {e}")
    
    # Test database real data (bevat job creation & validation)
    print_section("Database Real Data Test (includes Jobs)")
    try:
        result = subprocess.run([
            sys.executable, "test_database_real_data.py"
        ], cwd="../..", capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✅ Database real data test passed")
            # Show relevant output
            lines = result.stdout.split('\n')
            for line in lines[-10:]:  # Last 10 lines for summary
                if line.strip():
                    print(f"   {line}")
        else:
            print(f"❌ Database real data test failed")
            print(f"   Error: {result.stderr}")
    except Exception as e:
        print(f"❌ Could not run database test: {e}")

def test_jobs_api_endpoints():
    """Test specifieke job API endpoints"""
    print_section("Jobs API Endpoints")
    
    endpoints = [
        "/api/jobs/today",
        "/api/queue/status", 
        "/api/analytics/jobs/stats",
        "/api/admin/ssot"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"http://localhost:8001{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✅ {endpoint}: HTTP {response.status_code}")
                if 'job' in endpoint.lower():
                    data = response.json()
                    if isinstance(data, list):
                        print(f"   📊 Found {len(data)} jobs")
                    elif isinstance(data, dict) and 'jobs' in str(data):
                        print(f"   📊 Response contains job data")
            else:
                print(f"❌ {endpoint}: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: {e}")

def test_admin_ui_integration():
    """Test admin UI integration voor Jobs & Queue view"""
    print_section("Admin UI Integration - Jobs & Queue")
    
    try:
        # Test admin UI accessibility
        response = requests.get("http://localhost:8004/", timeout=10)
        if response.status_code == 200:
            print("✅ Admin UI: Accessible")
            
            # Check if HTML contains queue-related elements
            html = response.text
            if 'queue' in html.lower() or 'jobs' in html.lower():
                print("✅ Admin UI: Contains queue/jobs references")
            else:
                print("⚠️  Admin UI: No queue/jobs references found")
        else:
            print(f"❌ Admin UI: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ Admin UI test failed: {e}")

def main():
    print("🧪 Jobs & Queue Test Suite")
    print("Hergebruikt bestaande AgentOS test scripts")
    print(f"Started at: {datetime.now()}")
    
    # Test 1: Custom Jobs & Queue SSOT test
    success_ssot = test_jobs_queue_ssot()
    
    # Test 2: API endpoints
    test_jobs_api_endpoints()
    
    # Test 3: Admin UI integration
    test_admin_ui_integration()
    
    # Test 4: Run bestaande relevante tests
    run_existing_tests()
    
    # Summary
    print_section("Test Summary")
    print(f"✅ SSOT Data Flow: {'PASS' if success_ssot else 'FAIL'}")
    print(f"✅ API Endpoints: Tested")
    print(f"✅ Admin UI: Tested") 
    print(f"✅ Integration: Via existing scripts")
    print(f"\n🎯 Jobs & Queue testing completed using existing AgentOS test infrastructure")

if __name__ == "__main__":
    from datetime import datetime
    main()