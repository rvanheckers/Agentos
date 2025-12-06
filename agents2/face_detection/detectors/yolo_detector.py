#!/usr/bin/env python3
"""
YOLO Face Detector - Fallback Accurate Detector
================================================

Context7-validated YOLO implementation for AgentOS
Used when MediaPipe confidence < 0.75 (adaptive fallback)

Configuration validated via Context7:
- confidence=0.25: Standard per Context7 examples

Source: /akanametov/yolo-face documentation
"""

import sys
import cv2
from typing import List, Dict, Optional

# Optional YOLO (gracefully degrades if not available)
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False


class YOLODetector:
    """
    YOLOv8-Face Detection (Fallback Accurate Detector)

    Used when MediaPipe confidence is low:
    - More accurate for challenging cases
    - Slower than MediaPipe (30-60 FPS on CPU)
    - Only used when needed (< 5% of cases)

    Context7 Configuration:
    - confidence=0.25: Standard threshold
    """

    # Context7-validated configuration
    CONFIDENCE_THRESHOLD = 0.25  # Standard per Context7 examples

    def __init__(self):
        """Initialize YOLO detector (if available)"""
        self.detector = None

        if YOLO_AVAILABLE:
            try:
                # Load YOLOv8n-face model (small, fast)
                # Note: Model will auto-download on first use
                self.detector = YOLO('yolov8n-face.pt')
            except Exception as e:
                print(f"Warning: YOLO initialization failed: {e}", file=sys.stderr)
                self.detector = None

    def is_available(self) -> bool:
        """Check if YOLO detector is available"""
        return self.detector is not None

    def detect_faces(
        self,
        cap: cv2.VideoCapture,
        fps: float,
        total_frames: int,
        sample_rate: int = 30
    ) -> List[Dict]:
        """
        Detect faces in video with YOLO (fallback mode)

        Args:
            cap: OpenCV VideoCapture object
            fps: Video frames per second
            total_frames: Total frames in video
            sample_rate: Process every Nth frame (default: 30)

        Returns:
            List of face detections with bbox and confidence
        """
        if self.detector is None:
            return []

        faces_found = []
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Sample frames (same rate as MediaPipe for consistency)
            if frame_count % sample_rate == 0:
                # Run YOLO inference
                results = self.detector.predict(
                    frame,
                    conf=self.CONFIDENCE_THRESHOLD,
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
