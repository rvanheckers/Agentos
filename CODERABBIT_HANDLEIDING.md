# 🤖 CodeRabbit & CI/CD Handleiding voor AgentOS

## 📍 Waar staan de bestanden?

**CodeRabbit configuraties (MOET in project root!):**
```text
AgentOS/
├── .coderabbit.yml            👈 Actieve configuratie (default: uitgebreid)
├── .coderabbit-fast.yml       👈 Snelle versie (basics only)
└── .coderabbit-full-backup.yml 👈 Backup van uitgebreide versie (tijdelijk)
```

**GitHub workflows:**
```text
AgentOS/
└── .github/
    ├── workflows/
    │   ├── ci.yml         👈 Volledige teststraat 
    │   └── ci-fast.yml    👈 Snelle checks
    └── pull_request_template.md  👈 PR checklist
```

⚠️ **BELANGRIJK:** CodeRabbit bestanden MOETEN in de root staan, niet in een map!

### 🔍 **Verschil tussen configuraties:**
- **`.coderabbit.yml`** (uitgebreid): Volledige code review, alle regels, uitgebreide checks
- **`.coderabbit-fast.yml`** (snel): Alleen kritieke issues, snelle feedback voor dagelijkse development

---

## 🚀 Hoe gebruik je het?

### Stap 1: Kies je configuratie

**Voor dagelijkse development (snel):**
```bash
# Backup huidige uitgebreide versie en activeer snelle versie
cp .coderabbit.yml .coderabbit-full-backup.yml
cp .coderabbit-fast.yml .coderabbit.yml
```

**Voor belangrijke features (uitgebreid):**
```bash
# Herstel de uitgebreide versie
cp .coderabbit-full-backup.yml .coderabbit.yml
```

**Check welke versie actief is:**
```bash
# Kijk of het de snelle of uitgebreide versie is
head -n 20 .coderabbit.yml | grep -E "(minimal|comprehensive|fast)"
```

### Stap 2: Branch naamgeving (voor automatische CI keuze)

**Snelle CI pipeline:** 
- `feature/quick-*`
- `hotfix/*` 
- `bugfix/*`

**Volledige CI pipeline:**
- `feature/*` (normaal)
- `main`
- `develop`

**Voorbeelden:**
```bash
git checkout -b feature/quick-button-fix    # → Snelle CI
git checkout -b feature/user-authentication # → Volledige CI
git checkout -b hotfix/critical-bug         # → Snelle CI
```

---

## 🔄 Workflow stappen

### Visuele Flow Overzicht:
```
┌─────────────────┐
│ 1. Branch maken │  git checkout -b feature/nieuwe-feature
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. Code schrijven│  # Maak je wijzigingen
│    & Testen     │  pytest tests/        ← Voorkomt CI fails!
└────────┬────────┘  ruff check .
         │
         ▼
┌─────────────────┐
│ 3. Commit+Push  │  git add .
│                 │  git commit -m "feat: nieuwe feature"
└────────┬────────┘  git push origin feature/nieuwe-feature
         │
         ▼
┌─────────────────┐
│ 4. PR maken     │  gh pr create
│                 │  # OF: gh pr create --web
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 5. Automatisch: │  ✓ CI draait tests
│ CI + CodeRabbit │  ✓ CodeRabbit geeft feedback
└────────┬────────┘  ✓ Security checks
         │
    ❌ Iets faalt?
         │
         ▼
┌─────────────────┐
│ 6. Fix & Push   │  # Fix lokaal, commit, push
│                 │  git add . && git commit -m "fix: ..."
└────────┬────────┘  git push
         │           ↺ Terug naar stap 5
         │
    ✅ Alles groen?
         │
         ▼
┌─────────────────┐
│ 7. Merge!       │  gh pr merge
│                 │  # OF merge button op GitHub
└─────────────────┘
```

### Voor een nieuwe feature:

1. **Branch maken:**
```bash
git checkout -b feature/mijn-nieuwe-feature
```

2. **Configuratie kiezen:**
- Kleine fix? → Snelle CodeRabbit
- Belangrijke feature? → Uitgebreide CodeRabbit

3. **Code schrijven en committen:**
```bash
git add .
git commit -m "Add nieuwe feature"
git push origin feature/mijn-nieuwe-feature
```

4. **Pull Request maken:**
```bash
# Optie A: Via GitHub CLI (makkelijk!)
gh pr create --title "Mijn nieuwe feature" --body "Beschrijving"

# Optie B: Via browser
gh pr create --web  # Opent browser met PR form
```

5. **CodeRabbit feedback bekijken:**
```bash
# Bekijk PR status
gh pr view

# Bekijk CodeRabbit comments
gh pr view --comments

# Open PR in browser
gh pr view --web

# Check CI status
gh pr checks
```

6. **CodeRabbit feedback verwerken:**
- Lees de comments
- Fix de issues
- Push weer → CodeRabbit checkt opnieuw

7. **GitHub Secrets setup (eenmalig):**
```bash
# Voor CI database wachtwoord
gh secret set POSTGRES_PASSWORD_TEST --body "your_secure_test_password"
```

8. **Mergen:**
```bash
# Check status
gh pr status

# Als alles groen is:
gh pr merge --auto  # Auto-merge wanneer checks slagen
# OF
gh pr merge --squash  # Squash en merge
```

---

## 🎛️ Configuratie uitleg

### `.coderabbit.yml` (Uitgebreid)
- **Checkt:** Alles (security, types, performance, style)
- **Tests:** Draait pytest automatisch
- **Tools:** ruff, mypy, bandit, pip-audit  
- **Tijd:** ~5-10 minuten
- **Gebruik voor:** Productie-klare features

### `.coderabbit-fast.yml` (Snel)  
- **Checkt:** Alleen security + basic quality
- **Tests:** Geen  
- **Tools:** Alleen bandit (security)
- **Tijd:** ~1-2 minuten
- **Gebruik voor:** Dagelijkse fixes, experimenten

---

## 🚨 Troubleshooting

### "CodeRabbit reageert niet"
- Check of `.coderabbit.yml` in project root staat
- Controleer of de YAML syntax klopt
- Wacht 2-3 minuten na push

### "CI faalt op workflow permissions"  
- GitHub token mist `workflow` scope
- Ga naar: https://github.com/settings/tokens
- Edit token → vink `workflow` aan

### "Tests falen in CI"
```bash
# Test lokaal eerst:
pytest testing/ -v
ruff check .
mypy . --ignore-missing-imports
```

### "Merge geblokkeerd"
- Los alle CodeRabbit comments op
- Zorg dat CI groen is  
- Vul PR template volledig in

---

## 🎯 Pro Tips

### 1. Smart branch naming
```bash
# Voor snelle doorloop:
git checkout -b feature/quick-typo-fix
git checkout -b hotfix/urgent-security

# Voor grondige review:  
git checkout -b feature/new-user-system
```

### 2. GitHub CLI handige commando's
```bash
# Lijst van al je PRs
gh pr list

# Bekijk specifieke PR (#4 bijvoorbeeld)
gh pr view 4
gh pr view 4 --comments

# Checkout een PR lokaal
gh pr checkout 4

# Sluit PR zonder merge
gh pr close 4

# Heropen PR
gh pr reopen 4

# Review goedkeuren
gh pr review --approve

# Zie workflow runs
gh run list
gh workflow view
```

### 3. CodeRabbit hacks
- Type `@coderabbitai explain this` in PR comments voor uitleg
- `@coderabbitai suggest improvements` voor tips
- `@coderabbitai review only security` voor specifieke focus

### 4. CI optimalisatie
- Commit vaak (kleine commits = snellere CI)
- Fix linting lokaal: `ruff check . --fix`
- Test lokaal: `pytest testing/test_jobs_queue.py -v`

### 5. Merge strategy
1. Start met **snelle config** tijdens development  
2. Switch naar **uitgebreide config** voor finale review
3. Fix alle issues
4. Merge naar main

---

## 📊 Wat wordt er precies gecheckt?

### Uitgebreide configuratie:
✅ **Security:** Passwords, secrets, SQL injection  
✅ **Code quality:** Style, imports, complexity  
✅ **Types:** mypy type checking  
✅ **Tests:** pytest automatisch  
✅ **Performance:** Database queries, loops  
✅ **Dependencies:** Vulnerability scan  

### Snelle configuratie:
✅ **Security:** Basic secret detection  
✅ **Syntax:** Python compile check  
✅ **Style:** Alleen kritieke errors  

---

## 🔧 Aanpassen configuratie

### Meer mappen toevoegen voor review:
```yaml
# In .coderabbit.yml
reviews:
  include:
    - "api/**"
    - "jouw-nieuwe-map/**"  # 👈 Voeg toe
```

### Bestanden uitsluiten:
```yaml
reviews:
  exclude:
    - "**/test_temp/**"     # 👈 Voeg toe
    - "**/*.backup"         # 👈 Voeg toe
```

### Security patronen toevoegen:
```yaml
rules:
  security:
    patterns:
      - "database_password"  # 👈 Voeg toe
      - "admin_token"        # 👈 Voeg toe
```

---

## ❓ Vragen & Antwoorden

**Q: Kan ik CodeRabbit uitschakelen voor een PR?**  
A: Ja, hernoem `.coderabbit.yml` tijdelijk naar `.coderabbit.yml.backup`

**Q: Waarom duurt de CI zo lang?**  
A: Gebruik de fast versie, of check welke tests falen

**Q: Kan ik eigen regels toevoegen?**  
A: Ja! Edit `.coderabbit.yml` en voeg custom patterns toe

**Q: Werkt dit ook voor JavaScript?**  
A: Ja, maar voeg `eslint` toe aan je `package.json` voor betere checks

---

## 🎉 Klaar!

Je hebt nu een professionele development setup! 

**Next steps:**
1. Test met een kleine PR
2. Kijk hoe CodeRabbit reageert  
3. Pas configuratie aan naar je wensen
4. Enjoy de geautomatiseerde code quality! 🚀