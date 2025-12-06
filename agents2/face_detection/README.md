# Face Detection Agents - v2.8.0 Advanced Tracking

Industry-standard face detection with multi-frame analysis and dynamic tracking.

## 🎯 Available Agents

### face_detector_mediapipe.py - **ENHANCED: Multi-Frame Detection**
- **Purpose**: Multi-frame face detection with movement compensation
- **NEW Features**:
  - ✅ **Multi-Frame Sampling**: Analyzes faces every 3 seconds through video
  - ✅ **Movement Analysis**: Tracks face movement patterns across frames
  - ✅ **Weighted Averaging**: Higher confidence faces get more weight
  - ✅ **Face Grouping**: Groups same person across multiple frames
- **Input**: 
  ```json
  {
    "video_path": "path/to/video.mp4",    // NEW: Video support
    "image_path": "path/to/image.jpg",    // Still supported
    "sample_interval": 3.0,               // NEW: Seconds between samples
    "confidence": 0.4                     // NEW: Lower threshold
  }
  ```
- **Output**: 
  ```json
  {
    "faces": [{
      "x": 226, "y": 111, "width": 180, "height": 200,
      "confidence": 0.78, "center_x": 0.52, "center_y": 0.31,
      "movement_range": {"width": 45, "height": 23},  // NEW
      "frames_in_group": 4                            // NEW
    }],
    "frames_sampled": 8,                              // NEW
    "method_used": "mediapipe_multiframe"             // NEW
  }
  ```
- **Usage**: `python face_detector_mediapipe.py '{"video_path": "video.mp4", "sample_interval": 2.0}'`

### face_tracker_dynamic.py - **NEW: Industry-Standard Tracking** 
- **Purpose**: Frame-by-frame face tracking like TikTok/Instagram
- **Technology**: OpenCV object tracking (CSRT/KCF/MOSSE)
- **Features**:
  - ✅ **Camera-Like Following**: Smooth movement that follows faces
  - ✅ **Tracking Algorithms**: Industry-standard OpenCV trackers
  - ✅ **Smoothing Factor**: Prevents jerky camera movement (0.3 default)
  - ✅ **Face Margin**: 25% buffer around face prevents cut-off
- **Input**:
  ```json
  {
    "video_path": "video.mp4",
    "target_aspect_ratio": "9:16",
    "tracker_type": "KCF",           // CSRT/KCF/MOSSE
    "smoothing_factor": 0.3,        // 0.1-0.9 (higher = smoother)
    "face_margin": 0.25,            // 0.2-0.5 (face area margin)
    "initial_faces": [...]          // From face_detector_mediapipe
  }
  ```
- **Output**: Frame-by-frame tracking data with crop coordinates
- **Usage**: `python face_tracker_dynamic.py '{"video_path": "video.mp4", "initial_faces": [...]}'`

### face_detector.py
- **Purpose**: Legacy face detection implementation  
- **Status**: Maintained for compatibility
- **Input**: Image path and detection parameters
- **Output**: Basic face detection results
- **Usage**: `python face_detector.py '{"image_path": "image.jpg"}'`

## 🚀 Integration with Video Pipeline

**Celery Workflow Integration** (`tasks/video_processing.py`):
```python
# Dynamic face tracking workflow:
faces = detect_faces(video_path)  # Multi-frame detection
↓
tracking_data = track_faces_through_video(video_path, faces)  # Dynamic tracking
↓ 
cut_videos_with_tracking(tracking_data)  # Camera-following cuts
```

**Result**: Gezichten blijven perfect in frame door hele video, zoals professionele camera operator.

## 🔧 External Usage
All agents support command line JSON interface for external system integration.