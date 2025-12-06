# AgentOS Architecture Documentation
**Last Updated:** 2025-10-15

---

## Overview

This directory contains **architecture decision records (ADRs)**, **design documents**, and **technical deep-dives** for AgentOS video processing pipeline.

Each document captures the **why** behind major technical decisions, performance optimizations, and system design trade-offs.

---

## Document Index

### 🎬 Cinema Mode & Video Processing

| Document | Version | Description | Status |
|----------|---------|-------------|--------|
| [CINEMA_MODE_SHOT_SEQUENCING_V3.2.md](./CINEMA_MODE_SHOT_SEQUENCING_V3.2.md) | 3.2.0 | Cinematographic shot sequencing for split-screen videos. Explains why more clips are generated and how establishing → single → reaction sequences are planned. | ✅ Production |
| [SPLIT_SCREEN_DETECTION_AND_FALLBACK.md](./SPLIT_SCREEN_DETECTION_AND_FALLBACK.md) | 3.2.0 | Automatic split-screen detection logic and fallback behavior. Answers: "Do normal videos still work?" Covers face clustering, confidence thresholds, and backwards compatibility. | ✅ Production |

### 👤 Face Detection & Optimization

| Document | Version | Description | Status |
|----------|---------|-------------|--------|
| [FACE_DETECTION_EFFICIENCY_V2.2.2.md](./FACE_DETECTION_EFFICIENCY_V2.2.2.md) | 2.2.2 | Face detection performance optimization. Covers adaptive sampling, frame skipping strategies, and computational budget management. | ✅ Production |
| [FACE_GROUPING_OPTIMIZATION_PLAN.md](./FACE_GROUPING_OPTIMIZATION_PLAN.md) | 2.2.x | Face grouping and clustering optimization strategy. Reduces redundant face detection calls across video processing pipeline. | 📋 Planning |

### 🎯 Threshold & Validation

| Document | Version | Description | Status |
|----------|---------|-------------|--------|
| [THRESHOLD_FIX_V2.2.1.md](./THRESHOLD_FIX_V2.2.1.md) | 2.2.1 | Moment detection threshold calibration fix. Addresses false positive/negative rates in moment detection. | ✅ Production |
| [VALIDATION_V2.2.1_V2.2.2.md](./VALIDATION_V2.2.1_V2.2.2.md) | 2.2.x | Validation framework for V2.2.1 and V2.2.2 releases. Testing strategy and acceptance criteria. | ✅ Complete |

### 📝 Transcription & Audio

| Document | Version | Description | Status |
|----------|---------|-------------|--------|
| [TRANSCRIPT_CHUNKING_STRATEGY.md](./TRANSCRIPT_CHUNKING_STRATEGY.md) | - | Audio transcription chunking strategy. Optimizes Whisper API usage with smart segment splitting. | ✅ Production |

---

## Document Lifecycle

### Status Definitions

| Status | Meaning |
|--------|---------|
| 📋 Planning | Document in draft stage, design under discussion |
| 🚧 In Progress | Implementation ongoing, document being updated |
| ✅ Production | Implemented and deployed, document reflects production behavior |
| ✅ Complete | Implementation complete, document archived for historical reference |
| ⚠️ Deprecated | Superseded by newer design, kept for historical context |

---

## Key Architectural Concepts

### Cinema Mode V3.2 (NEW)

**What:** Cinematographic shot sequencing for split-screen videos
**Why:** Transform static split-screen crops into dynamic multi-shot sequences
**Impact:** 3-4× more output clips per moment, professional editing quality

**Core Innovation:**
```
1 moment (15s) → 4 sub-moments:
├─ Establishing shot (2.5s): Context
├─ Single shot (6.5s): Active speaker
├─ Reaction shot (3.0s): Listener
└─ Single shot (3.0s): Return to speaker
```

**Read:** [CINEMA_MODE_SHOT_SEQUENCING_V3.2.md](./CINEMA_MODE_SHOT_SEQUENCING_V3.2.md)

---

### Split-Screen Detection (NEW)

**What:** Automatic layout detection with confidence scoring
**Why:** Apply appropriate cropping strategy per video type
**Impact:** No manual configuration needed, backwards compatible

**Detection Methods:**
1. **Face clustering**: Spatial distribution analysis
2. **Visual edge detection**: OpenCV Canny edge detection
3. **Confidence threshold**: > 0.7 for split-screen detection

**Fallback Behavior:**
```
Split-screen detected? (confidence > 0.7)
├─ YES → Panel boundary cropping (V3.2)
└─ NO  → Traditional cinematography (rule of thirds)
```

**Read:** [SPLIT_SCREEN_DETECTION_AND_FALLBACK.md](./SPLIT_SCREEN_DETECTION_AND_FALLBACK.md)

---

### Face Detection Efficiency

**What:** Adaptive sampling strategy for face detection
**Why:** Reduce computational cost without sacrificing accuracy
**Impact:** 60-80% reduction in face detection calls

**Strategy:**
- Variable frame sampling rate (0.5 fps → 2 fps based on motion)
- Shot boundary awareness (higher sampling at cuts)
- Temporal interpolation for skipped frames

**Read:** [FACE_DETECTION_EFFICIENCY_V2.2.2.md](./FACE_DETECTION_EFFICIENCY_V2.2.2.md)

---

### Transcription Chunking

**What:** Smart audio segment splitting for Whisper API
**Why:** Optimize API usage and reduce transcription cost
**Impact:** 30-50% cost reduction, improved accuracy at boundaries

**Strategy:**
- Split on silence detection (> 500ms pause)
- Maintain semantic boundaries (sentence-aware)
- 30-second target chunk size with 1-second overlap

**Read:** [TRANSCRIPT_CHUNKING_STRATEGY.md](./TRANSCRIPT_CHUNKING_STRATEGY.md)

---

## Version History

### V3.2.0 (2025-10-15) - Cinema Mode Shot Sequencing

**Major Changes:**
- ✅ Split-screen shot sequencing (establishing → single → reaction)
- ✅ Automatic layout detection with confidence scoring
- ✅ Panel boundary cropping for split-screen videos
- ✅ Activity-based speaker tracking (audio + visual)
- ✅ Backwards compatibility with traditional cinematography

**Documents:**
- CINEMA_MODE_SHOT_SEQUENCING_V3.2.md (NEW)
- SPLIT_SCREEN_DETECTION_AND_FALLBACK.md (NEW)

### V2.2.2 (2025-10-13) - Face Detection Optimization

**Major Changes:**
- ✅ Adaptive face detection sampling
- ✅ Threshold calibration fix
- ✅ Face grouping optimization

**Documents:**
- FACE_DETECTION_EFFICIENCY_V2.2.2.md
- FACE_GROUPING_OPTIMIZATION_PLAN.md
- THRESHOLD_FIX_V2.2.1.md
- VALIDATION_V2.2.1_V2.2.2.md

---

## Contributing

### Adding New Documentation

When adding a new architecture document:

1. **Use descriptive filename:** `{FEATURE}_{VERSION}.md` (e.g., `CINEMA_MODE_SHOT_SEQUENCING_V3.2.md`)
2. **Include header metadata:**
   ```markdown
   # Document Title
   **Version:** X.Y.Z
   **Last Updated:** YYYY-MM-DD
   **Status:** [Planning|In Progress|Production|Complete|Deprecated]
   ```
3. **Add to this README:** Update the relevant section in the document index
4. **Link related docs:** Cross-reference related architecture documents

### Document Template

```markdown
# Feature Name
**Version:** X.Y.Z
**Last Updated:** YYYY-MM-DD
**Status:** ✅ Production

---

## Executive Summary
[1-2 sentence overview]

## Table of Contents
[Auto-generated or manual TOC]

## Architecture Overview
[Problem statement, solution, design decisions]

## Implementation Details
[Code references, algorithms, data structures]

## Performance Characteristics
[Computational cost, latency, throughput]

## Validation & Testing
[Test coverage, production validation]

## Future Enhancements
[Planned improvements, known limitations]

## Code References
[File paths, line numbers, function names]
```

---

## Contact & Maintenance

**Maintainer:** AgentOS Video Processing Team
**Last Review:** 2025-10-15
**Next Review:** 2025-11-15 (or upon major version bump)

For questions about architecture decisions, consult:
1. This README for overview
2. Specific document for deep-dive
3. Code comments in referenced files
4. Git history for evolution context

---

## Quick Reference

### Most Important Documents for New Contributors

1. **Start here:** [SPLIT_SCREEN_DETECTION_AND_FALLBACK.md](./SPLIT_SCREEN_DETECTION_AND_FALLBACK.md)
   - Understand video processing pipeline behavior
   - Learn when Cinema Mode V3.2 vs traditional composition is used

2. **Then read:** [CINEMA_MODE_SHOT_SEQUENCING_V3.2.md](./CINEMA_MODE_SHOT_SEQUENCING_V3.2.md)
   - Understand why multiple clips are generated per moment
   - Learn shot sequence planning algorithm

3. **For performance:** [FACE_DETECTION_EFFICIENCY_V2.2.2.md](./FACE_DETECTION_EFFICIENCY_V2.2.2.md)
   - Understand computational budget management
   - Learn adaptive sampling strategy

### Most Referenced Code Locations

| Component | File | Key Functions |
|-----------|------|---------------|
| Cinematic Composer | `agents2/video_processing/cinematic_composer.py` | `compose_for_moment_with_sequence()` |
| Layout Detector | `agents2/video_processing/layout_detector.py` | `detect_layout()`, `track_activity_per_region()` |
| Shot Sequence Planner | `agents2/video_processing/shot_sequence_planner.py` | `plan_shot_sequence()` |
| Video Cutter | `agents2/video_processing/video_cutter.py` | `cut_videos()` (line 705-750) |
| Data Contracts | `agents2/schemas/video_processing.py` | `CropsPerMoment`, `SubMoment` |
| Task Orchestration | `tasks/video_processing.py` | `cut_videos()` (line 1116-1154) |

---

## Document Statistics

**Total Documents:** 7
**Production Ready:** 6
**Planning Stage:** 1
**Total Size:** ~78 KB
**Average Document Size:** ~11 KB

**Document Coverage by Category:**
- 🎬 Cinema Mode: 2 docs (29%)
- 👤 Face Detection: 2 docs (29%)
- 🎯 Validation: 2 docs (29%)
- 📝 Transcription: 1 doc (14%)

---

**Last Updated:** 2025-10-15 by AgentOS Architecture Team
