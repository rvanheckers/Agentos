# AgentOS Script Monitoring System

Monitor voor codebase grootte en script complexiteit. Houdt 145+ bestanden in de gaten en waarschuwt voor te grote bestanden.

## 🚀 Snelle Start

```bash
# Ga naar script-monitoring directory
cd script-monitoring

# Run het monitoring rapport
python3 run_constraint_check.py
```

## 📁 Bestanden

- `run_constraint_check.py` - **GEBRUIK DEZE** voor dagelijks rapport
- `constraint_enforcer.py` - Core monitoring engine
- `vibecoder_limits.json` - Configuratielimieten
- `utils/file_utils.py` - File scanning utilities
- `test_constraint.py` - Test scripts

## 🎯 Features

- **145+ bestanden** gemonitoreerd (Python, JavaScript, JSON, TypeScript)
- **Alle AgentOS directories**: api/, services/, workers/, agents2/, ui-admin/, ui-v2/, etc.
- **Gradient systeem**: 🟢 groen → 🟡 geel → 🟠 oranje → 🔴 rood  
- **Configureerbare limieten** via JSON
- **Concrete aanbevelingen** voor refactoring
- **Blokkeert nieuwe code** bij rood niveau

## 📊 Gebruik

**Dagelijks rapport (aanbevolen):**
```bash
python3 run_constraint_check.py
```

**Programmatische toegang:**
```python
from constraint_enforcer import get_enforcer, enforce_constraints

# Check status
enforcer = get_enforcer('../')
status = enforcer.get_current_status()

# Check of actie is toegestaan
allowed = enforce_constraints("nieuwe feature toevoegen")
```

## ⚙️ Configuratie

Edit `vibecoder_limits.json` voor custom limieten:
- **base_lines**: 35,000 (waarschuwing niveau)
- **max_lines**: 45,000 (maximum project grootte)
- **file_limits**: Specifieke limieten per bestand

## 📈 Huidige Status

✅ **PRODUCTION READY** - Volledig geïmplementeerd voor AgentOS
- 36,000+ regels code gemonitoreerd
- 🟠 Oranje niveau (normale status voor groot project)
- Realtime feedback over codebase gezondheid