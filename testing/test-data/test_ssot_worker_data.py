#!/usr/bin/env python3
"""
SSOT Endpoint Worker Data Test
=============================

Test SSOT endpoint om te bewijzen dat worker data nu echt is (niet mock).
"""

import requests
import json
from datetime import datetime

def test_ssot_worker_data():
    """Test SSOT endpoint voor worker data"""
    print("🔍 Testing SSOT Endpoint Worker Data")
    print("=" * 50)
    
    try:
        # Call SSOT endpoint
        response = requests.get("http://localhost:8001/api/admin/ssot", timeout=10)
        
        if response.status_code != 200:
            print(f"❌ SSOT endpoint failed: {response.status_code}")
            return False
        
        data = response.json()
        
        # Extract worker data
        dashboard = data.get('dashboard', {})
        workers_summary = dashboard.get('workers', {})
        worker_details = workers_summary.get('details', [])
        
        print(f"📊 SSOT Worker Summary:")
        print(f"   Total Workers: {workers_summary.get('total', 'N/A')}")
        print(f"   Active Workers: {workers_summary.get('active', 'N/A')}")
        print(f"   Idle Workers: {workers_summary.get('idle', 'N/A')}")
        print(f"   Offline Workers: {workers_summary.get('offline', 'N/A')}")
        print()
        
        # Analyze each worker
        mock_indicators = []
        real_indicators = []
        
        for i, worker in enumerate(worker_details, 1):
            worker_id = worker.get('worker_id', 'unknown')
            status = worker.get('status', 'unknown')
            current_tasks = worker.get('current_tasks', 0)
            total_completed = worker.get('total_tasks_completed', 0)
            pool_size = worker.get('pool_size', 'unknown')
            load_avg = worker.get('load_average', 0)
            memory = worker.get('memory_usage', 0)
            queues = worker.get('queues', [])
            
            print(f"📋 Worker {i}: {worker_id}")
            print(f"   Status: {status}")
            print(f"   Current Tasks: {current_tasks}")
            print(f"   Total Completed: {total_completed}")
            print(f"   Pool Size: {pool_size}")
            print(f"   Load Average: {load_avg}")
            print(f"   Memory Usage: {memory} MB")
            print(f"   Queues: {len(queues)} queues")
            
            # Detect if this is mock data
            is_mock = False
            reasons = []
            
            # Old mock data indicators
            if worker_id == "celery@Stormchaser" and current_tasks == 2 and total_completed == 147:
                is_mock = True
                reasons.append("Exact match with old hardcoded values")
            
            # Check for typical mock patterns
            if total_completed == 147 and current_tasks == 2 and load_avg == 0.65:
                is_mock = True
                reasons.append("Matches exact mock data pattern")
            
            # Real data indicators
            if pool_size != 'unknown' and isinstance(pool_size, int):
                real_indicators.append(f"Pool size is real integer: {pool_size}")
            
            if current_tasks == 0 and total_completed == 0:
                real_indicators.append("Zero values suggest real idle worker")
            
            if load_avg != 0.65 and memory != 45.2:
                real_indicators.append("Different from mock load/memory values")
            
            # Print analysis
            if is_mock:
                print(f"   ❌ MOCK DATA DETECTED!")
                for reason in reasons:
                    print(f"      • {reason}")
                mock_indicators.extend(reasons)
            else:
                print(f"   ✅ APPEARS TO BE REAL DATA")
            
            print()
        
        # Summary analysis
        print("🎯 ANALYSIS SUMMARY:")
        print("-" * 30)
        
        if mock_indicators:
            print("❌ MOCK DATA INDICATORS FOUND:")
            for indicator in mock_indicators:
                print(f"   • {indicator}")
        
        if real_indicators:
            print("✅ REAL DATA INDICATORS FOUND:")
            for indicator in real_indicators:
                print(f"   • {indicator}")
        
        if not mock_indicators and real_indicators:
            print("\n🎉 SUCCESS: Worker data appears to be REAL Celery data!")
            return True
        elif mock_indicators:
            print("\n⚠️  WARNING: Some mock data patterns detected")
            return False
        else:
            print("\n❓ UNCLEAR: Unable to determine data source definitively")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to SSOT API - is server running?")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_worker_data_changes():
    """Test if worker data changes over time (real data should fluctuate)"""
    print("\n🔄 Testing Worker Data Stability (Real vs Mock)")
    print("=" * 50)
    
    try:
        # Get data twice with a small delay
        import time
        
        print("📊 First reading...")
        response1 = requests.get("http://localhost:8001/api/admin/ssot")
        data1 = response1.json()
        worker1 = data1['dashboard']['workers']['details'][0]
        
        time.sleep(2)
        
        print("📊 Second reading (2 seconds later)...")
        response2 = requests.get("http://localhost:8001/api/admin/ssot")
        data2 = response2.json()
        worker2 = data2['dashboard']['workers']['details'][0]
        
        # Compare values
        fields_to_check = ['current_tasks', 'total_tasks_completed', 'load_average', 'memory_usage']
        
        changes_detected = False
        for field in fields_to_check:
            val1 = worker1.get(field, 0)
            val2 = worker2.get(field, 0)
            
            if val1 != val2:
                print(f"   📈 {field}: {val1} → {val2} (CHANGED)")
                changes_detected = True
            else:
                print(f"   📊 {field}: {val1} (same)")
        
        if changes_detected:
            print("\n✅ DATA CHANGES DETECTED - Likely real data!")
        else:
            print("\n⚠️  NO CHANGES DETECTED - Could be mock data or stable system")
            
        return changes_detected
        
    except Exception as e:
        print(f"❌ Change detection failed: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 SSOT Worker Data Verification Test")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test 1: Analyze current data
    data_test = test_ssot_worker_data()
    
    # Test 2: Check for changes over time
    change_test = test_worker_data_changes()
    
    # Final verdict
    print("\n" + "=" * 60)
    print("🏁 FINAL VERDICT:")
    
    if data_test is True:
        print("✅ Worker data is REAL Celery data via SSOT!")
    elif data_test is False:
        print("❌ Worker data appears to be MOCK data")
    else:
        print("❓ Data source unclear - manual inspection needed")
    
    if change_test:
        print("✅ Data shows dynamic behavior (good sign)")
    else:
        print("⚠️  Data appears static (could be mock or stable)")

if __name__ == "__main__":
    main()