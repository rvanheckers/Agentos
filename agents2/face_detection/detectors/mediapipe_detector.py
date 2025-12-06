#!/usr/bin/env python3
"""
MediaPipe Face Detector - Primary Fast Detector
================================================

Context7-validated MediaPipe implementation for AgentOS
Target: 180+ FPS on CPU, 95%+ usage rate

Configuration validated via Context7:
- model_selection=1: Full-range model (within 5 meters)
- min_detection_confidence=0.5: Default per Context7 docs

Source: /google-ai-edge/mediapipe documentation
"""

import cv2
import mediapipe as mp
from typing import List, Dict, Tuple


class MediaPipeDetector:
    """
    MediaPipe Face Detection (Primary Fast Detector)

    Optimized for speed:
    - CPU-based inference (180+ FPS)
    - Lightweight model
    - Frame sampling for efficiency

    Context7 Configuration:
    - model_selection=1: Full-range model (5m range)
    - min_detection_confidence=0.5: Standard threshold
    """

    # Context7-validated configuration
    MODEL_SELECTION = 1  # Full-range model (0-5 meters)
    MIN_DETECTION_CONFIDENCE = 0.5  # Default per Context7 docs

    def __init__(self):
        """Initialize MediaPipe face detection"""
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_drawing = mp.solutions.drawing_utils

        self.detector = self.mp_face_detection.FaceDetection(
            model_selection=self.MODEL_SELECTION,
            min_detection_confidence=self.MIN_DETECTION_CONFIDENCE
        )

    def detect_faces(
        self,
        cap: cv2.VideoCapture,
        fps: float,
        total_frames: int,
        sample_rate: int = 30
    ) -> Tuple[List[Dict], float]:
        """
        Detect faces in video with frame sampling

        Args:
            cap: OpenCV VideoCapture object
            fps: Video frames per second
            total_frames: Total frames in video
            sample_rate: Process every Nth frame (default: 30)

        Returns:
            (faces_found, avg_confidence)
            - faces_found: List of face detections with bbox and confidence
            - avg_confidence: Average confidence across all detections
        """
        faces_found = []
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Sample frames (not every frame - Context7 best practice)
            if frame_count % sample_rate == 0:
                # Convert BGR → RGB (MediaPipe requirement)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Detect faces
                results = self.detector.process(rgb_frame)

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

    def __del__(self):
        """Cleanup MediaPipe resources"""
        if hasattr(self, 'detector'):
            self.detector.close()
