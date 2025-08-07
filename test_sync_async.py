#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from services.admin_data_manager import AdminDataManager
import asyncio

def main():
    print("🔍 Testing sync vs async AdminDataManager...")
    
    manager = AdminDataManager()
    
    # Test sync version (what API might use)
    print("\n📊 SYNC version (get_all_data_sync):")
    sync_data = manager.get_all_data_sync()
    print(f"  - total_today: {sync_data['dashboard']['jobs'].get('total_today', 'N/A')}")
    
    # Test async version  
    print("\n⚡ ASYNC version (get_all_data):")
    async def test_async():
        async_data = await manager.get_all_data()
        print(f"  - total_today: {async_data['dashboard']['jobs'].get('total_today', 'N/A')}")
        
    asyncio.run(test_async())
    
    # Test direct _get_jobs_summary
    print("\n🎯 DIRECT _get_jobs_summary:")
    jobs_direct = manager._get_jobs_summary()
    print(f"  - total_today: {jobs_direct.get('total_today', 'N/A')}")
    
if __name__ == "__main__":
    main()