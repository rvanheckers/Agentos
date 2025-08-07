#!/usr/bin/env python3
"""
Test script om constraint enforcer gebruiksvriendelijkheid te testen
"""

from constraint_enforcer import get_enforcer
import json

def test_constraint_suite():
    enforcer = get_enforcer('../')
    status = enforcer.get_current_status()

    print('🎯 CONSTRAINT ENFORCER STATUS RAPPORT')
    print('=' * 50)
    print(f'📊 Algemeen: {status["enforcement_icon"]} {status["enforcement_level"].upper()}')
    print(f'📈 Totaal: {status["total_lines"]}/{status["max_limit"]} regels ({status["total_usage_pct"]}%)')
    print(f'💡 Advies: {status["gradient_analysis"]["recommendation"]}')
    print()

    if status['violations']:
        print('⚠️  PROBLEMEN GEVONDEN:')
        for i, violation in enumerate(status['violations'], 1):
            print(f'   {i}. {violation}')
        print()

    print('📁 BESTAND STATUS (top 5 grootste):')
    files_sorted = sorted([(k,v) for k,v in status['files'].items() if isinstance(v.get('lines'), int)], 
                         key=lambda x: x[1]['lines'], reverse=True)[:5]
    for file_path, file_info in files_sorted:
        icons = {'green': '🟢', 'yellow': '🟡', 'orange': '🟠', 'red': '🔴'}
        icon = icons.get(file_info['level'], '❓')
        print(f'   {icon} {file_path}: {file_info["lines"]} regels')

    print()
    if status['enforcement_level'] != 'red':
        print('✅ GEBRUIKSVRIENDELIJKHEID: GOED - System klaar voor gebruik')
        return True
    else:
        print('❌ GEBRUIKSVRIENDELIJKHEID: PROBLEEM - Refactoring nodig')
        return False

if __name__ == "__main__":
    test_constraint_suite()