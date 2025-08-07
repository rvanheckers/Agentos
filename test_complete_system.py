#!/usr/bin/env python3
import sys
import os
import requests
import json
sys.path.insert(0, os.path.abspath('.'))

def test_system_health_flow():
    print("🧪 Testing complete System Health flow...")
    
    # Test 1: Direct AdminDataManager
    print("\n1️⃣ Testing AdminDataManager._get_system_health()...")
    from services.admin_data_manager import AdminDataManager
    manager = AdminDataManager()
    system_health = manager._get_system_health()
    print(f"   ✅ Direct call - uptime: {system_health.get('uptime')}")
    print(f"   ✅ Direct call - uptime_seconds: {system_health.get('uptime_seconds')}")
    
    # Test 2: API endpoint
    print("\n2️⃣ Testing API endpoint /api/admin/ssot...")
    try:
        response = requests.get('http://localhost:8001/api/admin/ssot', timeout=10)
        if response.status_code == 200:
            data = response.json()
            dashboard_system = data.get('dashboard', {}).get('system', {})
            print(f"   ✅ API endpoint - uptime: {dashboard_system.get('uptime', 'MISSING')}")
            print(f"   ✅ API endpoint - uptime_seconds: {dashboard_system.get('uptime_seconds', 'MISSING')}")
            print(f"   ✅ API endpoint - all system keys: {list(dashboard_system.keys())}")
        else:
            print(f"   ❌ API endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ API endpoint error: {e}")
    
    # Test 3: Frontend transformation simulation
    print("\n3️⃣ Testing frontend transformation logic...")
    
    # Simulate Dashboard.js transformSystemHealthData
    def transform_system_health_data(system_health, system_control=None):
        try:
            if not system_health and not system_control:
                return None
                
            # Get overall system status
            overall_status = 'healthy'
            if system_health:
                services = ['api_status', 'database_status', 'redis_status', 'websocket_status']
                unhealthy_services = [service for service in services 
                                    if system_health.get(service) and system_health.get(service) != 'healthy']
                if unhealthy_services:
                    overall_status = 'degraded'
            
            # Get uptime from system health data (industry standard backend calculation)
            uptime = system_health.get('uptime', 'N/A') if system_health else 'N/A'
            
            return {
                'status': overall_status,
                'uptime': uptime,
                'cpu_usage': system_health.get('cpu_usage', 0) if system_health else 0,
                'memory_usage': system_health.get('memory_usage', 0) if system_health else 0,
                'disk_usage': system_health.get('disk_usage', 0) if system_health else 0,
                'services': {
                    'api': system_health.get('api_status', 'unknown') if system_health else 'unknown',
                    'database': system_health.get('database_status', 'unknown') if system_health else 'unknown',
                    'redis': system_health.get('redis_status', 'unknown') if system_health else 'unknown',
                    'websocket': system_health.get('websocket_status', 'unknown') if system_health else 'unknown'
                }
            }
        except Exception as error:
            print(f"Failed to transform system health data: {error}")
            return None
    
    # Test transformation with real data
    if 'dashboard_system' in locals():
        transformed = transform_system_health_data(dashboard_system)
        if transformed:
            print(f"   ✅ Frontend transformation - uptime: {transformed.get('uptime')}")
            print(f"   ✅ Frontend transformation - status: {transformed.get('status')}")
        else:
            print(f"   ❌ Frontend transformation failed")
    
    print("\n🎯 System Health flow test complete!")

if __name__ == "__main__":
    test_system_health_flow()