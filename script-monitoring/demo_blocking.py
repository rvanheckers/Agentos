#!/usr/bin/env python3
"""
Demo: Hoe constraint enforcer blokkeert bij red level
"""

from constraint_enforcer import enforce_constraints, get_enforcer

print('🧪 BLOCKING DEMO')
print('=' * 50)

# Simuleer red state door fake hoge line count
enforcer = get_enforcer('../')
original_get_current_status = enforcer.get_current_status

def fake_red_status():
    status = original_get_current_status()
    status['enforcement_level'] = 'red'
    status['total_lines'] = 5000  # Over de limiet
    return status

enforcer.get_current_status = fake_red_status

print('🔴 SIMULATIE: Project in RED state')
blocked = enforce_constraints('nieuwe code toevoegen')
print(f'Geblokkeerd: {not blocked}')
print()

print('💡 HOE HET WERKT:')
print('- 🟢 Green/Yellow/Orange: return True (toegestaan)')
print('- 🔴 Red: return False (GEBLOKKEERD)')
print('- Print waarschuwing naar console')
print('- Geen logs naar files (alleen console output)')