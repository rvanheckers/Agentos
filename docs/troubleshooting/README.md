# 🛠️ AgentOS Troubleshooting Documentation

Deze map bevat documentatie voor het oplossen van problemen in het AgentOS video processing systeem.

## 📋 Beschikbare Documenten

### [🔧 Metadata Pipeline Fix](./metadata-pipeline-fix.md)
**Probleem:** Frontend toont "Analysis details not available" in plaats van echte metadata  
**Oplossing:** Missing `moments` array in data flow tussen Celery tasks  
**Status:** ✅ Opgelost  

### [🎬 Video Processing Analysis](./video_processing_analysis.md)  
**Beschrijving:** Volledige analyse van de video processing pipeline en data flow  
**Gebruik:** Referentie voor het begrijpen van agent volgorde en data doorgifte  
**Status:** 📚 Referentie document  

## 🚀 Hoe Te Gebruiken

1. **Identificeer het probleem** door logs te checken
2. **Zoek het relevante document** in deze map
3. **Volg de stappen** in de troubleshooting guide
4. **Verifieer de fix** met de gegeven test procedures

## 📞 Support

Voor nieuwe problemen, maak een issue aan met:
- Beschrijving van het probleem
- Relevante logs
- Stappen om te reproduceren
- Verwachte vs werkelijke resultaat