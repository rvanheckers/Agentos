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

        # Initialize enforcer
        enforcer = SmartConstraintEnforcer("../")
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

        # Show top 5 largest files
        print("📁 Largest files:")
        files_sorted = sorted(
            [(k, v) for k, v in status['files'].items()
             if isinstance(v.get('lines'), int)],
            key=lambda x: x[1]['lines'],
            reverse=True
        )[:5]

        for file_path, file_info in files_sorted:
            level_icons = {'green': '🟢', 'yellow': '🟡', 'orange': '🟠', 'red': '🔴'}
            icon = level_icons.get(file_info['level'], '❓')
            lines = file_info['lines']
            print(f"   {icon} {file_path}: {lines:,} lines")

        print()
        print("✅ Report complete! Use this data to keep your code organized.")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're in the script-monitoring directory.")
    except Exception as e:
        print(f"❌ Error generating report: {e}")

if __name__ == "__main__":
    main()
