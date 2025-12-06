# 🤖 Agent Configuraties

Deze directory bevat de **concrete agent prompt files** die je kunt gebruiken in Claude Code.

## 📁 Structuur

```
agent_configs/
├── README.md                    ← Dit bestand
├── 1_security_agent.md          ← SecurityAgent (EERST!) ✅ COMPLEET
├── 2_profile_agent.md           ← ProfileAgent (NA security) ✅ COMPLEET
├── 3_face_detect_agent.md       ← FaceDetectAgent (implementatie) ✅ COMPLEET
├── 4_quality_agent.md           ← QualityAgent (ALTIJD actief!) ✅ COMPLEET
└── 5_integration_agent.md       ← IntegrationAgent (LAATSTE) ✅ COMPLEET
```

## 🚀 Hoe Te Gebruiken

### **Optie A: Claude Code .claude/agents/ (Aanbevolen)**

Kopieer deze bestanden naar `.claude/agents/`:

```bash
cd /mnt/c/Users/rober/OneDrive/Bureaublad/Projecten/01_Active_Development/AgentOS

# Maak agents directory
mkdir -p .claude/agents

# Kopieer alle agent configs
cp simple_refactor_plan/agent_configs/*.md .claude/agents/
```

Gebruik in Claude Code:
```
@security_agent Implement SECURITY_FIRST.md
@quality_agent Review security implementation
```

### **Optie B: Handmatige Prompts**

Open een agent file en kopieer de prompt naar Claude Code chat.

---

## 📊 Agent Volgorde

**KRITIEK: Volg deze volgorde!**

```
1️⃣ SecurityAgent     → Implement security layer
   └─ QualityAgent   → Validate (score 8+/10)

2️⃣ ProfileAgent      → Setup profiling tools
   └─ QualityAgent   → Validate approach

3️⃣ FaceDetectAgent   → Implement face detection v2
   └─ QualityAgent   → Validate implementation

4️⃣ IntegrationAgent  → Test everything together
   └─ QualityAgent   → Final review
```

**QualityAgent is ALTIJD aanwezig bij elke stap!**

---

## 🔧 MCP Connecties Per Agent

| Agent | Context7 | Andere MCP | Tools |
|-------|----------|------------|-------|
| SecurityAgent | ✅ VERPLICHT | - | python-magic, pytest |
| ProfileAgent | ✅ VERPLICHT | - | py-spy, Scalene, memray |
| FaceDetectAgent | ✅ VERPLICHT | - | mediapipe, ultralytics |
| QualityAgent | ✅ PRIMAIR | - | Context7 alleen |
| IntegrationAgent | ✅ VERPLICHT | - | pytest |

**Context7 is VERPLICHT voor alle agents!**

---

## ✅ Success Criteria

Elk agent bestand bevat:
- ✅ Duidelijke taak beschrijving
- ✅ Context7 integratie instructies
- ✅ Concrete deliverables
- ✅ Success criteria
- ✅ Prompt voor proactief Context7 gebruik

---

**START HIER:** Open `1_security_agent.md` →