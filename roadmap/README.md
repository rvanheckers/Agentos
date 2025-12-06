# 📋 Roadmap Management System

Deze directory bevat alle roadmap-gerelateerde bestanden voor AgentOS.

## 📁 Bestandsstructuur

```
roadmap/
├── README.md                    # Deze file - uitleg van het systeem
├── ROADMAP_VALIDATED.md        # 🔴 SOURCE OF TRUTH - Strategic roadmap (CLEAN)
├── roadmap_validated.json      # 🤖 AUTO-GENERATED - JSON export voor AI
├── technical_specs/            # 🔧 TECHNISCHE SPECIFICATIES (FORCED READ)
│   ├── phase_1_audio_chunking.json     # Alle code snippets, env vars, tests
│   ├── pipeline_guard_spec.json        # Pipeline guard implementatie details
│   └── phase_2_ui_integration.json     # UI integration specifications
├── md_to_json_converter.py     # 🔄 Conversie script MD → JSON
├── validate_sync.py            # ✅ Validatie script voor sync check
└── templates/                  # 📝 Templates voor nieuwe roadmaps
    ├── roadmap_template.md
    └── handover_template.json
```

## 🔄 Workflow

### 1. **MD is Leading (Strategic Level)**
- `ROADMAP_VALIDATED.md` is de **source of truth** voor strategy/overzicht
- Bevat **alleen** high-level beschrijving + verwijzingen naar technical specs
- Technische details staan in `technical_specs/*.json` files

### 2. **Technical Specs (Implementation Level)**
- `technical_specs/` bevat **alle** exacte implementatie details
- Code snippets, env variables, test commands, success criteria
- **VERPLICHTE** reading voor AI - roadmap verwijst naar deze files

### 3. **Automatische Conversie**
```bash
# Update JSON vanuit MD
python roadmap/md_to_json_converter.py

# Check of bestanden in sync zijn
python roadmap/validate_sync.py
```

### 4. **AI Handover Generation (IMPROVED)**
```bash
# AI wordt GEDWONGEN om technical specs te lezen
python ai_handover_generator.py \
  --primary="roadmap/roadmap_validated.json" \
  --secondary="roadmap/technical_specs/phase_1_audio_chunking.json,roadmap/technical_specs/pipeline_guard_spec.json" \
  --template="docs/BELANGRIJKE_PROMPT_AI_HANDOVER_GENERATOR.md"
```

## ⚠️ Belangrijke Regels

1. **NOOIT** direct de JSON editten
2. **ALTIJD** MD eerst updaten, dan script runnen
3. **TECHNISCHE DETAILS** gaan in `technical_specs/*.json`, NIET in MD
4. **ROADMAP MD** blijft clean - alleen strategy + verwijzingen
5. **CHECK** sync status voor commits
6. **VALIDEER** tegen actuele codebase

## 🎯 **Design Philosophy**

### **Problem**: Roadmaps worden technische monsters die niemand leest
### **Solution**: Gescheiden verantwoordelijkheden

- **📋 Roadmap MD**: Clean, strategic, management-friendly
- **🔧 Technical Specs**: Exacte implementatie details, AI-forced reading
- **🤖 AI Handover**: Combineert beide voor complete context

### **Result**:
- ✅ Developers zien clean roadmap overzicht
- ✅ AI wordt gedwongen alle technische details te lezen
- ✅ Implementatie details compleet en up-to-date
- ✅ Geen technische draak van een document

## 🚀 Quick Commands

```bash
# Auto-fix sync (recommended) - vanuit project root
python roadmap/validate_sync.py --auto-fix

# Full update cycle - vanuit roadmap directory
cd roadmap
python md_to_json_converter.py && python validate_sync.py

# Generate AI handover
cd .. && python ai_handover_generator.py --primary="roadmap/roadmap_validated.json"
```