# Job Debug Viewer - Active Contract

**Status:** 🟡 Ready for Implementation
**Priority:** MEDIUM
**Estimated Time:** 6-8 hours

---

## 📋 Project Overview

### What to Build

Een **visuele debug interface** voor de video processing pipeline waar je per stap kunt zien:
- ✅ Of de stap succesvol was
- 📊 Het resultaat (text/image/video preview)
- ⚙️ Welke settings gebruikt zijn
- ❌ Errors met context

**Target Audience:** "Vibecoders" - gebruikers die zonder code willen debuggen en configureren.

### Problem Being Solved

**Current State:**
- Debugging vereist log files lezen
- Geen visuele feedback tijdens processing
- Moeilijk te zien waar iets misgaat
- Geen manier om output quality te valideren per stap

**After This Feature:**
- Real-time visuele feedback per pipeline stap
- Thumbnails, transcripts, face previews direct zichtbaar
- Instant error identification
- Quality validation op elk punt in de pipeline

---

## 🏗️ Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                   Frontend Layer                         │
│  job-debug.html - Visual interface met auto-refresh      │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    API Layer                             │
│  GET /api/jobs/{id}/debug - Returns step outputs        │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                  Database Layer                          │
│  Job.step_outputs (JSON) - Stores debug data per step   │
└─────────────────────────────────────────────────────────┘
                            ↑
┌─────────────────────────────────────────────────────────┐
│                 Processing Tasks                         │
│  All 6 pipeline tasks save output to step_outputs       │
│  - download_video → thumbnail, duration, resolution      │
│  - transcribe_audio → transcript preview, metadata       │
│  - detect_moments → moment count, top moments            │
│  - detect_faces → face screenshots                       │
│  - intelligent_crop → crop comparison image              │
│  - cut_videos → clip previews                            │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Task Execution**: Elk task update slaat output op in `Job.step_outputs` JSON column
2. **API Request**: Frontend polled debug endpoint elke 5 seconden
3. **Response**: API returns alle step outputs met status & visuele data
4. **Rendering**: Frontend toont visuele previews per stap

---

## 📊 Database Schema

### New Column: `step_outputs`

```sql
ALTER TABLE jobs
ADD COLUMN step_outputs JSONB DEFAULT '{}';

CREATE INDEX idx_jobs_step_outputs ON jobs USING GIN (step_outputs);
```

### JSON Structure

```json
{
  "download_video": {
    "status": "success",
    "timestamp": "2025-10-16T05:00:00Z",
    "output": {
      "video_path": "/path/to/video.mp4",
      "thumbnail": "/path/to/thumb.jpg",
      "duration": 300,
      "resolution": "1920x1080",
      "file_size": 52428800
    }
  },
  "transcribe_audio": {
    "status": "success",
    "timestamp": "2025-10-16T05:02:00Z",
    "output": {
      "transcript": "First 500 characters...",
      "full_text_length": 5000,
      "segments_count": 50,
      "language": "en"
    }
  },
  "detect_moments": {
    "status": "success",
    "timestamp": "2025-10-16T05:03:00Z",
    "output": {
      "moments_count": 8,
      "top_moments": [
        {
          "description": "Viral moment description",
          "start_time": 10.5,
          "end_time": 25.3,
          "viral_score": 95
        }
      ]
    }
  }
}
```

---

## 🔄 Implementation Workflow

### Pipeline Steps Tracked

1. **📥 Download Video** (`download_video`)
   - Thumbnail generation
   - Duration, resolution, file size

2. **🎤 Transcribe Audio** (`transcribe_audio`)
   - Transcript preview (500 chars)
   - Language detection
   - Segment count

3. **✨ Detect Viral Moments** (`detect_moments`)
   - Total moments found
   - Top 3 moments with scores
   - Time ranges

4. **👤 Detect Faces** (`detect_faces`)
   - Face count
   - Face screenshots (max 5)
   - Primary speaker detection

5. **✂️ Intelligent Crop** (`intelligent_crop`)
   - Crop settings (x, y, width, height)
   - Before/after comparison image
   - Target aspect ratio

6. **🎬 Cut Videos** (`cut_videos`)
   - Clip count
   - Clip previews with thumbnails
   - Duration per clip

---

## 🛠️ Key Deliverables

### 1. Database Migration
**File:** `migrations/add_step_outputs_column.sql`
- Adds `step_outputs` JSONB column
- Creates GIN index for fast queries
- Adds column documentation

### 2. API Endpoint
**File:** `api/routes/debug.py` (NEW)
- Endpoint: `GET /api/jobs/{job_id}/debug`
- Returns: Job info + all step outputs
- Error handling: 404 for missing jobs

### 3. Task Updates
**Files:**
- `tasks/video_processing_phase1.py` (UPDATE)
- `tasks/video_processing_phase2.py` (UPDATE)

All tasks krijgen `save_step_output()` helper die:
- Status opslaat (success/failed/in_progress)
- Timestamp toevoegt
- Visual output opslaat
- Errors captured met context

### 4. Helper Functions
**File:** `utils/video_helpers.py` (NEW/UPDATE)

Functions:
- `generate_thumbnail(video_path, timestamp)` - FFmpeg thumbnail
- `get_duration(video_path)` - Video duration in seconds
- `get_resolution(video_path)` - Resolution string (e.g., "1920x1080")
- `generate_face_screenshots(faces, video_path, job_id)` - Face image extracts
- `generate_crop_comparison(video_path, crop_settings, job_id)` - Side-by-side crop preview

### 5. Frontend Debug Page
**File:** `frontend/job-debug.html` (NEW)

Features:
- Visual step cards met status badges
- Thumbnail previews
- Transcript display
- Face grid layout
- Crop comparison viewer
- Video clip previews
- Auto-refresh elke 5 seconden
- Responsive design

---

## 🔍 Context7 3-Phase Methodology

**MANDATORY:** This contract requires proactive Context7 validation at 8/10 quality threshold.

### Phase 1: BEFORE (Research)
- Resolve library IDs for FastAPI, SQLAlchemy, FFmpeg
- Get best practices for JSON column patterns
- Research video thumbnail generation techniques
- Learn async workflow progress tracking

### Phase 2: DURING (Validation)
- Validate database design approach
- Check implementation patterns per component
- Verify error handling strategies
- Cross-reference with industry standards

### Phase 3: AFTER (Self-Check)
- Run Context7 analysis on output (target: ≥8/10)
- Validate deliverable completeness
- Document Context7 findings
- Only submit to review after 8+ score

**Escalation:** If score < 8/10, iterate with Context7 until threshold met.

---

## ✅ Acceptance Criteria

### Database
- [ ] Migration script uitgevoerd zonder errors
- [ ] `step_outputs` column bestaat op `jobs` table
- [ ] GIN index aangemaakt voor performance

### API
- [ ] GET `/api/jobs/{id}/debug` endpoint werkt
- [ ] Returns correct JSON structure
- [ ] 404 handling voor missing jobs
- [ ] Proper error logging

### Tasks
- [ ] Alle 6 tasks slaan output op
- [ ] Success states bevatten visual data
- [ ] Failures bevatten error context
- [ ] Timestamps accurate

### Helpers
- [ ] `generate_thumbnail()` werkt met FFmpeg
- [ ] Face screenshots worden gegenereerd
- [ ] Crop comparison image correct
- [ ] No crashes op invalid input

### Frontend
- [ ] Page loads met job ID parameter
- [ ] All 6 steps render correctly
- [ ] Visual previews tonen (images/videos)
- [ ] Auto-refresh works elke 5s
- [ ] Error messages duidelijk
- [ ] Responsive op mobile

---

## 🧪 How to Test

### Quick Test Flow

```bash
# 1. Run migration
psql -U postgres -d agentos -f migrations/add_step_outputs_column.sql

# 2. Start services
make run-api  # Terminal 1
make run-celery  # Terminal 2

# 3. Create test job
curl -X POST http://localhost:8001/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"video_url": "https://example.com/test.mp4", "user_id": "test"}'

# 4. Get job ID and open debug viewer
JOB_ID=<from-response>
open http://localhost:8000/job-debug.html?job=$JOB_ID

# 5. Watch real-time updates
# Verify each step shows output as processing completes
```

### Verification Checklist

- [ ] Thumbnails load correctly
- [ ] Transcript preview displays
- [ ] Moments show with scores
- [ ] Face screenshots visible
- [ ] Crop comparison renders
- [ ] Clips are playable
- [ ] Errors display clearly
- [ ] Auto-refresh updates UI

---

## 🚨 Critical Points

### Security
- Validate job_id format (UUID only)
- Sanitize file paths (prevent traversal)
- Limit JSON size (prevent bloat)
- Add authentication (job owner only)

### Performance
- GIN index on step_outputs
- Limit thumbnail resolution (400px max)
- Compress face screenshots
- Lazy load videos (no autoplay)
- Cache generated images

### Error Handling
- Graceful fallback if thumbnail fails
- Handle missing ffmpeg
- Catch corrupted video files
- User-friendly error messages

### Data Management
- Cleanup old debug images (retention policy)
- Don't store full transcripts (preview only)
- Limit moments to top 5
- Consider separate debug table for large data

---

## 📚 References

### Contract Document
**Primary:** [JOB_DEBUG_VIEWER.md](./JOB_DEBUG_VIEWER.md)

### Input Files to Read
1. `core/database_manager.py` - Job model structure
2. `api/routes/jobs.py` - Existing API patterns
3. `tasks/video_processing_phase1.py` - Phase 1 task patterns
4. `tasks/video_processing_phase2.py` - Phase 2 task patterns
5. `frontend/job-status.html` - Frontend patterns

### External Documentation
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [PostgreSQL JSON Functions](https://www.postgresql.org/docs/current/functions-json.html)

---

## 📊 Implementation Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| Phase 1: Foundation | 2h | Migration, Job model update, testing |
| Phase 2: API | 1h | Debug endpoint, router registration |
| Phase 3: Task Updates | 2h | Update all 6 tasks with save_step_output |
| Phase 4: Helpers | 1.5h | Video helpers, thumbnail generation |
| Phase 5: Frontend | 2h | HTML page, JavaScript, styling |
| Phase 6: Testing | 1.5h | Integration test, bug fixes, polish |
| **Total** | **10h** | Buffer included for debugging |

---

## 🎯 Success Metrics

**Definition of Done:**
- All acceptance criteria checked ✅
- Context7 validation score ≥ 8/10 ✅
- Full integration test passes ✅
- Vibecoders can debug without code ✅

**Quality Bar:**
- Visual feedback instant and accurate
- Error messages helpful, not technical
- Performance smooth (< 1s page load)
- Works on desktop + mobile

---

## 💡 Future Enhancements

Potential improvements na initial release:
- 🎯 Video preview scrubber per step
- 🎯 Downloadable debug reports (PDF)
- 🎯 Compare multiple jobs side-by-side
- 🎯 Real-time WebSocket updates (vs polling)
- 🎯 Step execution replay/rerun
- 🎯 Export step outputs to JSON

---

**Status:** Ready for implementation
**Contract Owner:** AgentOS Development Team
**Last Updated:** 2025-10-16

Voor complete implementation details, zie [JOB_DEBUG_VIEWER.md](./JOB_DEBUG_VIEWER.md)
