#!/usr/bin/env python3
"""
Simple AgentOS Constraint Checker - Gewoon runnen en rapport krijgen
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

def main():
    try:
        from constraint_enforcer import SmartConstraintEnforcer

        print("🎯 AGENTOS SCRIPT SIZE MONITOR")
        print("=" * 50)

        # Initialize enforcer for entire AgentOS project from repository root
        project_root = Path(__file__).parent.parent  # Go up from script-monitoring to AgentOS root
        enforcer = SmartConstraintEnforcer(str(project_root))
        status = enforcer.get_current_status()

        # Show main status
        icon = status["enforcement_icon"]
        level = status["enforcement_level"].upper()
        total = status["total_lines"]
        limit = status["max_limit"]
        percentage = status["total_usage_pct"]

        print(f"📊 Status: {icon} {level}")
        print(f"📈 Code size: {total:,}/{limit:,} lines ({percentage}%)")
        print(f"📁 Files monitored: {len(status['files'])}")
        print()

        # Show recommendation
        print("💡 Recommendation:")
        print(f"   {status['gradient_analysis']['recommendation']}")
        print()

        # Show violations if any
        if status["violations"]:
            print(f"⚠️  Issues found ({len(status['violations'])}):")
            for i, violation in enumerate(status["violations"][:5], 1):
                print(f"   {i}. {violation}")
            if len(status["violations"]) > 5:
                print(f"   ... and {len(status['violations']) - 5} more")
            print()

        # Show files by type that exceed limits
        print("📁 Files exceeding limits by type:")

        # Group files by type - only include those exceeding limits
        files_by_type = {}
        for file_path, file_info in status['files'].items():
            lines = file_info.get('lines')
            limit = file_info.get('limit')
            if isinstance(lines, int) and isinstance(limit, int) and lines > limit:
                file_type = file_info.get('file_type', 'PY')
                if file_type not in files_by_type:
                    files_by_type[file_type] = []
                files_by_type[file_type].append((file_path, file_info))

        # Check if any files exceed limits
        if not files_by_type:
            print("   ✅ Geen overschrijdingen gevonden")
        else:
            # Show per type
            type_icons = {'PY': '🐍', 'JS': '📜', 'TS': '🔷', 'CSS': '🎨', 'HTML': '🌐',
                         'JSON': '📋', 'YAML': '⚙️', 'YML': '⚙️', 'TSX': '⚛️', 'VUE': '💚'}

            for file_type in sorted(files_by_type.keys()):
                files = sorted(files_by_type[file_type], key=lambda x: x[1]['lines'], reverse=True)
                icon = type_icons.get(file_type, '📄')
                print(f"\n   {icon} {file_type} Files:")

                for file_path, file_info in files[:3]:  # Top 3 per type
                    level_icons = {'green': '🟢', 'yellow': '🟡', 'orange': '🟠', 'red': '🔴'}
                    status_icon = level_icons.get(file_info['level'], '❓')
                    lines = file_info['lines']
                    limit = file_info['limit']
                    print(f"     {status_icon} {file_path}: {lines:,} lines (limit: {limit})")

                if len(files) > 3:
                    print(f"     ... and {len(files) - 3} more {file_type} files")

        print()
        print("✅ Report complete! Use this data to keep your code organized.")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're in the script-monitoring directory.")
    except Exception as e:
        print(f"❌ Error generating report: {e}")

if __name__ == "__main__":
    main()
