"""
Face Detection Detectors Package

Contains specialized detector implementations:
- MediaPipeDetector: Fast primary detector (180+ FPS)
- YOLODetector: Accurate fallback detector
"""

from .mediapipe_detector import MediaPipeDetector
from .yolo_detector import YOLODetector

__all__ = ["MediaPipeDetector", "YOLODetector"]
