#!/usr/bin/env python3
"""
Dynamic Face Tracker - Industry Standard Implementation
======================================================

Implements dynamic face tracking with OpenCV object tracking.
Tracks faces frame-by-frame for camera-like following behavior.

INDUSTRY STANDARDS:
- TikTok/Instagram Reels face tracking
- YouTube auto-framing
- Zoom smart cropping
"""

import json
import sys
import os
import time
from typing import Dict, List, Any, Tuple

# OpenCV imports with fallback
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
    
    # Available trackers (industry standard) - Updated for OpenCV 4.x
    TRACKER_TYPES = {}
    try:
        TRACKER_TYPES['CSRT'] = cv2.legacy.TrackerCSRT_create    # Best accuracy (slower)
        TRACKER_TYPES['KCF'] = cv2.legacy.TrackerKCF_create      # Good balance  
        TRACKER_TYPES['MOSSE'] = cv2.legacy.TrackerMOSSE_create  # Fastest (less accurate)
    except AttributeError:
        # Fallback for older OpenCV versions or missing legacy module
        try:
            TRACKER_TYPES['KCF'] = cv2.TrackerKCF_create
            TRACKER_TYPES['CSRT'] = cv2.TrackerCSRT_create  
            TRACKER_TYPES['MOSSE'] = cv2.TrackerMOSSE_create
        except AttributeError:
            # No tracking available
            pass
except ImportError:
    OPENCV_AVAILABLE = False
    TRACKER_TYPES = {}

class DynamicFaceTracker:
    """
    Industry-standard dynamic face tracking for video cropping.
    
    Implements camera-like behavior that follows faces through entire video,
    similar to TikTok/Instagram auto-framing.
    """
    
    def __init__(self):
        self.version = "1.0.0"
        self.opencv_available = OPENCV_AVAILABLE
        
    def track_faces_through_video(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Track faces through entire video for dynamic cropping.
        
        Args:
            input_data: {
                "video_path": str,
                "target_aspect_ratio": str,  # "9:16"
                "tracker_type": str,         # "CSRT", "KCF", "MOSSE"
                "smoothing_factor": float,   # 0.1-0.9 (higher = smoother)
                "face_margin": float,        # 0.2-0.5 (face area margin)
                "initial_faces": List[dict]  # from face detector
            }
            
        Returns:
            {
                "success": bool,
                "tracking_data": List[{
                    "frame_number": int,
                    "timestamp": float,
                    "crop_coordinates": {"x": int, "y": int, "width": int, "height": int},
                    "face_position": {"x": int, "y": int, "width": int, "height": int},
                    "tracking_confidence": float
                }],
                "crop_zones": List[{
                    "start_time": float,
                    "end_time": float, 
                    "crop_coordinates": {"x": int, "y": int, "width": int, "height": int}
                }],
                "processing_time": float,
                "frames_tracked": int,
                "method_used": str
            }
        """
        
        start_time = time.time()
        
        try:
            if not self.opencv_available:
                return self._error("OpenCV not available for dynamic tracking")
                
            video_path = input_data.get("video_path")
            if not video_path or not os.path.exists(video_path):
                return self._error("Valid video_path required")
                
            initial_faces = input_data.get("initial_faces", [])
            if not initial_faces:
                return self._error("initial_faces required from face detector")
                
            # Parameters
            tracker_type = input_data.get("tracker_type", "KCF")  # Good balance
            smoothing = input_data.get("smoothing_factor", 0.3)
            face_margin = input_data.get("face_margin", 0.3)
            target_aspect = input_data.get("target_aspect_ratio", "9:16")
            
            # Execute dynamic tracking
            tracking_result = self._track_primary_face(
                video_path, initial_faces[0], tracker_type, 
                smoothing, face_margin, target_aspect
            )
            
            if tracking_result["success"]:
                processing_time = time.time() - start_time
                tracking_result["processing_time"] = processing_time
                tracking_result["agent_version"] = self.version
                
            return tracking_result
            
        except Exception as e:
            return self._error(f"Dynamic tracking failed: {str(e)}")
    
    def _track_primary_face(self, video_path: str, primary_face: dict, 
                           tracker_type: str, smoothing: float, 
                           face_margin: float, target_aspect: str) -> Dict[str, Any]:
        """Track primary face through entire video"""
        
        try:
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if fps <= 0 or total_frames <= 0:
                return self._error("Invalid video properties")
                
            # Get video dimensions
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Calculate target crop dimensions
            target_ratio = self._parse_aspect_ratio(target_aspect)
            if target_ratio > (frame_width / frame_height):
                crop_width = frame_width
                crop_height = int(frame_width / target_ratio)
            else:
                crop_height = frame_height  
                crop_width = int(frame_height * target_ratio)
                
            # Initialize tracker on first frame
            ret, frame = cap.read()
            if not ret:
                return self._error("Could not read first frame")
                
            # Setup initial tracking box around primary face
            face_x = primary_face.get("x", 0)
            face_y = primary_face.get("y", 0) 
            face_w = primary_face.get("width", 100)
            face_h = primary_face.get("height", 100)
            
            # Expand tracking box with margin
            margin_x = int(face_w * face_margin)
            margin_y = int(face_h * face_margin)
            
            track_box = (
                max(0, face_x - margin_x),
                max(0, face_y - margin_y),
                min(face_w + 2*margin_x, frame_width),
                min(face_h + 2*margin_y, frame_height)
            )
            
            # Create tracker
            if tracker_type not in TRACKER_TYPES:
                tracker_type = "KCF"
            tracker = TRACKER_TYPES[tracker_type]()
            
            # Initialize tracker
            success = tracker.init(frame, track_box)
            if not success:
                return self._error("Tracker initialization failed")
                
            # Track through all frames
            tracking_data = []
            crop_zones = []
            frames_tracked = 0
            
            # Previous crop position for smoothing
            prev_crop_x = (frame_width - crop_width) // 2
            prev_crop_y = (frame_height - crop_height) // 2
            
            frame_number = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                # Update tracker
                success, bbox = tracker.update(frame)
                timestamp = frame_number / fps
                
                if success:
                    # Get tracked face position
                    track_x, track_y, track_w, track_h = bbox
                    face_center_x = track_x + track_w / 2
                    face_center_y = track_y + track_h / 2
                    
                    # Calculate optimal crop position to keep face centered
                    target_crop_x = int(face_center_x - crop_width / 2)
                    target_crop_y = int(face_center_y - crop_height / 2)
                    
                    # Apply smoothing to prevent jerky movement (INDUSTRY STANDARD)
                    crop_x = int(prev_crop_x * smoothing + target_crop_x * (1 - smoothing))
                    crop_y = int(prev_crop_y * smoothing + target_crop_y * (1 - smoothing))
                    
                    # Ensure crop stays within video bounds
                    crop_x = max(0, min(crop_x, frame_width - crop_width))
                    crop_y = max(0, min(crop_y, frame_height - crop_height))
                    
                    # Store tracking data
                    tracking_data.append({
                        "frame_number": frame_number,
                        "timestamp": timestamp,
                        "crop_coordinates": {
                            "x": crop_x,
                            "y": crop_y,
                            "width": crop_width,
                            "height": crop_height
                        },
                        "face_position": {
                            "x": int(track_x),
                            "y": int(track_y),
                            "width": int(track_w),
                            "height": int(track_h)
                        },
                        "tracking_confidence": 1.0  # OpenCV trackers don't provide confidence
                    })
                    
                    prev_crop_x = crop_x
                    prev_crop_y = crop_y
                    frames_tracked += 1
                else:
                    # Tracking lost - use previous position
                    tracking_data.append({
                        "frame_number": frame_number,
                        "timestamp": timestamp,
                        "crop_coordinates": {
                            "x": prev_crop_x,
                            "y": prev_crop_y,
                            "width": crop_width,
                            "height": crop_height
                        },
                        "face_position": None,
                        "tracking_confidence": 0.0
                    })
                
                frame_number += 1
                
            cap.release()
            
            # Generate crop zones for video cutting (group similar positions)
            crop_zones = self._generate_crop_zones(tracking_data)
            
            return {
                "success": True,
                "tracking_data": tracking_data,
                "crop_zones": crop_zones,
                "frames_tracked": frames_tracked,
                "total_frames": total_frames,
                "method_used": f"opencv_{tracker_type.lower()}_tracking"
            }
            
        except Exception as e:
            return self._error(f"Tracking failed: {str(e)}")
    
    def _generate_crop_zones(self, tracking_data: List[dict]) -> List[dict]:
        """Generate crop zones by grouping similar crop positions"""
        if not tracking_data:
            return []
            
        zones = []
        current_zone = None
        zone_threshold = 50  # pixels difference for new zone
        
        for data in tracking_data:
            crop = data["crop_coordinates"]
            
            if not current_zone:
                # Start first zone
                current_zone = {
                    "start_time": data["timestamp"],
                    "end_time": data["timestamp"],
                    "crop_coordinates": crop,
                    "frame_count": 1
                }
            else:
                # Check if crop position is similar to current zone
                prev_crop = current_zone["crop_coordinates"]
                distance = ((crop["x"] - prev_crop["x"])**2 + 
                           (crop["y"] - prev_crop["y"])**2)**0.5
                
                if distance < zone_threshold:
                    # Extend current zone
                    current_zone["end_time"] = data["timestamp"]
                    current_zone["frame_count"] += 1
                else:
                    # Start new zone
                    zones.append(current_zone)
                    current_zone = {
                        "start_time": data["timestamp"],
                        "end_time": data["timestamp"],
                        "crop_coordinates": crop,
                        "frame_count": 1
                    }
        
        # Add final zone
        if current_zone:
            zones.append(current_zone)
            
        return zones
    
    def _parse_aspect_ratio(self, ratio_str: str) -> float:
        """Parse aspect ratio string to float"""
        try:
            if ':' in ratio_str:
                width, height = ratio_str.split(':')
                return float(width) / float(height)
            else:
                return float(ratio_str)
        except (ValueError, TypeError, ZeroDivisionError):
            return 9/16  # Default to mobile
    
    def _error(self, message: str) -> Dict[str, Any]:
        """Return standardized error response"""
        return {
            "success": False,
            "error": message,
            "error_code": "DYNAMIC_TRACKING_ERROR",
            "tracking_data": [],
            "crop_zones": [],
            "frames_tracked": 0,
            "agent_version": self.version
        }

def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: python face_tracker_dynamic.py '<json_input>'",
            "error_code": "USAGE_ERROR"
        }))
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
        tracker = DynamicFaceTracker()
        result = tracker.track_faces_through_video(input_data)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get("success", False) else 1)

    except json.JSONDecodeError:
        print(json.dumps({
            "success": False,
            "error": "Invalid JSON input",
            "error_code": "JSON_ERROR"
        }))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_code": "UNEXPECTED_ERROR"
        }))
        sys.exit(1)

if __name__ == "__main__":
    main()