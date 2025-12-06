# Moment Detection Agent - v3.0.0 Unified AI Analysis

AI-powered content analysis combining content type detection + viral moment analysis in a single API call.

## 🚀 NEW: UnifiedContentAnalyzer (v3.0.0)

**Production-grade unified content analyzer** that replaces naive regex-based detection with AI-powered analysis.

### Problem Solved
- **Before**: Mehdi political speech "CALLS OUT Israel to 12,000 People" → misclassified as 'music' due to "live performance" regex
- **After**: AI context understanding → correctly classified as 'spoken' content with proper viral moments

### Key Benefits
- 🎯 **50-66% API Cost Reduction**: Single Claude call instead of 2-3 separate calls
- 🧠 **AI Context Understanding**: Replaces naive regex with intelligent analysis
- 🛡️ **Enterprise Security**: Prompt injection protection, comprehensive validation
- 🔄 **Zero-Risk Deployment**: Environment toggle with automatic fallbacks
- 📊 **Production Monitoring**: Comprehensive telemetry and A/B testing

### Quick Start
```bash
# Enable UnifiedContentAnalyzer
export USE_UNIFIED_ANALYZER=true
export ANTHROPIC_API_KEY=your_key_here

# Use existing MomentDetector - automatically uses UnifiedContentAnalyzer
from agents2.moment_detection.moment_detector import MomentDetector
detector = MomentDetector()
result = detector.detect_moments(input_data)
```

### Content Classification
- **Music**: Official music videos, songs → `ai_song_lyrics`
- **Spoken**: Speeches, interviews, political → `ai_viral_analysis`
- **Tutorial**: How-to videos, cooking → `ai_tutorial_highlights`
- **Sports**: Games, matches → `ai_sports_highlights`
- **Gaming**: Gameplay, streams → `ai_gaming_highlights`
- **Other**: Everything else → `ai_general_highlights`

### Security Features
- Prompt injection protection via input sanitization
- JSON schema validation with retry logic
- Length enforcement (evidence 120chars, key_phrase 120chars)
- Engagement drivers validation (max 5 strings)
- Comprehensive fallback chain for 100% uptime

**📖 See `unified_content_analyzer.py` for complete documentation and examples.**

---

## 🎯 Available Agents

### moment_detector.py - **ENHANCED: Real Transcript Analysis**
- **Purpose**: Detect valuable moments based on transcript content analysis
- **NEW Features**:
  - ✅ **Real NLP Analysis**: Scans transcript for viral keywords and emotions
  - ✅ **Variable Clip Count**: 0-5 clips based on content quality (no artificial limit)
  - ✅ **Viral Scoring**: Each sentence scored on viral potential
  - ✅ **Quality-Based Output**: Only creates clips for high-value moments
  - ✅ **User Feedback**: Logs how many valuable moments found
- **Input**: 
  ```json
  {
    "video_path": "video.mp4",
    "transcript": "Wow this is amazing! And then he said...",  // Real transcript text
    "intent": "short_clips",           // viral/key_highlights/smart_summary  
    "min_duration": 15,               // Minimum clip length
    "max_duration": 60,               // Maximum clip length
    "max_moments": 10                 // Upper limit (AI decides actual count)
  }
  ```
- **Output**: 
  ```json
  {
    "success": true,
    "moments": [{
      "start_time": 45.2,
      "end_time": 60.1, 
      "duration": 14.9,
      "confidence": 0.85,              // Based on viral score
      "type": "viral_ai",              // Analysis method used
      "description": "🔥 Viral: wow this is amazing and incred...",
      "keywords": ["amazing", "incredible", "wow"],
      "viral_score": 4,                // Number of viral indicators found
      "sentence_text": "wow this is amazing and incredible reaction"
    }],
    "total_moments": 2,                // Variable count (0-5 based on quality)
    "analysis_mode": "ai_viral_analysis",  // vs fallback_no_transcript
    "video_duration": 180.5
  }
  ```
- **Usage**: `python moment_detector.py '{"video_path": "video.mp4", "transcript": "Real transcript text..."}'`

**🔥 Viral Detection Logic**:
1. **Keyword Categories**:
   - **Reactions**: wow, amazing, incredible, unbelievable, omg, holy, crazy, insane
   - **Emotions**: laugh, crying, shocked, surprised, angry, excited, happy  
   - **Engagement**: wait, look, watch, see this, check this, listen
   - **Quotes**: said, quote, told me, like this, exactly
   - **Dramatic**: suddenly, then, but then, and then, happened, moment

2. **Scoring System**:
   - **Score ≥ 3**: High quality viral moments → Include in output
   - **Score ≥ 2**: Medium quality → Include if no high quality found
   - **Score < 2**: Low quality → Skip

3. **Variable Output**:
   - **No valuable content**: 0 clips
   - **Some good moments**: 1-2 clips  
   - **Viral content**: 3-5 clips
   - **Quality over quantity**: AI decides optimal count

## 🎵 SMART VIDEO TYPE DETECTION

**Automatische herkenning van video types met aangepaste clip logic:**

### 📺 NORMALE VIDEOS (praat content)
```
Transcript: "Wow dit is amazing! Holy shit wat gebeurt hier!"
↓
AI zoekt naar viral woorden: wow, amazing, holy → VIRAL SCORE: 3
↓  
Resultaat: 2-3 clips op momenten waar viral woorden staan
```

### 🎵 MUZIEK VIDEOS (alleen muziek/beats)
```
Transcript: "La la la musik beat drop bass"  
↓
AI zoekt naar viral woorden → NIETS GEVONDEN
↓
🎵 MUZIEK FALLBACK: Clips op muziek structuur timestamps:
  - 10-25s = intro/verse moment
  - 40% van video = chorus/drop moment  
  - 70% van video = bridge/climax moment
```

### 🤖 BESLISSING BOOM
```
Heeft video transcript? 
├── JA → Zoek viral woorden in tekst
│   ├── Viral woorden gevonden → Maak clips op die timestamps
│   └── GEEN viral woorden → 🎵 MUZIEK VIDEO FALLBACK
└── NEE → Standaard clips (elke 20 seconden verdeeld)
```

**🎯 Content-Based Clip Count Examples**:
```
Boring transcript: "This is a test. Nothing interesting happens."
→ Result: 🎵 Music fallback (3 clips op structurele momenten)

Good content: "Wow that was amazing! The reaction was incredible."  
→ Result: 2 clips (viral_score: 4)

Viral content: "OMG this is insane! Amazing reaction! Holy cow! Incredible moment!"
→ Result: 4-5 clips (multiple viral_score ≥ 2 moments)

Music video: "Beat drop bass line rhythm flow"
→ Result: 🎵 3 clips (intro 10-25s, chorus 40%, bridge 70%)
```

## 🚀 Integration with Video Pipeline

**Enhanced Celery Workflow**:
```python
# Real transcript analysis workflow:
transcript = transcribe_audio(video)           # Real or mock transcript
↓
moments = detect_moments_with_ai(transcript)   # AI analysis, variable count
↓  
faces = detect_faces_multiframe(video)         # Face tracking
↓
dynamic_cuts = cut_videos_with_tracking(moments, faces)  # All detected moments
```

**User Feedback Logging**:
```
INFO: "🎯 Found 4 viral moments for job 123 - great content!"
INFO: "⚠️ No valuable moments found in content for job 124"  
INFO: "🎯 Found 1 high-quality moments for job 125"
```

**Database Integration**: 
- Stores actual moment count and analysis method
- UI shows user how many valuable moments were detected
- Analytics track content quality distribution

## 🔧 External Usage
Supports real transcript analysis via JSON interface - ideal for content creators to analyze video quality before processing.