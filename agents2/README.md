# 🛠️ Agents2 - Atomic Agent Toolkit

## **Complete Agent Workforce & Toolbox**

Deze directory bevat alle **atomic agents** - gespecialiseerde tools die elk één specifieke taak uitvoeren. Elk agent heeft een single responsibility en kan onafhankelijk of in combinatie gebruikt worden.

---

## **📋 Agent Inventory**

### **🎬 Video Processing Agents**

#### **Core Video Operations**
- **`video_cutter.py`** - ✂️ Knip video op timestamps
- **`video_converter.py`** - 🔄 Format/resolutie conversie 
- **`video_effects.py`** - ✨ Visual effects (fade, zoom, blur)
- **`video_metadata.py`** - 📊 Metadata extractie

#### **AI-Enhanced Video**
- **`face_detector.py`** - 👤 MediaPipe gezichtsherkenning
- **`intelligent_cropper.py`** - 🎯 Slimme crop coordinates
- **`content_analyzer.py`** - 🧠 Content analyse en scoring

### **🎵 Audio Processing Agents**

#### **Audio Operations**
- **`audio_transcriber.py`** - 📝 Audio naar tekst (Whisper)
- **`audio_extractor.py`** - 🎵 Audio uit video halen
- **`voiceover_creator.py`** - 🗣️ Text-to-speech

### **🧠 AI & Analysis Agents**

#### **Content Intelligence**
- **`moment_detector.py`** - ⚡ Viral momenten detectie
- **`script_generator.py`** - 📝 AI script generatie
- **`social_post_generator.py`** - 📱 Socialmediaposts

### **🌐 Download & Upload Agents**

#### **Content Acquisition**
- **`video_downloader.py`** - ⬇️ YouTube/TikTok/Instagram download

### **📊 Orchestration Agents**

#### **Legacy Agents (Complex)**
- **`clipper.py`** - 🎬 Basic video clipper (multi-function)
- **`clipper_intelligent.py`** - 🤖 AI-enhanced clipper
- **`clipper_optimized.py`** - ⚡ Performance clipper
- **`video_analyzer.py`** - 🔍 Video analysis pipeline

---

## **🚀 Agent Usage Patterns**

### **1. Independent Usage**
```bash
# Gebruik één specifieke agent
python3 agents2/face_detector.py '{"video_path": "video.mp4"}'
python3 agents2/video_cutter.py '{"video_path": "video.mp4", "cuts": [...]}'
```

### **2. Orchestrated Workflow**
```python
# Combineer multiple agents
faces = face_detector.detect(video_path)
crop_coords = intelligent_cropper.calculate(faces)
clips = video_cutter.cut(video_path, timestamps)
```

### **3. API Integration**
```python
# Via API endpoints
POST /api/agents/face_detector
POST /api/agents/video_cutter
POST /api/agents/moment_detector
```

---

## **📊 Atomic Agent Principles**

### **1. Single Responsibility**
- Elk agent doet ÉÉN ding perfect
- Geen mixed concerns
- Duidelijke, gefocuste purpose

### **2. Standardized Interface**
```python
def main(input_data: Dict[str, Any]) -> Dict[str, Any]:
    # Validate input
    # Process data  
    # Return standardized output
```

### **3. Consistent Error Handling**
```json
{
    "success": false,
    "error": "Descriptive error message",
    "error_code": "ERROR_TYPE",
    "agent_version": "1.0.0"
}
```

### **4. Performance Metadata**
```json
{
    "success": true,
    "data": { /* main output */ },
    "processing_time": 1.5,
    "agent_version": "1.0.0"
}
```

---

## **🔧 Migration Strategy**

### **Phase 1: Core Atomic Agents** ✅
- Independent agents werken standalone
- Standardized interfaces
- Consistent error handling

### **Phase 2: UI Integration** 🔄
- Update UI om agents2 te gebruiken
- Atomic endpoint mapping
- Fallback naar legacy agents

### **Phase 3: Legacy Deprecation** 📅
- Gradual migration van legacy agents
- Maintain backwards compatibility
- Performance optimization

---

## **🎯 Agent Selection Guide**

### **Voor Eenvoudige Tasks:**
```text
Video knippen → video_cutter.py
Gezichten detecteren → face_detector.py
Audio transcriberen → audio_transcriber.py
```

### **Voor Complexe Workflows:**
```text
Elite Pipeline → Orchestratie van 5+ agents
Smart Clipping → face_detector + intelligent_cropper + video_cutter
Content Analysis → audio_transcriber + moment_detector
```

### **Voor Externe Systemen:**
```text
API Client → Kiest exact de agents die nodig zijn
Geen overhead van onnodige functionaliteit
Clean, focused interfaces
```

---

## **✨ Voordelen Atomic Architecture**

### **🔧 Development**
- **Easier Testing**: Elk agent onafhankelijk testbaar
- **Cleaner Code**: Single responsibility per agent
- **Faster Debugging**: Problemen geïsoleerd per agent

### **📈 Scalability**
- **Mix & Match**: Combineer agents voor custom workflows
- **Performance**: Alleen laden wat nodig is
- **Resource Optimization**: Specifieke agents voor specifieke taken

### **🔗 Integration**
- **Flexible Workflows**: Maak custom pipelines
- **External Systems**: Gebruik exact wat je nodig hebt
- **API Efficiency**: Minimale overhead per request

---

## **🎪 Conclusie**

**Agents2 is je complete gereedschapskist voor video processing!**

Van simpele video cutting tot geavanceerde AI-enhanced workflows - elk agent is geoptimaliseerd voor zijn specifieke taak en kan onafhankelijk of in combinatie gebruikt worden.

**Perfect voor:**
- 🎬 Video content creators
- 🤖 AI-powered workflows  
- 📱 Social media automation
- 🔗 External system integration

**Atomic agents = Maximum flexibiliteit, minimum overhead!**