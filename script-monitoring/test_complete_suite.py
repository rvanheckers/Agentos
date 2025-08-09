#!/usr/bin/env python3
"""
Complete Script Monitoring Suite Test - Debug version
"""
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

def main():
    try:
        from constraint_enforcer import SmartConstraintEnforcer
        
        print("🎯 AGENTOS COMPLETE SCRIPT MONITORING SUITE TEST")
        print("=" * 60)
        
        # Initialize enforcer
        enforcer = SmartConstraintEnforcer("../")
        print("✅ Enforcer initialized")
        
        status = enforcer.get_current_status()
        print("✅ Status retrieved")
        
        # Basic info
        total = status.get("total_lines", 0)
        files_count = len(status.get('files', {}))
        level = status.get("enforcement_level", "unknown")
        icon = status.get("enforcement_icon", "❓")
        
        print(f"\n📊 Overall Status: {icon} {level.upper()}")
        print(f"📈 Total Python lines: {total:,}")
        print(f"📁 Files exceeding limits: {files_count}")
        
        # Files by type
        files_by_type = {}
        for file_path, file_info in status.get('files', {}).items():
            if isinstance(file_info.get('lines'), int):
                file_type = file_info.get('file_type', 'PY')
                if file_type not in files_by_type:
                    files_by_type[file_type] = []
                files_by_type[file_type].append((file_path, file_info))
        
        print(f"\n📁 Files by type:")
        type_icons = {'PY': '🐍', 'JS': '📜', 'TS': '🔷', 'CSS': '🎨', 'HTML': '🌐', 
                     'JSON': '📋', 'YAML': '⚙️', 'YML': '⚙️', 'TSX': '⚛️', 'VUE': '💚'}
        
        for file_type in sorted(files_by_type.keys()):
            files = sorted(files_by_type[file_type], key=lambda x: x[1]['lines'], reverse=True)
            icon = type_icons.get(file_type, '📄')
            print(f"\n  {icon} {file_type} ({len(files)} files):")
            
            for file_path, file_info in files[:5]:  # Top 5 per type
                level_icons = {'green': '🟢', 'yellow': '🟡', 'orange': '🟠', 'red': '🔴'}
                status_icon = level_icons.get(file_info.get('level', 'yellow'), '❓')
                lines = file_info.get('lines', 0)
                limit = file_info.get('limit', 0)
                print(f"    {status_icon} {file_path}: {lines:,} lines (limit: {limit})")
            
            if len(files) > 5:
                print(f"    ... and {len(files) - 5} more {file_type} files")
        
        print(f"\n✅ Complete suite test successful!")
        print(f"   Total types monitored: {len(files_by_type)}")
        print(f"   Total files over limits: {files_count}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()