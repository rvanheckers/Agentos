# Agent Contract Template

**Wat is dit?** Een standaard template voor het maken van nieuwe agent contracts die de kwaliteit en volledigheid van feature specifications waarborgt.

---

## 📋 Template Files

### [AGENT_CONTRACT_TEMPLATE.md](./AGENT_CONTRACT_TEMPLATE.md)
Volledige contract template met alle vereiste secties:

- **🎯 DOEL** - Wat wordt gebouwd en waarom
- **📥 INPUT FILES** - Welke files moeten gelezen worden voor context
- **📤 OUTPUT** - Exacte deliverables met volledige code voorbeelden
- **🔍 CONTEXT7 METHODOLOGY** - Verplichte 3-fase validatie (8/10 target)
- **✅ ACCEPTANCE CRITERIA** - Definition of done checklist
- **🧪 HOE TE TESTEN** - Stap-voor-stap test instructies
- **🚨 KRITIEKE PUNTEN** - Security, Performance, Error Handling
- **📊 IMPLEMENTATION CHECKLIST** - Fase-opdeling met tijdschatting

---

## 🚀 Hoe Het Template Te Gebruiken

### Voor Contract Makers

#### Stap 1: Kopieer Template
```bash
# Maak nieuwe feature directory
mkdir -p agent_contracts/my-new-feature

# Kopieer template
cp agent_contracts/template/AGENT_CONTRACT_TEMPLATE.md \
   agent_contracts/my-new-feature/MY_FEATURE_CONTRACT.md
```

#### Stap 2: Vul Alle Secties In

**Verplichte secties (MOET ingevuld):**
- [ ] `[FEATURE_NAME]` in titel
- [ ] **DOEL** - Complete beschrijving van wat en waarom
- [ ] **INPUT FILES** - Alle files die gelezen moeten worden
- [ ] **OUTPUT** - Alle deliverables met COMPLETE code (geen pseudocode!)
- [ ] **ACCEPTANCE CRITERIA** - Concrete, testbare criteria
- [ ] **HOE TE TESTEN** - Werkende test commando's

**Context7 integratie (VERPLICHT):**
- [ ] PHASE 1: BEFORE - Specifieke Context7 queries voor research
- [ ] PHASE 2: DURING - Validatie checkpoints tijdens implementatie
- [ ] PHASE 3: AFTER - Self-check criteria (8/10 minimum)

**Optionele maar aanbevolen secties:**
- KRITIEKE PUNTEN (Security, Performance, etc.)
- IMPLEMENTATION CHECKLIST (Fase opdeling)
- DEPENDENCIES (Wat is nodig, wat blokkeert dit?)
- EXTRA NOTES (Limitations, Future work, Design decisions)

#### Stap 3: Valideer Volledigheid

**Checklist voor contract kwaliteit:**
- [ ] Alle `[PLACEHOLDERS]` vervangen met concrete content
- [ ] CODE voorbeelden zijn COMPLEET en werkend (geen pseudocode)
- [ ] INPUT FILES bevatten uitleg WAT je eruit moet leren
- [ ] OUTPUT bevat ALLE files met complete code
- [ ] ACCEPTANCE CRITERIA zijn testbaar en specifiek
- [ ] TEST instructies zijn stap-voor-stap uitvoerbaar
- [ ] Context7 queries zijn specifiek en actionable
- [ ] Tijdschatting is realistisch per fase

#### Stap 4: Maak Project README

```bash
# Maak overview README voor de feature
touch agent_contracts/my-new-feature/README.md
```

**README moet bevatten:**
- Project overview (wat, waarom, voor wie)
- Architecture diagram/uitleg
- Key deliverables samenvatting
- Status en timeline
- Link naar volledige contract

#### Stap 5: Update Hoofdindex

Voeg je nieuwe contract toe aan `agent_contracts/README.md`:

```markdown
## 📋 Active Contracts

### 🔧 [my-new-feature/](./my-new-feature/)
**Status:** 🟡 Ready for implementation
**Priority:** HIGH
**Estimated Time:** 8-10 hours

[Korte beschrijving...]

**Documentation:**
- [📄 Contract Details](./my-new-feature/MY_FEATURE_CONTRACT.md)
- [📖 Project README](./my-new-feature/README.md)
```

---

## 📐 Template Structuur Rationale

### Waarom Deze Secties?

#### 🎯 DOEL
**Waarom:** Agent moet begrijpen WAT, WAAROM en VOOR WIE voordat code schrijven.
- Voorkomt mis-interpretatie
- Zorgt voor focus op daadwerkelijke business value
- Helpt prioritering begrijpen

#### 📥 INPUT FILES
**Waarom:** Context is cruciaal voor goede implementatie.
- Agent leest relevante code om patterns te begrijpen
- Voorkomt architectuur inconsistenties
- Hergebruikt bestaande utilities en patterns

#### 📤 OUTPUT (met complete code)
**Waarom:** Elimineer ambiguïteit, geef exact wat gebouwd moet worden.
- Geen pseudocode = geen verwarring
- Complete voorbeelden = snellere implementatie
- Copy-paste ready voor standaard delen

#### 🔍 CONTEXT7 METHODOLOGY
**Waarom:** Proactieve kwaliteitsborging via AI-assisted validation.
- **PHASE 1 (BEFORE)**: Leer best practices VOOR implementatie
- **PHASE 2 (DURING)**: Valideer approach tijdens bouwen
- **PHASE 3 (AFTER)**: Self-check op 8/10 voor submit
- Voorkomt: outdated patterns, security holes, performance issues

#### ✅ ACCEPTANCE CRITERIA
**Waarom:** Definition of done moet crystal clear zijn.
- Agent weet wanneer feature compleet is
- Reviewer kan objectief valideren
- Voorkomt scope creep

#### 🧪 HOE TE TESTEN
**Waarom:** Testbare features zijn betrouwbare features.
- Concrete test commands = reproduceerbaar
- Stap-voor-stap = ook voor non-developers uitvoerbaar
- Voorkomt "works on my machine" issues

#### 🚨 KRITIEKE PUNTEN
**Waarom:** Veiligheid en performance mogen niet vergeten worden.
- Security checklist voorkomt vulnerabilities
- Performance criteria voorkomt trage code
- Error handling zorgt voor goede UX

---

## ✅ Kwaliteit Checklist

Gebruik deze checklist VOORDAT je een contract als "klaar" markeert:

### Contract Volledigheid
- [ ] Titel is specifiek en beschrijvend
- [ ] Priority + rationale zijn ingevuld
- [ ] DOEL sectie is compleet (wat, waarom, voor wie, use case)
- [ ] INPUT FILES bevatten alle relevante bestanden
- [ ] OUTPUT bevat ALLE deliverables
- [ ] Elke OUTPUT heeft VOLLEDIGE working code (geen TODO's)

### Context7 Integratie
- [ ] PHASE 1 bevat specifieke library/pattern research queries
- [ ] PHASE 2 bevat validatie checkpoints per component
- [ ] PHASE 3 bevat 8/10 self-check criteria
- [ ] Escalation rules zijn duidelijk

### Testing & Validatie
- [ ] ACCEPTANCE CRITERIA zijn allemaal testbaar
- [ ] HOE TE TESTEN bevat werkende bash commands
- [ ] Test output expectations zijn beschreven
- [ ] Edge cases zijn gedocumenteerd

### Security & Performance
- [ ] Security checklist is ingevuld
- [ ] Performance criteria zijn specifiek
- [ ] Error handling scenario's zijn benoemd
- [ ] Data management is addressed

### Practicaliteit
- [ ] Tijdschatting is realistisch per fase
- [ ] Dependencies zijn expliciet genoemd
- [ ] IMPLEMENTATION CHECKLIST is actionable
- [ ] Geen placeholders meer in de tekst

---

## 🎯 Best Practices

### DOs ✅

**Wees specifiek:**
```markdown
❌ BAD: "Update de database"
✅ GOOD: "Add column `step_outputs JSONB` to `jobs` table with GIN index"
```

**Geef volledige code:**
```markdown
❌ BAD: "Create API endpoint for debug data"
✅ GOOD:
@router.get("/{job_id}/debug")
async def get_debug(job_id: str):
    # Complete working implementation here...
```

**Context7 queries moeten actionable zijn:**
```markdown
❌ BAD: "Research best practices"
✅ GOOD: "Query Context7: 'What are PostgreSQL JSONB indexing best practices for frequent queries?'"
```

**Acceptance criteria moeten testbaar zijn:**
```markdown
❌ BAD: "API works correctly"
✅ GOOD: "GET /api/jobs/{id}/debug returns 200 with correct JSON structure"
```

### DON'Ts ❌

**Geen vage beschrijvingen:**
```markdown
❌ "Make it better"
❌ "Improve performance"
❌ "Add some error handling"
```

**Geen pseudocode in OUTPUT:**
```markdown
❌ "// TODO: implement download logic here"
❌ "[Add database query]"
```

**Geen generieke Context7 queries:**
```markdown
❌ "Check if this is good"
❌ "Review the code"
```

**Geen on-testbare criteria:**
```markdown
❌ "User is happy"
❌ "Code looks clean"
```

---

## 📚 Voorbeelden

### Goede Contract Voorbeelden

Zie bestaande contracts voor referentie:

1. **[job-debug-viewer/JOB_DEBUG_VIEWER.md](../job-debug-viewer/JOB_DEBUG_VIEWER.md)**
   - ✅ Complete Context7 3-fase integratie
   - ✅ Volledige code voorbeelden voor alle deliverables
   - ✅ Concrete test instructies
   - ✅ Security & Performance criteria

2. **[completed-moment-selection/AGENT_1_BACKEND_API.md](../completed-moment-selection/AGENT_1_BACKEND_API.md)**
   - ✅ Duidelijke INPUT/OUTPUT structuur
   - ✅ Specifieke API endpoint voorbeelden
   - ✅ Testbare acceptance criteria

### Template Checklist Per Sectie

**Gebruik deze per sectie om volledigheid te checken:**

#### DOEL Sectie
- [ ] Wat wordt gebouwd?
- [ ] Waarom is dit nodig?
- [ ] Voor wie is dit?
- [ ] Use case beschreven?
- [ ] Voor/na situatie helder?

#### INPUT FILES Sectie
- [ ] Alle relevante files genoemd?
- [ ] Per file: wat moet je eruit leren?
- [ ] Gecategoriseerd (Database, API, Frontend, etc.)?

#### OUTPUT Sectie
- [ ] Alle deliverables genoemd?
- [ ] Per deliverable: filepath + (NEW/UPDATE)?
- [ ] Volledige werkende code?
- [ ] Uitleg bij elke deliverable?

#### CONTEXT7 Sectie
- [ ] PHASE 1: Specifieke research queries?
- [ ] PHASE 2: Validatie checkpoints?
- [ ] PHASE 3: 8/10 self-check criteria?
- [ ] Escalation rules beschreven?

---

## 🔄 Contract Lifecycle

```
1. CREATE (gebruik template)
   ↓
2. FILL IN (vul alle secties compleet in)
   ↓
3. VALIDATE (check met quality checklist)
   ↓
4. PUBLISH (naar agent_contracts/{feature}/)
   ↓
5. IMPLEMENT (agent gebruikt contract)
   ↓
6. COMPLETE (verplaats naar completed-{feature}/)
   ↓
7. DOCUMENT (maak README met resultaten)
```

### Status Indicators

- 🟡 **Ready for implementation** - Contract compleet, kan starten
- 🔵 **In Progress** - Agent is aan het werk
- ✅ **Completed** - Feature live, contract naar completed/
- 🔴 **Blocked** - Dependency issue, kan niet starten

---

## 🛠️ Tools & Helpers

### Contract Validator Script (Future)

```bash
# Future: Automatische contract validatie
./scripts/validate-contract.sh agent_contracts/my-feature/CONTRACT.md

# Checks:
# - All placeholders filled
# - Code blocks are not empty
# - Required sections present
# - Context7 queries are specific
```

### Quick Start Script

```bash
# Future: Snel nieuwe contract maken
./scripts/new-contract.sh my-new-feature "Feature description"

# Creates:
# - agent_contracts/my-new-feature/
# - Copy of template
# - Blank README.md
# - Updates main index
```

---

## 📖 Zie Ook

- [Agent Contracts README](../README.md) - Hoofdindex van alle contracts
- [Job Debug Viewer Contract](../job-debug-viewer/JOB_DEBUG_VIEWER.md) - Volledig voorbeeld
- [Completed Moment Selection](../completed-moment-selection/) - Afgerond project
- [.claude/agents/TEMPLATE.md](../../.claude/agents/TEMPLATE.md) - Agent template (complementair)

---

**Laatst bijgewerkt:** 2025-10-16
**Template Versie:** 1.0
**Maintainer:** AgentOS Development Team
