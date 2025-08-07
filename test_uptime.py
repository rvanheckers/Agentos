#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from services.admin_data_manager import AdminDataManager

def main():
    print("🔍 Testing uptime implementation...")
    
    manager = AdminDataManager()
    
    # Test _get_system_health directly
    system_health = manager._get_system_health()
    print(f"📊 _get_system_health() returned:")
    print(f"  - uptime: {system_health.get('uptime', 'MISSING')}")
    print(f"  - uptime_seconds: {system_health.get('uptime_seconds', 'MISSING')}")
    print(f"  - all keys: {list(system_health.keys())}")
    
if __name__ == "__main__":
    main()