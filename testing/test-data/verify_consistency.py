#!/usr/bin/env python3
"""
Quick Consistency Verification Script
====================================

Snel script om te verificeren dat alle SSOT consumers nu consistent zijn.
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('../..'))

def test_consistency():
    """Test dat alle SSOT consumers hetzelfde getal geven"""
    print("🔍 Testing SSOT Consistency...")
    
    # Test 1: JobsService direct (SSOT)
    from services.jobs_service import JobsService
    jobs_service = JobsService()
    jobs_stats = jobs_service.get_job_statistics(is_admin=True)
    ssot_success_rate = jobs_stats.get('success_rate', 0)
    
    print(f"✅ SSOT (JobsService): {ssot_success_rate}%")
    
    # Test 2: DatabaseService (should now use SSOT)
    from api.services.database_service import DatabaseService
    db_service = DatabaseService()
    
    db_analytics = db_service.get_analytics_data()
    db_stats = db_service.get_stats()
    
    analytics_success_rate = db_analytics.get('success_rate', 0)
    stats_success_rate = db_stats.get('success_rate', 0)
    
    print(f"✅ DatabaseService.get_analytics_data(): {analytics_success_rate}%")
    print(f"✅ DatabaseService.get_stats(): {stats_success_rate}%")
    
    # Test 3: AdminDataManager (should use SSOT via services)
    from services.admin_data_manager import AdminDataManager
    admin_data = AdminDataManager()
    
    dashboard_data = admin_data.get_dashboard_data()
    jobs_data = dashboard_data.get('jobs', {})
    admin_success_rate = jobs_data.get('success_rate', 0)
    
    print(f"✅ AdminDataManager: {admin_success_rate}%")
    
    # Verify consistency
    all_rates = [ssot_success_rate, analytics_success_rate, stats_success_rate, admin_success_rate]
    
    if len(set(all_rates)) == 1:
        print(f"\n🎯 SUCCESS: All sources consistent at {ssot_success_rate}%")
        print("✅ Legacy bypasses successfully removed!")
        return True
    else:
        print(f"\n❌ INCONSISTENCY: Rates vary: {all_rates}")
        print("⚠️  Some legacy bypasses still exist")
        return False

def main():
    """Main function"""
    try:
        success = test_consistency()
        if success:
            print("\n🎉 SSOT Architecture is now fully consistent!")
            sys.exit(0)
        else:
            print("\n🔧 More work needed to achieve consistency")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()