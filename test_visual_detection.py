#!/usr/bin/env python3
"""
Quick test script voor visual edge detection op job 7df4efda video
"""

import sys
import logging
sys.path.insert(0, '/mnt/c/Users/rober/OneDrive/Bureaublad/Projecten/01_Active_Development/AgentOS')

# Enable DEBUG logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')

from agents2.video_processing.layout_detector import LayoutDetector
import cv2
import os

def test_visual_detection():
    video_path = "./io/input/7df4efda-9fb4-4571-95ee-ee4bafcaef09/video_1760395583.mp4"
    timestamp = 29.0  # Center of moment (6.2 + 52.1) / 2

    print(f"\n🎬 Testing visual edge detection...")
    print(f"   Video: {video_path}")
    print(f"   Video exists: {os.path.exists(video_path)}")
    print(f"   Timestamp: {timestamp}s")
    print()

    # Quick OpenCV test
    print("📹 Quick OpenCV test:")
    cap = cv2.VideoCapture(video_path)
    if cap.isOpened():
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"   FPS: {fps}")
        print(f"   Total frames: {total_frames}")
        print(f"   Resolution: {width}x{height}")

        # Try to read frame at timestamp
        frame_number = int(timestamp * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        print(f"   Frame {frame_number} read success: {ret}")
        if ret:
            print(f"   Frame shape: {frame.shape}")
        cap.release()
    else:
        print("   ❌ Could not open video file")
    print()

    detector = LayoutDetector()
    print(f"   LayoutDetector version: {detector.version}")
    print()

    # Test with empty faces (to trigger fallback to visual detection)
    print("🔍 Running layout detection...")
    result = detector.detect_layout(
        faces=[],
        orig_w=1920,  # Assuming HD video
        orig_h=1080,
        video_path=video_path,
        timestamp=timestamp
    )

    print(f"\n📊 Detection Result:")
    print(f"   Layout Type: {result.get('layout_type')}")
    print(f"   Confidence: {result.get('confidence', 0):.2%}")
    print(f"   Detection Method: {result.get('detection_method', 'N/A')}")
    print(f"   Reason: {result.get('reason', 'N/A')}")
    print(f"   Should Skip Crop: {result.get('should_skip_crop', False)}")
    print()

    if result.get('layout_type'):
        print("✅ SUCCESS: Split-screen detected via visual edge detection!")
    else:
        print("❌ FAILED: No split-screen detected")

    return result

if __name__ == "__main__":
    test_visual_detection()
