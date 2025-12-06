# 📁 Simple Refactor Plan

## ✅ **Wat is dit?**
Simpele, duidelijke documenten voor AgentOS refactoring.
Geen ingewikkeld gedoe, gewoon wat echt moet gebeuren.

## 📚 **Documenten:**

### **📖 Refactor Strategy:**

1. **[START_HIER.md](./START_HIER.md)**
   - Begin hier! Overzicht van wat goed/slecht is
   - Concrete week planning
   - Belangrijke regels

2. **[SECURITY_FIRST.md](./SECURITY_FIRST.md)** ⚠️ **NIEUW - KRITIEK**
   - Video input validatie
   - Path sanitization (prevent attacks)
   - Resource limits (prevent DoS)
   - **LEES DIT EERST VOOR PRODUCTIE**

3. **[MEASURE_FIRST.md](./MEASURE_FIRST.md)** ✨ **UPDATED 2025**
   - Meet eerst wat traag/duur is
   - Moderne profiling tools (py-spy, Scalene)
   - Complete profiling script
   - Beslissen wat te fixen

4. **[FACE_DETECTOR_V2.md](./FACE_DETECTOR_V2.md)** ✨ **UPDATED 2025**
   - Concrete code om fake face detector te vervangen
   - Adaptive detection (MediaPipe + YOLO fallback)
   - Van mock → Production-ready
   - Copy-paste ready

5. **[CONTEXT7_VALIDATION_SUMMARY.md](./CONTEXT7_VALIDATION_SUMMARY.md)** ✅
   - Volledige Context7 validatie report
   - Voor/na vergelijking
   - Rating improvements

### **🤖 Claude Code Agents:**

6. **[CLAUDE_CODE_AGENTS.md](./CLAUDE_CODE_AGENTS.md)** 🤖 **NIEUW**
   - Welke agents je nodig hebt
   - Flowchart van responsibilities
   - Agent execution workflow
   - **START HIER voor agent-based refactoring**

7. **[agent_configs/](./agent_configs/)** 📁 **Agent Prompts** ✅ **COMPLEET**
   - `1_security_agent.md` - SecurityAgent prompt ✅
   - `2_profile_agent.md` - ProfileAgent prompt ✅
   - `3_face_detect_agent.md` - FaceDetectAgent prompt ✅
   - `4_quality_agent.md` - QualityAgent prompt ✅
   - `5_integration_agent.md` - IntegrationAgent prompt ✅

## 🚀 **Quick Start (10 minuten)**

```bash
# 1. Backup maken
cp -r AgentOS AgentOS_backup_$(date +%Y%m%d)

# 2. KRITIEK: Installeer security & profiling tools
pip install python-magic py-spy scalene memray

# 3. Meten wat traag is (2025 tools)
py-spy record -o profile.svg -- python task_chain.py test_video.mp4
scalene agents2/face_detection/face_detector_mediapipe.py

# 4. Kijk wat mock/fake is
grep -r "random.randint\|mock\|fake" agents2/

# 5. Implementeer security layer EERST (zie SECURITY_FIRST.md)

# 6. Fix de ergste agents (zie FACE_DETECTOR_V2.md)
```

## 📋 **Simpele Checklist (Context7 Validated ✅)**

- [ ] Backup gemaakt?
- [ ] **🔒 Security layer geïmplementeerd?** (KRITIEK!)
- [ ] Moderne profiling tools geïnstalleerd? (py-spy, Scalene)
- [ ] Gemeten wat traag is met py-spy?
- [ ] Mock agents geïdentificeerd?
- [ ] Face detector gefixed met adaptive strategy?
- [ ] Error handling toegevoegd aan subprocess calls?
- [ ] Getest of alles nog werkt?

## ⚠️ **Belangrijke Regel**

**OUDE CODE BLIJFT STAAN**

```
face_detector.py      ← blijft (oude)
face_detector_v2.py   ← nieuw (naast oude)
```

## ❌ **NIET Nodig**

- Geen CQRS
- Geen Event Sourcing
- Geen Kubernetes
- Geen complex architecture
- Geen alles tegelijk

## ✅ **WEL Nodig**

- Meten eerst
- Een ding tegelijk
- Testen na elke change
- Simpel houden

---

**Start met:** Open [START_HIER.md](./START_HIER.md)