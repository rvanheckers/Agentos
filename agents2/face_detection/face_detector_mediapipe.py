#!/usr/bin/env python3
"""
Simple Face Detector Agent - Based on clipper_intelligent.py
============================================================

Simplified face detection using MediaPipe from the working backup.
Falls back gracefully when MediaPipe is not available.
"""

import json
import sys
import os
import time

# MediaPipe imports with fallback
try:
    import cv2
    import mediapipe as mp
    FACE_DETECTION_AVAILABLE = True
except ImportError:
    FACE_DETECTION_AVAILABLE = False

class SimpleFaceDetector:
    """
    Simple face detector using MediaPipe (based on working clipper_intelligent.py)
    """

    def __init__(self):
        self.version = "1.0.0"
        self.face_detection = None
        self.face_detection_available = False

        if FACE_DETECTION_AVAILABLE:
            try:
                # Initialize MediaPipe Face Detection (same as clipper_intelligent)
                self.mp_face_detection = mp.solutions.face_detection
                self.face_detection = self.mp_face_detection.FaceDetection(
                    model_selection=1,  # Full-range model
                    min_detection_confidence=0.5
                )
                self.face_detection_available = True
            except Exception:
                self.face_detection_available = False

    def detect_faces(self, input_data):
        """
        Detect faces in image/video with multi-frame sampling for videos.

        Args:
            input_data: {
                "image_path": str,          # path to image file
                "video_path": str,          # path to video file (alternative to image_path)
                "output_path": str,         # output path for result
                "draw_boxes": bool,         # draw bounding boxes (default: True)
                "confidence": float,        # detection confidence (default: 0.5)
                "sample_interval": float    # seconds between samples for video (default: 2.0)
            }

        Returns:
            {
                "success": bool,
                "faces_detected": int,
                "faces": List[{
                    "x": int, "y": int, "width": int, "height": int,
                    "confidence": float,
                    "center_x": float, "center_y": float
                }],
                "output_image": str,        # path to output image with boxes
                "processing_time": float,
                "method_used": str,
                "agent_version": str,
                "frames_sampled": int       # number of frames analyzed
            }
        """

        start_time = time.time()

        try:
            # Validate input - support both image and video
            image_path = input_data.get("image_path")
            video_path = input_data.get("video_path")
            
            if not image_path and not video_path:
                return self._error("Either image_path or video_path is required")

            target_path = image_path or video_path
            if not os.path.exists(target_path):
                return self._error(f"File not found: {target_path}")

            output_path = input_data.get("output_path", "faces_detected.jpg")
            draw_boxes = input_data.get("draw_boxes", True)
            confidence_threshold = input_data.get("confidence", 0.5)
            sample_interval = input_data.get("sample_interval", 2.0)

            # Detect faces - choose method based on input type
            if self.face_detection_available:
                if video_path:
                    faces, frames_sampled = self._detect_video_multiframe(video_path, confidence_threshold, sample_interval)
                    method_used = "mediapipe_multiframe"
                else:
                    faces = self._detect_with_mediapipe(image_path, confidence_threshold)
                    frames_sampled = 1
                    method_used = "mediapipe_single"
            else:
                # Fallback: return mock data
                faces = self._mock_detection(target_path)
                frames_sampled = 1
                method_used = "mock"

            # Draw boxes if requested
            output_image_path = None
            if draw_boxes and faces and image_path:
                output_image_path = self._draw_face_boxes(image_path, faces, output_path)

            processing_time = time.time() - start_time

            return {
                "success": True,
                "faces_detected": len(faces),
                "faces": faces,
                "output_image": output_image_path or output_path,
                "processing_time": processing_time,
                "method_used": method_used,
                "agent_version": self.version,
                "frames_sampled": frames_sampled
            }

        except Exception as e:
            return self._error(f"Face detection failed: {str(e)}")

    def _detect_with_mediapipe(self, image_path, confidence_threshold):
        """Detect faces using MediaPipe (single image)"""
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                return []

            frame_h, frame_w = image.shape[:2]
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Detect faces
            results = self.face_detection.process(rgb_image)

            if not results.detections:
                return []

            faces = []
            for detection in results.detections:
                if detection.score[0] < confidence_threshold:
                    continue

                bbox = detection.location_data.relative_bounding_box

                # Convert normalized coordinates to pixel coordinates
                x = int(bbox.xmin * frame_w)
                y = int(bbox.ymin * frame_h)
                w = int(bbox.width * frame_w)
                h = int(bbox.height * frame_h)

                # Calculate center
                center_x = (x + w / 2) / frame_w
                center_y = (y + h / 2) / frame_h

                faces.append({
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h,
                    "confidence": float(detection.score[0]),
                    "center_x": center_x,
                    "center_y": center_y
                })

            return faces

        except Exception as e:
            print(f"MediaPipe detection error: {e}", file=sys.stderr)
            return []

    def _detect_video_multiframe(self, video_path, confidence_threshold, sample_interval):
        """Multi-frame face detection for better tracking through video"""
        try:
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            # Calculate frame indices to sample
            frame_indices = []
            current_time = 0
            while current_time < duration:
                frame_idx = int(current_time * fps)
                if frame_idx < total_frames:
                    frame_indices.append(frame_idx)
                current_time += sample_interval
            
            # Ensure we sample at least the first frame
            if not frame_indices:
                frame_indices = [0]
            
            all_faces = []
            frames_processed = 0
            
            for frame_idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if not ret:
                    continue
                    
                frame_h, frame_w = frame.shape[:2]
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Detect faces in this frame
                results = self.face_detection.process(rgb_frame)
                
                if results.detections:
                    for detection in results.detections:
                        if detection.score[0] < confidence_threshold:
                            continue
                            
                        bbox = detection.location_data.relative_bounding_box
                        
                        # Convert to pixel coordinates
                        x = int(bbox.xmin * frame_w)
                        y = int(bbox.ymin * frame_h)
                        w = int(bbox.width * frame_w)
                        h = int(bbox.height * frame_h)
                        
                        # Store with frame timestamp for averaging
                        all_faces.append({
                            "x": x,
                            "y": y,
                            "width": w,
                            "height": h,
                            "confidence": float(detection.score[0]),
                            "frame_time": frame_idx / fps,
                            "frame_w": frame_w,
                            "frame_h": frame_h
                        })
                
                frames_processed += 1
            
            cap.release()
            
            # Calculate averaged face positions
            averaged_faces = self._average_face_positions(all_faces)
            
            return averaged_faces, frames_processed
            
        except Exception as e:
            print(f"Multi-frame detection error: {e}", file=sys.stderr)
            return [], 0
    
    def _average_face_positions(self, all_faces):
        """Calculate movement-compensated face positions across frames"""
        if not all_faces:
            return []
        
        # Group faces by proximity (same person across frames)
        face_groups = []
        proximity_threshold = 120  # pixels - increased for more grouping
        
        for face in all_faces:
            # Find existing group this face belongs to
            assigned = False
            for group in face_groups:
                # Check if face is close to any face in this group
                for existing_face in group:
                    distance = ((face["x"] - existing_face["x"])**2 + 
                               (face["y"] - existing_face["y"])**2)**0.5
                    if distance < proximity_threshold:
                        group.append(face)
                        assigned = True
                        break
                if assigned:
                    break
            
            # Create new group if not assigned
            if not assigned:
                face_groups.append([face])
        
        # Calculate movement-compensated position for each group
        averaged_faces = []
        for group in face_groups:
            if not group:
                continue
                
            # Calculate movement boundaries (min/max positions across all frames)
            min_x = min(f["x"] for f in group)
            max_x = max(f["x"] + f["width"] for f in group)
            min_y = min(f["y"] for f in group)
            max_y = max(f["y"] + f["height"] for f in group)
            
            # Calculate movement range
            movement_width = max_x - min_x
            movement_height = max_y - min_y
            
            # Calculate weighted averages (higher confidence = more weight)
            total_weight = sum(f["confidence"] for f in group)
            
            avg_x = sum(f["x"] * f["confidence"] for f in group) / total_weight
            avg_y = sum(f["y"] * f["confidence"] for f in group) / total_weight
            avg_w = sum(f["width"] * f["confidence"] for f in group) / total_weight
            avg_h = sum(f["height"] * f["confidence"] for f in group) / total_weight
            avg_conf = sum(f["confidence"] for f in group) / len(group)
            
            # Use the frame dimensions from the first face in group
            frame_w = group[0]["frame_w"]
            frame_h = group[0]["frame_h"]
            
            # MOVEMENT COMPENSATION: Expand bounding box to include movement range
            # Add 30% buffer around movement area to prevent faces going out of frame
            movement_buffer_x = movement_width * 0.3
            movement_buffer_y = movement_height * 0.3
            
            # Adjust average position to center of movement area
            compensated_x = (min_x + max_x) / 2 - avg_w / 2
            compensated_y = (min_y + max_y) / 2 - avg_h / 2
            
            # Calculate center in normalized coordinates with movement compensation
            center_x = (compensated_x + avg_w / 2) / frame_w
            center_y = (compensated_y + avg_h / 2) / frame_h
            
            # INDUSTRY STANDARD: Preserve temporal metadata for per-moment filtering
            # Calculate average timestamp from all frames in group
            avg_timestamp = sum(f["frame_time"] for f in group) / len(group)
            first_seen = min(f["frame_time"] for f in group)
            last_seen = max(f["frame_time"] for f in group)

            averaged_faces.append({
                "x": int(compensated_x),
                "y": int(compensated_y),
                "width": int(avg_w + movement_buffer_x),
                "height": int(avg_h + movement_buffer_y),
                "confidence": avg_conf,
                "center_x": center_x,
                "center_y": center_y,
                "timestamp": avg_timestamp,  # ← CRITICAL: For per-moment filtering
                "first_seen": first_seen,    # ← OPTIONAL: For debugging
                "last_seen": last_seen,      # ← OPTIONAL: For debugging
                "frames_in_group": len(group),
                "movement_range": {
                    "width": movement_width,
                    "height": movement_height,
                    "buffer_added": {
                        "x": movement_buffer_x,
                        "y": movement_buffer_y
                    }
                }
            })
        
        # Sort by confidence (best faces first)
        averaged_faces.sort(key=lambda f: f["confidence"], reverse=True)
        
        return averaged_faces

    def _mock_detection(self, image_path):
        """Mock face detection for when MediaPipe is not available"""
        return [{
            "x": 100,
            "y": 100,
            "width": 200,
            "height": 200,
            "confidence": 0.95,
            "center_x": 0.5,
            "center_y": 0.4,
            "note": "Mock face detection - MediaPipe not available"
        }]

    def _draw_face_boxes(self, image_path, faces, output_path):
        """Draw bounding boxes around detected faces"""
        try:
            if not FACE_DETECTION_AVAILABLE:
                return output_path

            image = cv2.imread(image_path)
            if image is None:
                return output_path

            # Draw boxes
            for face in faces:
                x, y, w, h = face["x"], face["y"], face["width"], face["height"]
                confidence = face["confidence"]

                # Draw rectangle
                cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # Add confidence text
                text = f"{confidence:.2f}"
                cv2.putText(image, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Save image
            cv2.imwrite(output_path, image)
            return output_path

        except Exception as e:
            print(f"Error drawing boxes: {e}", file=sys.stderr)
            return output_path

    def _error(self, message):
        """Return standardized error response"""
        return {
            "success": False,
            "error": message,
            "error_code": "FACE_DETECTION_ERROR",
            "faces_detected": 0,
            "faces": [],
            "output_image": "",
            "processing_time": 0.0,
            "method_used": "error",
            "agent_version": self.version
        }

def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: python face_detector_simple.py '<json_input>'",
            "error_code": "USAGE_ERROR"
        }))
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])
        detector = SimpleFaceDetector()
        result = detector.detect_faces(input_data)
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
