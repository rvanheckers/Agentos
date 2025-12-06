# Agent Contracts - Feature Implementation Specs

**Wat is dit?** Agent contracts zijn gedetailleerde specificaties voor het bouwen van nieuwe features. Elk contract bevat exacte INPUT/OUTPUT definities, Context7 validatie, en acceptance criteria.

---

## 📋 Active Contracts

### 🔍 [job-debug-viewer/](./job-debug-viewer/)
**Status:** 🟡 Ready for implementation
**Priority:** MEDIUM
**Estimated Time:** 6-8 hours

**Doel:** Visuele debug interface waar je per stap van de video processing pipeline kunt zien:
- ✅ Of de stap succesvol was
- 📊 Het resultaat (thumbnails, transcripts, video previews)
- ⚙️ Welke settings gebruikt zijn
- ❌ Errors met context

**Voor wie:** Vibecoders die zonder code willen debuggen en configureren.

**Key Deliverables:**
- Database migration voor `step_outputs` JSON column
- API endpoint `GET /api/jobs/{id}/debug`
- Updated Celery tasks (download, transcribe, detect moments, etc.)
- Frontend `job-debug.html` page met visual previews
- Helper functions (thumbnail generation, face screenshots)

**Dependencies:** None - can start immediately

**Documentation:**
- [📄 Contract Details](./job-debug-viewer/JOB_DEBUG_VIEWER.md)
- [📖 Project README](./job-debug-viewer/README.md)

---

## 📁 Completed Projects

### ✅ [completed-moment-selection/](./completed-moment-selection/)
**Completion Date:** October 2025
**Status:** ✅ Deployed & Working

**Feature:** User Moment Selection Workflow (2-Phase Pipeline)

Implementatie van een systeem waar gebruikers kunnen kiezen welke viral moments ze willen omzetten naar clips, in plaats van automatisch alle moments te verwerken.

**Agents:**
1. Backend API (AGENT_1) - REST endpoints voor moments ophalen en selecteren
2. Frontend UI (AGENT_2) - Moment selector interface
3. Workflow Splitter (AGENT_3) - Phase 1/2 workflow opsplitsing
4. Database Schema (AGENT_4) - Moment table + job.phase tracking
5. Integration (AGENT_5) - Complete end-to-end integratie

**Resultaat:**
- ✅ Phase 1 analyseert video en detecteert moments
- ✅ Job pauzeert bij "awaiting_selection"
- ✅ Frontend toont moments met viral scores
- ✅ User selecteert gewenste moments
- ✅ Phase 2 genereert alleen geselecteerde clips

[→ Zie completed-moment-selection/README.md voor details](./completed-moment-selection/README.md)

---

## 🎯 Hoe Agent Contracts Werken

### Contract Structuur

Elk agent contract bevat:

#### 1. **📥 INPUT FILES**
Exacte lijst van files die je moet **lezen** om de feature te begrijpen:
```markdown
📥 INPUT FILES
- core/database_manager.py (begrijp Job model)
- api/routes/jobs.py (begrijp API patterns)
- tasks/video_processing.py (begrijp workflow)
```

#### 2. **📤 OUTPUT (Deliverables)**
Exacte lijst van files die je moet **maken/updaten** met volledige code voorbeelden:
```markdown
📤 OUTPUT
1. Database Migration
   File: migrations/005_add_debug_outputs.sql
   [Complete SQL code]

2. API Endpoint
   File: api/routes/debug.py (NEW)
   [Complete Python code]
```

#### 3. **🔍 PROACTIVE CONTEXT7 METHODOLOGY**
Verplichte 3-fase validatie:
- **PHASE 1: BEFORE** - Research best practices via Context7
- **PHASE 2: DURING** - Validate approach tijdens implementatie
- **PHASE 3: AFTER** - Self-check met 8/10 quality target

#### 4. **✅ ACCEPTANCE CRITERIA**
Checklist om te valideren dat feature compleet is.

#### 5. **🧪 HOE TE TESTEN**
Stap-voor-stap test instructies.

---

## 🚀 Een Contract Gebruiken

### Voor een Agent (Claude in andere terminal):

```bash
# 1. Lees het contract
cat agent_contracts/JOB_DEBUG_VIEWER.md

# 2. Volg de INPUT FILES sectie
# Lees elk genoemd bestand om context te krijgen

# 3. Implementeer de OUTPUT (Deliverables)
# Maak/update elk genoemd bestand met de gegeven code

# 4. Valideer met Context7
# PHASE 1: Research (voor je begint)
# PHASE 2: Validate (tijdens implementatie)
# PHASE 3: Self-check (8/10 target voor submission)

# 5. Test volgens HOE TE TESTEN
# Volg de test stappen exact

# 6. Checklist ACCEPTANCE CRITERIA
# Vink alles af voordat je klaar bent
```

### Voor een Mens:

Het contract is ook een **technische specificatie** die je kunt volgen. Elk OUTPUT bestand heeft volledige code voorbeelden die je kunt copy-pasten en aanpassen.

---

## 📊 Contract Status Tracking

| Contract | Status | Priority | Estimated | Started | Completed |
|----------|--------|----------|-----------|---------|-----------|
| [job-debug-viewer/](./job-debug-viewer/) | 🟡 Ready | MEDIUM | 6-8h | - | - |
| [completed-moment-selection/](./completed-moment-selection/) | ✅ Done | HIGH | 12-14h | Oct 2025 | Oct 2025 |

---

## 💡 Tips

### Voor Contract Makers:
- ✅ **Wees specifiek**: Geen "update de database", maar "add Column X to Table Y"
- ✅ **Geef volledige code**: Geen pseudocode, echte working code
- ✅ **Definieer INPUT**: Wat moet gelezen worden om feature te snappen?
- ✅ **Definieer OUTPUT**: Wat moet gemaakt/geupdate worden?
- ✅ **Context7 integreren**: Verplicht 3-fase validation
- ✅ **Testbaar maken**: Exacte test stappen opnemen

### Voor Contract Executors (Agents):
- ✅ **Lees ALLES eerst**: Vooral INPUT FILES en DOEL
- ✅ **Context7 VERPLICHT**: Gebruik het in alle 3 fases
- ✅ **Self-check eerst**: Haal 8/10 voordat je submit
- ✅ **Test grondig**: Volg HOE TE TESTEN exact
- ✅ **Checklist afvinken**: ACCEPTANCE CRITERIA = definition of done

---

## 📚 Referenties

- **Contract Template:** [template/](./template/) - Standaard template voor nieuwe agent contracts
- **Agent Template:** `.claude/agents/TEMPLATE.md` - Template voor herbruikbare agents
- **Completed Example:** `completed-moment-selection/` - Zie hoe een volledig project eruitziet
- **Project Context:** Zie [PROJECT_CONTEXT.md](../docs/PROJECT_CONTEXT.md) indien beschikbaar

---

**Laatst bijgewerkt:** 2025-10-16
**Actieve Contracts:** 1
**Completed Projects:** 1
