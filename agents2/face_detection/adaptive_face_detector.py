#!/usr/bin/env python3
"""
Adaptive Face Detection System for AgentOS
==========================================

Production-grade face detector with adaptive strategy:
- MediaPipe as primary detector (180+ FPS, optimized for speed)
- YOLOv8-Face as fallback detector (accurate for challenging cases)
- Automatic fallback when average confidence < 0.75

Context7-validated configuration:
- MediaPipe model_selection=1 (full-range, within 5 meters)
- min_detection_confidence=0.5 (MediaPipe default)
- YOLO confidence=0.25 (Context7 standard)
- Frame sampling every 30 frames (1 sec at 30fps)

Security: Inherits from SecureVideoAgent for path validation and resource management
Performance: Targets 95%+ cases using fast MediaPipe path
"""

import json
import sys
import time
import cv2
import mediapipe as mp
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Import security layer from FASE 1
import os
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from agents2.base.secure_agent import SecureVideoAgent


# Optional YOLO fallback (gracefully degrades if not available)
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False


class AdaptiveFaceDetector(SecureVideoAgent):
    """
    Adaptive face detection with MediaPipe primary + YOLO fallback

    Inherits from SecureVideoAgent to ensure:
    - Path validation (prevents traversal attacks)
    - Video file validation (MIME type, size, duration checks)
    - Resource limits (memory, CPU time)
    - Proper cleanup (no file descriptor leaks)

    Architecture:
    1. Try MediaPipe first (fast: 180+ FPS)
    2. Calculate average confidence across detections
    3. If avg_confidence < 0.75 → fallback to YOLO (accurate)
    4. Return unified person-grouped results
    """

    # Context7-validated configuration
    MEDIAPIPE_MODEL_SELECTION = 1  # Full-range model (within 5 meters)
    MEDIAPIPE_MIN_CONFIDENCE = 0.5  # Default per Context7 docs
    YOLO_CONFIDENCE = 0.25  # Context7 standard for YOLO
    FRAME_SAMPLE_RATE = 30  # Process every 30th frame
    FALLBACK_THRESHOLD = 0.75  # Trigger YOLO if MediaPipe avg confidence < this

    def __init__(self):
        """Initialize with security validation and dual detectors"""
        super().__init__()

        # Initialize MediaPipe (primary detector)
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_drawing = mp.solutions.drawing_utils
        self.mediapipe_detector = self.mp_face_detection.FaceDetection(
            model_selection=self.MEDIAPIPE_MODEL_SELECTION,
            min_detection_confidence=self.MEDIAPIPE_MIN_CONFIDENCE
        )

        # Initialize YOLO (fallback detector, if available)
        self.yolo_detector = None
        if YOLO_AVAILABLE:
            try:
                # Try to load YOLOv8n-face model (small, fast)
                # Note: Model will auto-download on first use
                self.yolo_detector = YOLO('yolov8n-face.pt')
            except Exception as e:
                print(f"Warning: YOLO initialization failed: {e}", file=sys.stderr)
                self.yolo_detector = None

        # Statistics for monitoring adaptive strategy
        self.stats = {
            "mediapipe_only": 0,
            "yolo_fallback": 0,
            "total_detections": 0
        }

    def _process_validated_video(
        self,
        video_path,
        output_path,
        metadata,
        input_data
    ) -> Dict[str, Any]:
        """
        Override from SecureVideoAgent
        Video is already validated at this point (security checks passed)

        Args:
            video_path: Validated, sanitized video path (from PathSanitizer)
            output_path: Validated output path (optional)
            metadata: Video metadata from VideoSecurityValidator
            input_data: Original input data with additional params

        Returns:
            Unified face detection result with person grouping
        """
        start_time = time.time()

        # Open video with proper resource management
        cap = None
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                return self._error("Failed to open validated video")

            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # PHASE 1: MediaPipe detection (fast path)
            mediapipe_faces, mp_avg_confidence = self._detect_with_mediapipe(
                cap, fps, total_frames
            )

            # PHASE 2: Adaptive strategy decision
            use_fallback = (
                mp_avg_confidence < self.FALLBACK_THRESHOLD
                and self.yolo_detector is not None
                and len(mediapipe_faces) > 0  # Only fallback if MediaPipe found faces
            )

            if use_fallback:
                # Reset video capture for YOLO re-processing
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                yolo_faces = self._detect_with_yolo(cap, fps, total_frames)

                # Use YOLO results
                all_faces = yolo_faces
                method_used = "yolo_fallback"
                avg_confidence = sum(f["confidence"] for f in all_faces) / len(all_faces) if all_faces else 0
                self.stats["yolo_fallback"] += 1
            else:
                # Use MediaPipe results (fast path)
                all_faces = mediapipe_faces
                method_used = "mediapipe_primary"
                avg_confidence = mp_avg_confidence
                self.stats["mediapipe_only"] += 1

            self.stats["total_detections"] += 1

            # PHASE 3: Group faces into persons (temporal + spatial proximity)
            persons = self._group_faces_to_persons(all_faces)

            processing_time = time.time() - start_time

            return {
                "success": True,
                "persons": persons,
                "total_faces_detected": len(all_faces),
                "video_frames": total_frames,
                "frames_sampled": len(all_faces),
                "detection_method": method_used,
                "avg_confidence": round(avg_confidence, 3),
                "adaptive_strategy": {
                    "mediapipe_confidence": round(mp_avg_confidence, 3),
                    "fallback_triggered": use_fallback,
                    "fallback_threshold": self.FALLBACK_THRESHOLD
                },
                "performance": {
                    "processing_time_seconds": round(processing_time, 3),
                    "fps": round(total_frames / processing_time, 1) if processing_time > 0 else 0
                },
                "statistics": self.stats.copy(),
                "agent_version": "2.0.0-adaptive"
            }

        except Exception as e:
            return self._error(f"Face detection failed: {str(e)}")

        finally:
            # CRITICAL: Always release video capture (prevent file descriptor leaks)
            if cap is not None:
                cap.release()

    def _detect_with_mediapipe(
        self,
        cap: cv2.VideoCapture,
        fps: float,
        total_frames: int
    ) -> Tuple[List[Dict], float]:
        """
        MediaPipe detection with frame sampling

        Returns:
            (faces, avg_confidence)
        """
        faces_found = []
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Sample frames (not every frame - Context7 best practice)
            if frame_count % self.FRAME_SAMPLE_RATE == 0:
                # Convert BGR → RGB (MediaPipe requirement)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Detect faces
                results = self.mediapipe_detector.process(rgb_frame)

                if results.detections:
                    h, w, _ = frame.shape

                    for detection in results.detections:
                        bbox = detection.location_data.relative_bounding_box

                        # Convert normalized coords → pixels
                        x = int(bbox.xmin * w)
                        y = int(bbox.ymin * h)
                        width = int(bbox.width * w)
                        height = int(bbox.height * h)

                        faces_found.append({
                            "frame": frame_count,
                            "timestamp": frame_count / fps,
                            "bbox": {
                                "x": x,
                                "y": y,
                                "width": width,
                                "height": height
                            },
                            "confidence": float(detection.score[0]) if detection.score else 0.5
                        })

            frame_count += 1

        # Calculate average confidence for adaptive decision
        avg_confidence = (
            sum(f["confidence"] for f in faces_found) / len(faces_found)
            if faces_found else 0.0
        )

        return faces_found, avg_confidence

    def _detect_with_yolo(
        self,
        cap: cv2.VideoCapture,
        fps: float,
        total_frames: int
    ) -> List[Dict]:
        """
        YOLO fallback detection (accurate but slower)

        Returns:
            List of face detections
        """
        if self.yolo_detector is None:
            return []

        faces_found = []
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Sample frames (same rate as MediaPipe for consistency)
            if frame_count % self.FRAME_SAMPLE_RATE == 0:
                # Run YOLO inference
                results = self.yolo_detector.predict(
                    frame,
                    conf=self.YOLO_CONFIDENCE,
                    verbose=False
                )

                h, w, _ = frame.shape

                # Extract detections
                for result in results:
                    boxes = result.boxes
                    for box in boxes:
                        # YOLO boxes are already in pixel coordinates
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        conf = float(box.conf[0].cpu().numpy())

                        faces_found.append({
                            "frame": frame_count,
                            "timestamp": frame_count / fps,
                            "bbox": {
                                "x": int(x1),
                                "y": int(y1),
                                "width": int(x2 - x1),
                                "height": int(y2 - y1)
                            },
                            "confidence": conf
                        })

            frame_count += 1

        return faces_found

    def _group_faces_to_persons(self, faces: List[Dict]) -> List[Dict]:
        """
        Group faces into persons using temporal + spatial proximity

        Algorithm:
        1. Sort faces by timestamp
        2. For each face, check if it's close to existing person
        3. Close = within 5 seconds AND within 100 pixels spatially
        4. If close → add to existing person
        5. If not close → create new person

        Returns:
            List of persons with their appearances
        """
        if not faces:
            return []

        persons = []
        used_faces = set()

        for i, face in enumerate(faces):
            if i in used_faces:
                continue

            person = {
                "person_id": f"person_{len(persons) + 1}",
                "appearances": [face],
                "avg_confidence": face["confidence"]
            }

            # Find similar faces (same person across frames)
            for j, other_face in enumerate(faces[i + 1:], i + 1):
                if j in used_faces:
                    continue

                # Temporal proximity: within 5 seconds
                time_diff = abs(face["timestamp"] - other_face["timestamp"])
                if time_diff < 5.0:
                    # Spatial proximity: within 100 pixels
                    x_diff = abs(face["bbox"]["x"] - other_face["bbox"]["x"])
                    y_diff = abs(face["bbox"]["y"] - other_face["bbox"]["y"])

                    if x_diff < 100 and y_diff < 100:
                        person["appearances"].append(other_face)
                        used_faces.add(j)

            used_faces.add(i)

            # Calculate average confidence for this person
            person["avg_confidence"] = sum(
                app["confidence"] for app in person["appearances"]
            ) / len(person["appearances"])

            persons.append(person)

        return persons

    def _error(self, message: str) -> Dict[str, Any]:
        """Standardized error response"""
        return {
            "success": False,
            "error": message,
            "persons": [],
            "total_faces_detected": 0
        }


def main():
    """CLI interface for adaptive face detection"""
    if len(sys.argv) != 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: python adaptive_face_detector.py '<json_input>'"
        }))
        sys.exit(1)

    try:
        input_data = json.loads(sys.argv[1])

        # Initialize detector (inherits security validation)
        detector = AdaptiveFaceDetector()

        # Process video safely (SecureVideoAgent handles validation)
        result = detector.process_video_safely(input_data)

        print(json.dumps(result, indent=2))
        sys.exit(0 if result.get("success") else 1)

    except json.JSONDecodeError:
        print(json.dumps({
            "success": False,
            "error": "Invalid JSON input"
        }))
        sys.exit(1)

    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
