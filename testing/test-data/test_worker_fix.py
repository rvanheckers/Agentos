#!/usr/bin/env python3
"""
Test Worker Data Fix
===================

Direct test van QueueService om te zien of de fix werkt.
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('../..'))

from services.queue_service import QueueService

def test_worker_data_fix():
    """Test of worker data nu echt is"""
    print("🔍 Testing Worker Data Fix...")
    
    # Direct QueueService test
    queue_service = QueueService()
    workers = queue_service.get_workers_status(is_admin=True)
    
    print(f"\n📊 Found {len(workers)} workers:")
    
    for worker in workers:
        worker_id = worker.get('worker_id', 'unknown')
        status = worker.get('status', 'unknown')
        tasks = worker.get('current_tasks', 0)
        completed = worker.get('total_tasks_completed', 0)
        pool_size = worker.get('pool_size', 'unknown')
        
        print(f"\n📋 Worker: {worker_id}")
        print(f"   Status: {status}")
        print(f"   Current Tasks: {tasks}")
        print(f"   Total Completed: {completed}")
        print(f"   Pool Size: {pool_size}")
        
        # Analyze data source
        if worker_id == "celery@Stormchaser":
            print(f"   ❌ MOCK DATA DETECTED!")
            print(f"   🔧 QueueService still using old mock data")
        elif worker_id == "worker-offline":
            print(f"   ⚠️  FALLBACK DATA")
            print(f"   🔧 Celery workers not responding")
        elif worker_id.startswith("celery@") and "Stormchaser" not in worker_id:
            print(f"   ✅ REAL CELERY WORKER!")
            print(f"   🎯 Fix successful - using real data")
        else:
            print(f"   ❓ UNKNOWN DATA SOURCE")
        
        # Check for error field
        if 'error' in worker:
            print(f"   ⚠️  Error: {worker['error']}")

def main():
    """Main function"""
    try:
        test_worker_data_fix()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()