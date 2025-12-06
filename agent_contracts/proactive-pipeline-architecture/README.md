# Proactive Pipeline Architecture Refactor

Deze directory bevat drie agent contracts die samen de AgentOS video processing pipeline transformeren van een **reactieve** naar een **proactieve** architectuur.

---

## 📦 Contracts Overzicht

### 1. [PROACTIVE_PIPELINE_BACKEND.md](./PROACTIVE_PIPELINE_BACKEND.md)
**Focus:** Infrastructuur & State Management
**Priority:** HIGH
**Estimated Time:** 2 uur
**Dependencies:** Geen

**Bevat:**
- State Machine Definition (`core/pipeline_states.py`)
- Pipeline Control API (`api/routers/pipeline_control.py`)
- Database Schema Updates (`core/database_manager.py`)
- Context7 validatie voor backend patterns
- API testing procedures

**Key Deliverables:**
- `PipelinePhase` enum met alle states (CONFIGURING, AWAITING_ADMIN_CONFIG, etc.)
- REST API endpoints voor pipeline control
- JSONB `pipeline_config` column voor flexible configuration storage
- Database migration scripts

---

### 2. [PROACTIVE_PIPELINE_WORKFLOW.md](./PROACTIVE_PIPELINE_WORKFLOW.md)
**Focus:** Pipeline Pause Points & Orchestration
**Priority:** HIGH
**Estimated Time:** 1.5 uur
**Dependencies:** Backend contract VOLLEDIG geïmplementeerd

**Bevat:**
- Phase 1 Workflow Updates (`tasks/video_processing_phase1.py`)
- Phase 2 Workflow Updates (`tasks/video_processing_phase2.py`)
- Pause Point Logic (waar pipeline stopt voor admin input)
- Celery Task Coordination
- Context7 validatie voor workflow orchestration
- End-to-end testing procedures

**Key Deliverables:**
- Phase 1 stopt bij `awaiting_admin_config` (geen auto-continue)
- Phase 1 results opgeslagen in `pipeline_config` voor admin review
- Backwards compatibility met User UI flow
- Integration tests voor pause/resume functionaliteit

---

### 3. [PRESET_SETTINGS_UI.md](./PRESET_SETTINGS_UI.md)
**Focus:** User-Friendly Settings Interface
**Priority:** MEDIUM
**Estimated Time:** 2 uur
**Dependencies:** Backend + Workflow contracts geïmplementeerd

**Bevat:**
- 3-Laags Settings Architectuur (Quick Presets / Essential / Expert Mode)
- UI/UX Design met exacte CSS (consistent met bestaande design)
- John Sugarman copywriting voor labels/tooltips
- Preset definitions (Talk Show, Podcast, Interview, Viral Shorts)
- Updates voor `job-debug.html` EN `index.html`
- Context7 validatie voor UI/UX best practices
- Mobile responsive design
- Accessibility (ARIA labels, keyboard navigation)

**Key Deliverables:**
- Quick Preset buttons (1-click configuratie)
- Begrijpelijke labels ("Hoe lang moet elke clip zijn?" ipv "Clip Length")
- Expert Mode toggle voor advanced users
- Design consistency met bestaande intent cards en buttons

---

## 🔄 Implementatie Volgorde

**BELANGRIJK:** Volg deze volgorde strikt om dependencies te respecteren.

### Week 1: Backend Foundation
```
Dag 1-2: PROACTIVE_PIPELINE_BACKEND.md
├── State Machine Definition
├── API Endpoints
├── Database Migration
└── Backend Testing
```

### Week 2: Workflow Integration
```
Dag 3-4: PROACTIVE_PIPELINE_WORKFLOW.md
├── Phase 1 Pause Point
├── Phase 2 Configuration
├── Backwards Compatibility
└── End-to-End Testing
```

### Week 3: UI/UX Polish
```
Dag 5-6: PRESET_SETTINGS_UI.md
├── Quick Presets
├── Essential Settings (begrijpelijke taal)
├── Expert Mode
└── User Testing
```

---

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                          USER UPLOADS VIDEO                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  STATE: CONFIGURING (NEW)                                        │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Admin kan Phase 1 configureren via Debug View (optioneel) │ │
│  │  - Max Moments: 5                                           │ │
│  │  - Face Confidence: 0.6                                     │ │
│  │  - OF: Gebruik preset "Talk Show"                          │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  STATE: PHASE1_RUNNING                                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  download_video → transcribe_audio → detect_moments →      │ │
│  │  detect_faces                                               │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  STATE: AWAITING_ADMIN_CONFIG (NEW) ⏸️ PAUSE POINT               │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Pipeline STOPT automatisch                                 │ │
│  │  Phase 1 Results getoond: 5 moments, 8 faces detected      │ │
│  │                                                             │ │
│  │  Admin kan nu:                                              │ │
│  │  ✅ Visual Crop Editor openen                               │ │
│  │  ✅ Clip length aanpassen                                   │ │
│  │  ✅ Crop method kiezen (auto/manual/face-focused)          │ │
│  │  ✅ OF: Gebruik preset "Podcast"                           │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  STATE: AWAITING_USER_SELECTION (of admin override)             │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  User kiest moments via User UI                             │ │
│  │  OF admin selecteert all moments (voor testing)             │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  STATE: PHASE2_RUNNING                                           │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  intelligent_crop → cut_videos                              │ │
│  │  (gebruikt admin-gekozen settings)                          │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  STATE: COMPLETED ✅                                              │
│  Clips klaar voor download                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Probleemstelling & Oplossing

### ❌ HUIDIGE SITUATIE (Reactief - Verkeerd)
```
User uploadt video
    → Pipeline draait volledig door (geen controle)
    → Admin kan achteraf via re-run fixen
    → ⚠️ Verspilde resources, suboptimale resultaten
```

### ✅ NIEUWE SITUATIE (Proactief - Goed)
```
User uploadt video
    → Phase 1 analyseert (gather info)
    → Pipeline PAUZEERT ⏸️
    → Admin configureert/past aan via Debug View
    → Phase 2 draait met gekozen settings
    → ✨ Efficiënt, optimale resultaten vanaf eerste run
```

---

## 🧪 Testing Strategy

### 1. Backend Testing (na BACKEND contract)
```bash
# Test state machine transitions
pytest tests/test_pipeline_states.py

# Test API endpoints
pytest tests/test_pipeline_control_api.py

# Test database migrations
pytest tests/test_pipeline_config_storage.py
```

### 2. Workflow Testing (na WORKFLOW contract)
```bash
# Test Phase 1 pause point
pytest tests/test_phase1_pause.py

# Test backwards compatibility
pytest tests/test_user_ui_flow.py

# Integration test: full pipeline with admin intervention
pytest tests/test_admin_pipeline_flow.py
```

### 3. UI Testing (na UI contract)
```bash
# Manual testing in browser
open http://localhost:8001/ui-v2/job-debug.html?job=test-job-id

# Check preset buttons functionality
# Check expert mode toggle
# Check mobile responsiveness
```

---

## 📊 Success Criteria

**Backend Contract:**
- [ ] `PipelinePhase` enum exists met alle states
- [ ] API endpoints `/configure-phase1`, `/start-phase1`, etc. werken
- [ ] Database migration succesvol zonder data loss
- [ ] Backwards compatible met bestaande jobs

**Workflow Contract:**
- [ ] Phase 1 stopt bij `awaiting_admin_config` (geen auto-continue)
- [ ] Admin kan Phase 2 configureren met Phase 1 results
- [ ] User UI flow werkt identiek (backwards compatible)
- [ ] Visual Crop Editor toegankelijk tijdens config phase

**UI Contract:**
- [ ] Quick Presets werken (Talk Show, Podcast, etc.)
- [ ] Begrijpelijke labels (geen jargon)
- [ ] Expert Mode toont advanced settings
- [ ] Design consistent met bestaande UI (button sizes, colors)
- [ ] Mobile responsive
- [ ] Accessible (keyboard navigation, screen readers)

---

## 🚨 Kritieke Afhankelijkheden

**Backend → Workflow:**
- Workflow contract VEREIST dat backend volledig werkend is
- `pipeline_config` column moet bestaan in database
- API endpoints moeten beschikbaar zijn
- State machine enums moeten geïmporteerd kunnen worden

**Workflow → UI:**
- UI contract VEREIST dat pause points werken
- Pipeline moet daadwerkelijk stoppen bij `awaiting_admin_config`
- Phase 1 results moeten beschikbaar zijn in `pipeline_config`

**Kritieke Volgorde:**
```
BACKEND (dag 1-2)
    ↓ VOLLEDIG KLAAR
WORKFLOW (dag 3-4)
    ↓ VOLLEDIG KLAAR
UI (dag 5-6)
```

⚠️ **NIET parallel werken** - elke fase moet 100% af voordat de volgende start!

---

## 💡 Design Philosophy

### Voor Regular Users (80%)
- Auto-flow blijft werken (backwards compatible)
- Geen breaking changes
- Zero learning curve

### Voor Admin Users (15%)
- Quick Presets voor snelle workflows
- Essential Settings met begrijpelijke taal
- Expert Mode voor fine-tuning

### Voor Expert Users (5%)
- Volledige controle via Expert Mode
- Alle raw parameters toegankelijk
- Advanced features niet verstopt

---

## 📚 Referenties

### Internal Documentation
- [DEBUG_VIEWER_V2.md](../job-debug-viewer/DEBUG_VIEWER_V2.md) - Debug viewer requirements
- [SETTINGS_INVENTORY.md](../job-debug-viewer/SETTINGS_INVENTORY.md) - Alle beschikbare config settings
- [INVENTORY.md](../INVENTORY.md) - Config variables inventory

### Code Files
- `tasks/video_processing.py` - Huidige pipeline flow
- `core/database_manager.py` - Job model en database schema
- `ui-v2/job-debug.html` - Debug viewer frontend
- `ui-v2/index.html` - User UI frontend

### External Documentation
- Context7: Celery workflow orchestration
- Context7: FastAPI async patterns
- Context7: React/Vue state management (voor toekomstige React refactor)

---

## 🔧 Maintenance

**Eigenaar:** AgentOS Core Team
**Laatste Update:** 2025-10-17
**Status:** In Development

**Contact voor vragen:**
- Backend: [Backend Team]
- Workflow: [Pipeline Team]
- UI/UX: [Frontend Team]

---

**Ready to start?** Begin met [PROACTIVE_PIPELINE_BACKEND.md](./PROACTIVE_PIPELINE_BACKEND.md)!