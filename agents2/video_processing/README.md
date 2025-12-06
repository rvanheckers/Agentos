# Video Processing Agents - v2.8.0 Dynamic Face Tracking

Comprehensive video editing with industry-standard face tracking and dynamic cropping.

## 🎯 Available Agents

### video_cutter.py - **ENHANCED: Dual Output Generation**
- **Purpose**: Cut video segments with smart cropping support
- **NEW Features**:
  - ✅ **Dual File Output**: Creates both original and cropped versions
  - ✅ **Smart Cropping**: Uses crop coordinates from intelligent_cropper
  - ✅ **FFmpeg Integration**: Professional-grade video processing
  - ✅ **Fallback Support**: Graceful degradation when cropping fails
- **Input**:
  ```json
  {
    "video_path": "video.mp4",
    "cuts": [{
      "start_time": 10.0, "end_time": 25.0,
      "output_name": "clip_1"
    }],
    "output_path": "./io/output/job_123",
    "crop_coordinates": {              // NEW: From intelligent_cropper
      "x": 180, "y": 50, "width": 405, "height": 720
    },
    "target_aspect_ratio": "9:16"       // NEW: Target format
  }
  ```
- **Output**:
  ```json
  {
    "success": true,
    "cut_videos": [{
      "path": "./io/output/job_123/clip_1.mp4",         // Cropped version
      "original_path": "./io/output/job_123/clip_1_original.mp4",  // NEW
      "duration": 15.0,
      "size": 1215124,
      "original_size": 2450248,          // NEW
      "crop_method": "smart_crop_9_16",  // NEW
      "crop_applied": true               // NEW
    }]
  }
  ```
- **Usage**: `python video_cutter.py '{"video_path": "video.mp4", "cuts": [...], "crop_coordinates": {...}}'`

### video_cutter_dynamic.py - **NEW: Industry-Standard Dynamic Cutting**
- **Purpose**: Dynamic face-following video cutting like TikTok/Instagram
- **Technology**: FFmpeg with variable crop coordinates + OpenCV tracking data
- **Features**:
  - ✅ **Frame-by-Frame Cropping**: Uses tracking data for smooth movement
  - ✅ **Camera-Like Behavior**: Follows faces like professional camera operator
  - ✅ **Smooth Transitions**: Temporal weighting prevents abrupt movements
  - ✅ **Crop Zone Generation**: Groups similar positions for optimization
- **Input**:
  ```json
  {
    "video_path": "video.mp4",
    "cuts": [{"start_time": 10.0, "end_time": 25.0}],
    "tracking_data": [{                  // From face_tracker_dynamic
      "frame_number": 240,
      "timestamp": 10.0,
      "crop_coordinates": {"x": 180, "y": 50, "width": 405, "height": 720},
      "face_position": {"x": 300, "y": 200, "width": 150, "height": 180}
    }],
    "target_aspect_ratio": "9:16"
  }
  ```
- **Output**: Dynamic cropped video with perfect face tracking
- **Usage**: `python video_cutter_dynamic.py '{"video_path": "video.mp4", "tracking_data": [...]}'`

### video_downloader.py
- **Purpose**: Download videos from URLs (YouTube, Vimeo, etc.)
- **Input**: `{"url": "https://youtube.com/watch?v=...", "quality": "best"}`
- **Output**: Downloaded video file with metadata
- **Usage**: `python video_downloader.py '{"url": "https://example.com/video.mp4"}'`

### thumbnail_generator.py
- **Purpose**: Generate video thumbnails at specific timestamps
- **Input**: `{"video_path": "video.mp4", "timestamp": 5.0}`
- **Output**: Thumbnail image file
- **Usage**: `python thumbnail_generator.py '{"video_path": "video.mp4", "timestamp": 5}'`

### visual_effects.py
- **Purpose**: Apply visual effects to videos
- **Input**: `{"video_path": "video.mp4", "effects": ["blur", "sepia"]}`
- **Output**: Video with applied effects
- **Usage**: `python visual_effects.py '{"video_path": "video.mp4", "effects": ["blur"]}'`

## 🚀 Integration with Face Tracking Pipeline

**Enhanced Celery Workflow** (`tasks/video_processing.py`):
```python
# Industry-standard dynamic video processing:
faces_with_movement = detect_faces_multiframe(video_path)        # Multi-frame sampling
↓
tracking_data = track_faces_through_video(video_path, faces)     # OpenCV tracking  
↓
dynamic_cuts = cut_video_with_tracking(tracking_data)           # Camera-following cuts
↓
dual_output = {original: "clip_1_original.mp4", tracked: "clip_1.mp4"}
```

**Automatic Method Selection**:
- **Dynamic Tracking**: Used when faces detected (industry-standard approach)
- **Static Cropping**: Fallback when no faces or tracking fails
- **Performance Logging**: Tracks method used for analytics

**File Output Structure**:
```
io/output/job_123/
├── clip_1_original.mp4    # 16:9 original format
├── clip_1.mp4             # 9:16 tracked/cropped format  
├── clip_2_original.mp4    # Multiple clips supported
└── clip_2.mp4
```

## 🔧 External Usage
Complete video processing pipeline accessible via JSON interface for external integration.