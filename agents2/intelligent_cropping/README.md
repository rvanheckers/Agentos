# Intelligent Cropping Agent - v2.8.0 Movement Compensation

Smart video cropping with advanced face tracking and movement compensation.

## 🎯 Available Agents

### intelligent_cropper.py - **ENHANCED: Movement Compensation**
- **Purpose**: Calculate optimal crop coordinates with movement compensation
- **NEW Features**:
  - ✅ **Movement Compensation**: 15-40% adaptive margin based on face movement
  - ✅ **Safe Zone Cropping**: 25% expansion to prevent faces leaving frame
  - ✅ **Weighted Face Positioning**: Higher confidence faces get priority
  - ✅ **Movement Range Analysis**: Uses actual movement data from multi-frame detection
- **Input**: 
  ```json
  {
    "video_path": "video.mp4",
    "faces": [{                           // From face_detector_mediapipe
      "x": 226, "y": 111, "width": 180, "height": 200,
      "confidence": 0.78,
      "movement_range": {"width": 45, "height": 23}  // NEW: Movement data
    }],
    "target_aspect_ratio": "9:16",        // Mobile format
    "priority": "faces",                  // faces/content/center
    "padding": 0.1                        // Base padding around subjects
  }
  ```
- **Output**: 
  ```json
  {
    "success": true,
    "crop_coordinates": {
      "x": 180, "y": 50,                  // Compensated for movement
      "width": 405, "height": 720         // 9:16 aspect ratio
    },
    "original_resolution": {"width": 1920, "height": 1080},
    "crop_info": {
      "aspect_ratio": "9:16",
      "scale_factor": 0.67,
      "faces_included": 1,
      "crop_method": "face_based"         // face_based/center/content_based
    }
  }
  ```
- **Usage**: `python intelligent_cropper.py '{"video_path": "video.mp4", "faces": [...], "target_aspect_ratio": "9:16"}'`

**🔧 Movement Compensation Logic**:
1. **Analyze Movement**: Calculate movement range from multi-frame face data
2. **Adaptive Margins**: 15-40% margin based on actual face movement detected
3. **Safe Zone Expansion**: 25% minimum expansion to prevent cut-off between sample points
4. **Weighted Positioning**: Higher confidence faces get more influence on crop position

**🎯 Aspect Ratio Support**:
- **9:16** - TikTok/Instagram Reels (primary target)
- **16:9** - YouTube/landscape format  
- **1:1** - Instagram square posts
- **Custom** - Any ratio via "width:height" format

## 🚀 Integration with Face Detection

**Enhanced Pipeline Flow**:
```
Multi-Frame Face Detection (every 3s) 
↓
Movement Range Analysis
↓ 
Movement Compensation Calculation
↓
Safe Zone Crop Coordinates
↓
Dynamic Video Cutting
```

**Celery Integration** (`tasks/video_processing.py`):
```python
# Enhanced workflow:
faces_with_movement = detect_faces_multiframe(video_path)
↓
compensated_crop = intelligent_crop_with_movement(faces_with_movement)
↓
dynamic_cut_with_tracking(compensated_crop)
```

## 🔧 External Usage
Supports command line JSON interface for external system integration and standalone usage.