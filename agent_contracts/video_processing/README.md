# Video Processing Agent Contracts

**Doel:** Merge Cinema-MVP V3.2 sub-shots tot coherente final clips

**Status:** 🟡 Ready for implementation
**Priority:** HIGH
**Estimated Time:** 6-8 hours

---

## 🎯 Project Overview

### Het Probleem

**Current State:**
```
Gebruiker selecteert 1 moment (15s)
    ↓
Cinema-MVP V3.2 genereert intelligente shot sequence:
    - 0-2s: center crop (establishing shot)
    - 2-12s: left crop (linker persoon spreekt)
    - 12-15s: right crop (rechter persoon antwoordt)
    ↓
video_cutter.py maakt 3 aparte files:
    - clip_0_0.mp4 (2s)
    - clip_0_1.mp4 (10s)
    - clip_0_2.mp4 (3s)
    ↓
❌ Gebruiker krijgt: 3 losse clips (NIET coherent)
```

**Gewenste State:**
```
Gebruiker selecteert 1 moment (15s)
    ↓
Cinema-MVP V3.2 genereert shot sequence (zelfde als boven)
    ↓
video_cutter.py maakt tijdelijke sub-shots
    ↓
VideoStitcher merged ze tot 1 finale clip:
    - 0-2s: smooth center view
    - 2-12s: smooth left person close-up
    - 12-15s: smooth right person close-up
    ↓
✅ Gebruiker krijgt: moment_0_final.mp4 (15s, coherent, professioneel)
```

### Architectuur

```
┌─────────────────────────────────────────────────────────────┐
│                    Cinema-MVP V3.2                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │ 1. Layout Detection (split-screen/multi-person)    │    │
│  │ 2. Activity Tracking (wie spreekt wanneer?)        │    │
│  │ 3. Shot Sequencing (intelligente timeline)         │    │
│  └────────────────────────────────────────────────────┘    │
│                           ↓                                  │
│              shot_sequence = [                               │
│                {'crop_region': None, duration: 2.5},         │
│                {'crop_region': 'left', duration: 9.5},       │
│                {'crop_region': 'right', duration: 3.0}       │
│              ]                                               │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              intelligent_cropper.py (V3.2)                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │ Voor elk sub-shot in shot_sequence:                │    │
│  │   - Bereken crop coordinates                        │    │
│  │   - Call video_cutter.py                            │    │
│  │   - Save to: clip_0_0.mp4, clip_0_1.mp4, etc.      │    │
│  └────────────────────────────────────────────────────┘    │
│                           ↓                                  │
│              crops_per_moment = [                            │
│                {sub_moment_index: 0, file: 'clip_0_0.mp4'}, │
│                {sub_moment_index: 1, file: 'clip_0_1.mp4'}, │
│                {sub_moment_index: 2, file: 'clip_0_2.mp4'}  │
│              ]                                               │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   VideoStitcher (NEW!)                       │
│  ┌────────────────────────────────────────────────────┐    │
│  │ 1. Validate mezzanine format (alle clips uniform)  │    │
│  │ 2. Choose method:                                   │    │
│  │    - Hard cuts: FFmpeg concat demuxer (fast)       │    │
│  │    - Crossfades: filter_complex (quality)          │    │
│  │ 3. Merge clips → moment_0_final.mp4                │    │
│  │ 4. Validate A/V sync (±1 frame tolerance)          │    │
│  │ 5. Cleanup temp files                               │    │
│  └────────────────────────────────────────────────────┘    │
│                           ↓                                  │
│              moment_0_final.mp4 (15s, coherent)             │
└─────────────────────────────────────────────────────────────┘
                           ↓
                    ✅ GEBRUIKER
```

---

## 📦 Key Deliverables

### 1. VideoStitcher Core Implementation
**File:** `agents2/video_stitching/video_stitcher.py`
- Mezzanine format validation
- FFmpeg concat demuxer (hard cuts, no re-encode)
- FFmpeg filter_complex (crossfades, re-encode)
- A/V sync validation
- Atomic file operations

### 2. Celery Task Integration
**File:** `tasks/video_stitching_tasks.py`
- Async background processing
- Triggered after `cut_videos` completes
- Updates job status to "stitching"

### 3. Database Schema
**File:** `migrations/008_add_final_clip_path.sql`
- `moments.final_clip_path` column
- `moments.stitching_status` column
- Indexes for querying

### 4. API Endpoint
**File:** `api/routes/jobs.py` (UPDATE)
- `GET /jobs/{id}/moments/{i}/final` → final clip URL
- Status: pending/processing/completed/failed

### 5. Frontend Update
**File:** `static/job-status.html` (UPDATE)
- Download link: "moment_0_final.mp4"
- Video preview player
- Stitching status indicator

---

## 🎬 Hollywood Analogy

| Phase | Cinema Equivalent | AgentOS Implementation |
|-------|-------------------|------------------------|
| **Pre-Production** | Storyboarding, shot planning | Cinema-MVP V3.2: layout detection, shot sequencing |
| **Production** | Filming multiple takes/angles | video_cutter.py: generate sub-shot clips |
| **Post-Production** | Editing, stitching final cut | **VideoStitcher (NEW!)**: merge → final clip |
| **Distribution** | Deliver to audience | API/Frontend: download moment_X_final.mp4 |

**Current Missing:** Post-Production step! Cinema-MVP doet pre+production, maar vergeet post.

---

## 📋 Contracts

### [VIDEO_STITCHER_CONTRACT.md](./VIDEO_STITCHER_CONTRACT.md)
Volledig agent contract met:
- **INPUT FILES**: Wat moet gelezen worden om context te krijgen
- **OUTPUT**: Exacte deliverables met complete code voorbeelden
- **CONTEXT7 METHODOLOGY**: 3-fase validatie (BEFORE/DURING/AFTER)
- **ACCEPTANCE CRITERIA**: Testbare definition of done
- **HOE TE TESTEN**: Stap-voor-stap test instructies
- **IMPLEMENTATION CHECKLIST**: Fase-opdeling met tijdschatting

### [OUT_OF_SCOPE.md](./OUT_OF_SCOPE.md)
Features NIET in V1.0 maar wel waardevol voor toekomst:
- EBU R128 loudness normalization (V1.1)
- EDL (Edit Decision List) generation (V1.2)
- Custom transition effects (V2.0)
- GPU-accelerated encoding (V2.0)

---

## 🔗 Dependencies

### ✅ Al Geïmplementeerd (Vereist)
- **Cinema-MVP V3.2**: Shot sequencing logic (`cinematic_composer.py:289-540`)
- **intelligent_cropper V3.2**: Integration met shot sequencing (`intelligent_cropper.py:259-327`)
- **video_cutter.py**: Video cutting met crop coordinates (`video_cutter.py:650-750`)
- **Database schema**: `moments` table with `clip_paths` JSON array

### ❌ Nog Niet (Blocks This Feature)
GEEN! VideoStitcher kan direct geïmplementeerd worden.

### 🔄 Optional (Nice to Have)
- **Mezzanine preset**: Update `video_cutter.py` to render sub-shots in uniform format
  - Benefit: Eliminates concat failures door codec mismatches
  - Effort: 1-2h extra
  - Priority: MEDIUM (can be done after V1.0 if concat issues arise)

---

## 📊 Technical Specifications

### Mezzanine Format (Broadcast Standard)
```yaml
Video:
  Codec: H.264 High@4.1
  Pixel Format: yuv420p
  Frame Rate: CFR 30fps (or 60fps for action content)
  SAR: 1:1 (Square Pixel)
  Timebase: 1/90000 (broadcast standard)

Audio:
  Codec: AAC
  Sample Rate: 48kHz
  Channels: Stereo
  Bitrate: 192kbps
```

**Waarom mezzanine?**
- Ensures FFmpeg concat demuxer works 100% deterministically
- Prevents codec/format mismatches between clips
- Eliminates A/V sync drift
- Guarantees platform compatibility (YouTube, TikTok, Instagram)

### FFmpeg Strategies

#### Method 1: Concat Demuxer (Fast)
**Use When:** Hard cuts only (no transitions)
**Speed:** 10x faster (no re-encoding)
**Command:**
```bash
# concat.txt:
file 'clip_0_0.mp4'
file 'clip_0_1.mp4'
file 'clip_0_2.mp4'

ffmpeg -f concat -safe 0 -i concat.txt -c copy output.mp4
```

#### Method 2: Filter Complex (Quality)
**Use When:** Crossfades required
**Speed:** Slower (full re-encode)
**Command:**
```bash
ffmpeg \
  -i clip_0_0.mp4 -i clip_0_1.mp4 -i clip_0_2.mp4 \
  -filter_complex "[0:v][1:v]xfade=duration=0.3:offset=2.2[v01]; \
                   [v01][2:v]xfade=duration=0.3:offset=14.6[vout]; \
                   [0:a][1:a]acrossfade=d=0.3:c1=exp:c2=exp[a01]; \
                   [a01][2:a]acrossfade=d=0.3:c1=exp:c2=exp[aout]" \
  -map "[vout]" -map "[aout]" output.mp4
```

### Quality Standards

| Metric | Target | Validation Method |
|--------|--------|-------------------|
| **A/V Sync** | ±1 frame (0.033s @ 30fps) | FFmpeg framepts analysis |
| **Loudness** | -14 LUFS (social media) | EBU R128 measurement (optional V1.1) |
| **Duration Accuracy** | ±0.1s | FFprobe duration check |
| **File Integrity** | 100% playable | Atomic moves, validation probe |

---

## ⏱️ Timeline

| Fase | Deliverables | Tijd | Dependencies |
|------|--------------|------|--------------|
| **FASE 1** | VideoStitcher core class | 3-4h | None |
| **FASE 2** | Crossfades + quality validation | 2-3h | FASE 1 |
| **FASE 3** | Celery + DB + API + Frontend | 2-3h | FASE 1 |
| **FASE 4** | Testing + Context7 validation | 1-2h | FASE 1-3 |
| **TOTAAL** | Complete implementation | **6-8h** | - |

---

## 🎯 Success Criteria

Dit project is **compleet** wanneer:

### Functional
- [ ] Gebruiker selecteert 1 moment → krijgt 1 finale clip (niet 6 losse)
- [ ] Final clip heeft intelligente camera angle changes (zoals Cinema-MVP plande)
- [ ] Audio is sync (geen gaps, no clicks, smooth transitions)
- [ ] Video preview speelt af in browser

### Technical
- [ ] VideoStitcher class geïmplementeerd met `stitch_moment()` method
- [ ] Mezzanine format validation (prevent concat failures)
- [ ] Both methods werkend: hard cuts (fast) + crossfades (quality)
- [ ] A/V sync validation (±1 frame tolerance)
- [ ] Celery task async (don't block API)
- [ ] Database migration applied (`final_clip_path` column)
- [ ] API endpoint returns final clip URL
- [ ] Frontend toont download link + video player

### Quality
- [ ] Context7 validation 8+/10
- [ ] Security: FFmpeg command injection prevented
- [ ] Performance: Concat demuxer for hard cuts (10x faster)
- [ ] Error handling: Missing files, FFmpeg failures, validation errors
- [ ] Tests: End-to-end workflow test passes

---

## 📚 Resources

### Internal Documentation
- [VIDEO_STITCHER_CONTRACT.md](./VIDEO_STITCHER_CONTRACT.md) - Complete implementation contract
- [OUT_OF_SCOPE.md](./OUT_OF_SCOPE.md) - Future features
- [/docs/CINEMA_MVP_V3.2_IMPLEMENTATION.md](../../docs/CINEMA_MVP_V3.2_IMPLEMENTATION.md) - V3.2 architecture
- [video-stitcher-spec.md](../video-stitcher-spec.md) - Original single-file spec (pre-contract)

### External References
- FFmpeg concat demuxer: https://ffmpeg.org/ffmpeg-formats.html#concat-1
- FFmpeg xfade filter: https://ffmpeg.org/ffmpeg-filters.html#xfade
- EBU R128 loudness: https://tech.ebu.ch/docs/r/r128.pdf
- Mezzanine formats: SMPTE standards for broadcast interchange

---

**Status:** 🟡 Ready for implementation
**Last Updated:** 2025-10-19
**Maintainer:** AgentOS Development Team
