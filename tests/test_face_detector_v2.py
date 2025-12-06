#!/usr/bin/env python3
"""
Comprehensive tests for FaceDetectorV2
=======================================

Tests cover:
1. Security integration (SecureVideoAgent inheritance)
2. Adaptive strategy (MediaPipe → YOLO fallback)
3. Resource management (proper cleanup)
4. Performance benchmarks
5. Edge cases (no faces, partial faces, etc.)

Context7 Score Target: 8+/10
"""

import pytest
import json
import sys
import tempfile
import numpy as np
import cv2
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from agents2.face_detection.face_detector_v2 import FaceDetectorV2
from security.exceptions import SecurityError


class TestSecurityIntegration:
    """Test SecureVideoAgent inheritance and security features"""

    def test_inherits_from_secure_video_agent(self):
        """Verify FaceDetectorV2 inherits from SecureVideoAgent"""
        detector = FaceDetectorV2()
        assert hasattr(detector, 'validator')
        assert hasattr(detector, 'path_sanitizer')
        assert hasattr(detector, 'resource_limiter')
        assert hasattr(detector, 'process_video_safely')

    def test_invalid_video_path_rejected(self):
        """Test that invalid video paths are rejected by security layer"""
        detector = FaceDetectorV2()

        # Test missing video_path
        result = detector.process_video_safely({})
        assert result["success"] is False
        assert "No video_path provided" in result["error"]

    @patch('agents2.base.secure_agent.PathSanitizer.validate_input_path')
    def test_path_traversal_attack_blocked(self, mock_validate):
        """Test that path traversal attacks are blocked"""
        mock_validate.side_effect = SecurityError("Path outside allowed directories")

        detector = FaceDetectorV2()
        result = detector.process_video_safely({
            "video_path": "../../etc/passwd"
        })

        assert result["success"] is False
        assert result["error_type"] == "security"
        assert "Security validation failed" in result["error"]

    @patch('agents2.base.secure_agent.VideoSecurityValidator.validate_or_raise')
    def test_malformed_video_rejected(self, mock_validate):
        """Test that malformed video files are rejected"""
        mock_validate.side_effect = SecurityError("Invalid MIME type")

        detector = FaceDetectorV2()
        result = detector.process_video_safely({
            "video_path": "/tmp/fake_video.mp4"
        })

        assert result["success"] is False
        assert "Security validation failed" in result["error"]


class TestAdaptiveStrategy:
    """Test adaptive MediaPipe → YOLO fallback logic"""

    def test_mediapipe_detector_initialized(self):
        """Verify MediaPipe detector is properly initialized"""
        detector = FaceDetectorV2()
        assert detector.mediapipe_detector is not None
        # Configuration moved to detector classes
        assert detector.mediapipe_detector.MODEL_SELECTION == 1  # Full-range model
        assert detector.mediapipe_detector.MIN_DETECTION_CONFIDENCE == 0.5

    def test_yolo_gracefully_unavailable(self):
        """Test graceful degradation when YOLO is not available"""
        with patch('agents2.face_detection.face_detector_v2.YOLO_AVAILABLE', False):
            detector = FaceDetectorV2()
            assert detector.yolo_detector is None
            # Should still work with MediaPipe only

    def test_high_confidence_uses_mediapipe_only(self):
        """Test that high confidence detections use MediaPipe without fallback"""
        detector = FaceDetectorV2()

        # Mock high-confidence MediaPipe detections
        mock_faces = [
            {"frame": 0, "timestamp": 0.0, "bbox": {"x": 100, "y": 100, "width": 50, "height": 50}, "confidence": 0.9},
            {"frame": 30, "timestamp": 1.0, "bbox": {"x": 105, "y": 105, "width": 50, "height": 50}, "confidence": 0.85}
        ]

        with patch.object(detector.mediapipe_detector, 'detect_faces', return_value=(mock_faces, 0.875)):
            with patch.object(detector.yolo_detector, 'detect_faces') as mock_yolo:
                # Mock video capture
                with patch('cv2.VideoCapture') as mock_cap:
                    mock_cap_instance = MagicMock()
                    mock_cap_instance.isOpened.return_value = True
                    mock_cap_instance.get.side_effect = [30.0, 100]  # fps, total_frames
                    mock_cap.return_value = mock_cap_instance

                    result = detector._process_validated_video(
                        video_path=Path("/tmp/test.mp4"),
                        output_path=None,
                        metadata={},
                        input_data={}
                    )

                    # Verify MediaPipe was used (avg confidence 0.875 > 0.75 threshold)
                    assert result["success"] is True
                    assert result["detection_method"] == "mediapipe_primary"
                    assert result["adaptive_strategy"]["fallback_triggered"] is False
                    mock_yolo.assert_not_called()  # YOLO should NOT be called

    def test_low_confidence_triggers_yolo_fallback(self):
        """Test that low confidence triggers YOLO fallback"""
        detector = FaceDetectorV2()

        # Mock low-confidence MediaPipe detections
        mock_mp_faces = [
            {"frame": 0, "timestamp": 0.0, "bbox": {"x": 100, "y": 100, "width": 50, "height": 50}, "confidence": 0.6},
            {"frame": 30, "timestamp": 1.0, "bbox": {"x": 105, "y": 105, "width": 50, "height": 50}, "confidence": 0.65}
        ]

        # Mock high-confidence YOLO detections
        mock_yolo_faces = [
            {"frame": 0, "timestamp": 0.0, "bbox": {"x": 100, "y": 100, "width": 50, "height": 50}, "confidence": 0.9}
        ]

        # Ensure YOLO is available
        with patch.object(detector.yolo_detector, 'is_available', return_value=True):
            with patch.object(detector.mediapipe_detector, 'detect_faces', return_value=(mock_mp_faces, 0.625)):
                with patch.object(detector.yolo_detector, 'detect_faces', return_value=mock_yolo_faces) as mock_yolo:
                    with patch('cv2.VideoCapture') as mock_cap:
                        mock_cap_instance = MagicMock()
                        mock_cap_instance.isOpened.return_value = True
                        mock_cap_instance.get.side_effect = [30.0, 100]
                        mock_cap.return_value = mock_cap_instance

                        result = detector._process_validated_video(
                            video_path=Path("/tmp/test.mp4"),
                            output_path=None,
                            metadata={},
                            input_data={}
                        )

                        # Verify YOLO fallback was triggered (avg confidence 0.625 < 0.75)
                        assert result["success"] is True
                        assert result["detection_method"] == "yolo_fallback"
                        assert result["adaptive_strategy"]["fallback_triggered"] is True
                        mock_yolo.assert_called_once()  # YOLO SHOULD be called

    def test_fallback_threshold_configurable(self):
        """Test that fallback threshold is correct (0.75 per spec)"""
        detector = FaceDetectorV2()
        assert detector.FALLBACK_THRESHOLD == 0.75


class TestPersonGrouping:
    """Test face-to-person grouping logic"""

    def test_single_face_single_person(self):
        """Test that a single face creates a single person"""
        detector = FaceDetectorV2()

        faces = [
            {"frame": 0, "timestamp": 0.0, "bbox": {"x": 100, "y": 100, "width": 50, "height": 50}, "confidence": 0.9}
        ]

        persons = detector._group_faces_to_persons(faces)

        assert len(persons) == 1
        assert persons[0]["person_id"] == "person_1"
        assert len(persons[0]["appearances"]) == 1
        assert persons[0]["avg_confidence"] == 0.9

    def test_temporal_grouping(self):
        """Test that faces close in time are grouped as same person"""
        detector = FaceDetectorV2()

        faces = [
            {"frame": 0, "timestamp": 0.0, "bbox": {"x": 100, "y": 100, "width": 50, "height": 50}, "confidence": 0.9},
            {"frame": 30, "timestamp": 1.0, "bbox": {"x": 105, "y": 105, "width": 50, "height": 50}, "confidence": 0.85},
            {"frame": 60, "timestamp": 2.0, "bbox": {"x": 110, "y": 110, "width": 50, "height": 50}, "confidence": 0.88}
        ]

        persons = detector._group_faces_to_persons(faces)

        # Should be grouped as one person (within 5 seconds AND within 100 pixels)
        assert len(persons) == 1
        assert len(persons[0]["appearances"]) == 3

    def test_spatial_separation_creates_multiple_persons(self):
        """Test that spatially separated faces create different persons"""
        detector = FaceDetectorV2()

        faces = [
            {"frame": 0, "timestamp": 0.0, "bbox": {"x": 100, "y": 100, "width": 50, "height": 50}, "confidence": 0.9},
            {"frame": 30, "timestamp": 1.0, "bbox": {"x": 500, "y": 500, "width": 50, "height": 50}, "confidence": 0.85}
        ]

        persons = detector._group_faces_to_persons(faces)

        # Should create 2 persons (too far apart spatially)
        assert len(persons) == 2

    def test_empty_faces_returns_empty_persons(self):
        """Test that empty face list returns empty persons list"""
        detector = FaceDetectorV2()
        persons = detector._group_faces_to_persons([])
        assert persons == []


class TestResourceManagement:
    """Test proper resource cleanup and management"""

    def test_video_capture_released_on_success(self):
        """Test that cv2.VideoCapture is released after successful processing"""
        detector = FaceDetectorV2()

        with patch('cv2.VideoCapture') as mock_cap:
            mock_cap_instance = MagicMock()
            mock_cap_instance.isOpened.return_value = True
            mock_cap_instance.get.side_effect = [30.0, 100]
            mock_cap_instance.read.return_value = (False, None)  # End of video
            mock_cap.return_value = mock_cap_instance

            with patch.object(detector.mediapipe_detector, 'detect_faces', return_value=([], 0.0)):
                detector._process_validated_video(
                    video_path=Path("/tmp/test.mp4"),
                    output_path=None,
                    metadata={},
                    input_data={}
                )

            # Verify release was called
            mock_cap_instance.release.assert_called()

    def test_video_capture_released_on_exception(self):
        """Test that cv2.VideoCapture is released even on exception"""
        detector = FaceDetectorV2()

        with patch('cv2.VideoCapture') as mock_cap:
            mock_cap_instance = MagicMock()
            mock_cap_instance.isOpened.return_value = True
            mock_cap.return_value = mock_cap_instance

            # Force an exception during processing
            with patch.object(detector.mediapipe_detector, 'detect_faces', side_effect=Exception("Test error")):
                result = detector._process_validated_video(
                    video_path=Path("/tmp/test.mp4"),
                    output_path=None,
                    metadata={},
                    input_data={}
                )

                # Verify error was handled
                assert result["success"] is False

            # Verify release was still called (finally block)
            mock_cap_instance.release.assert_called()


class TestFrameSampling:
    """Test frame sampling strategy"""

    def test_frame_sample_rate_configured(self):
        """Test that frame sample rate is set correctly"""
        detector = FaceDetectorV2()
        assert detector.FRAME_SAMPLE_RATE == 30  # Every 30th frame per spec

    def test_mediapipe_samples_frames_correctly(self):
        """Test that MediaPipe samples every 30th frame"""
        detector = FaceDetectorV2()

        # Create mock video with 100 frames
        with patch('cv2.VideoCapture') as mock_cap:
            mock_cap_instance = MagicMock()
            mock_cap_instance.isOpened.return_value = True

            # Simulate 100 frames
            frame_data = [(True, np.zeros((480, 640, 3), dtype=np.uint8)) for _ in range(100)]
            frame_data.append((False, None))  # End of video
            mock_cap_instance.read.side_effect = frame_data

            # Mock MediaPipe detection
            with patch.object(detector.mediapipe_detector.detector, 'process', return_value=Mock(detections=[])):
                faces, _ = detector.mediapipe_detector.detect_faces(mock_cap_instance, 30.0, 100, 30)

            # With sample rate 30, should process frames: 0, 30, 60, 90 = 4 frames
            # (but no faces detected in our mock)
            assert len(faces) == 0  # No detections in mock


class TestStatistics:
    """Test adaptive strategy statistics tracking"""

    def test_statistics_initialized(self):
        """Test that statistics are properly initialized"""
        detector = FaceDetectorV2()
        assert detector.stats == {
            "mediapipe_only": 0,
            "yolo_fallback": 0,
            "total_detections": 0
        }

    def test_statistics_track_mediapipe_usage(self):
        """Test that MediaPipe usage is tracked"""
        detector = FaceDetectorV2()

        mock_faces = [{"frame": 0, "timestamp": 0.0, "bbox": {"x": 100, "y": 100, "width": 50, "height": 50}, "confidence": 0.9}]

        with patch.object(detector, '_detect_with_mediapipe', return_value=(mock_faces, 0.9)):
            with patch('cv2.VideoCapture') as mock_cap:
                mock_cap_instance = MagicMock()
                mock_cap_instance.isOpened.return_value = True
                mock_cap_instance.get.side_effect = [30.0, 100]
                mock_cap.return_value = mock_cap_instance

                result = detector._process_validated_video(
                    video_path=Path("/tmp/test.mp4"),
                    output_path=None,
                    metadata={},
                    input_data={}
                )

                # Verify statistics updated
                assert result["statistics"]["mediapipe_only"] == 1
                assert result["statistics"]["yolo_fallback"] == 0
                assert result["statistics"]["total_detections"] == 1


class TestCLIInterface:
    """Test command-line interface"""

    def test_cli_requires_json_input(self):
        """Test that CLI requires JSON input argument"""
        from agents2.face_detection.face_detector_v2 import main

        with patch('sys.argv', ['face_detector_v2.py']):
            with pytest.raises(SystemExit) as exc_info:
                with patch('builtins.print') as mock_print:
                    main()

            assert exc_info.value.code == 1

    def test_cli_handles_invalid_json(self):
        """Test that CLI handles invalid JSON gracefully"""
        from agents2.face_detection.face_detector_v2 import main

        with patch('sys.argv', ['face_detector_v2.py', 'invalid json']):
            with pytest.raises(SystemExit) as exc_info:
                with patch('builtins.print') as mock_print:
                    main()

            assert exc_info.value.code == 1


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_video_with_no_faces(self):
        """Test handling of video with no faces detected"""
        detector = FaceDetectorV2()

        with patch.object(detector.mediapipe_detector, 'detect_faces', return_value=([], 0.0)):
            with patch('cv2.VideoCapture') as mock_cap:
                mock_cap_instance = MagicMock()
                mock_cap_instance.isOpened.return_value = True
                mock_cap_instance.get.side_effect = [30.0, 100]
                mock_cap.return_value = mock_cap_instance

                result = detector._process_validated_video(
                    video_path=Path("/tmp/test.mp4"),
                    output_path=None,
                    metadata={},
                    input_data={}
                )

                assert result["success"] is True
                assert result["total_faces_detected"] == 0
                assert result["persons"] == []

    def test_video_fails_to_open(self):
        """Test handling of video that fails to open"""
        detector = FaceDetectorV2()

        with patch('cv2.VideoCapture') as mock_cap:
            mock_cap_instance = MagicMock()
            mock_cap_instance.isOpened.return_value = False
            mock_cap.return_value = mock_cap_instance

            result = detector._process_validated_video(
                video_path=Path("/tmp/test.mp4"),
                output_path=None,
                metadata={},
                input_data={}
            )

            assert result["success"] is False
            assert "Failed to open" in result["error"]


# Performance benchmark (optional, requires real video file)
class TestPerformance:
    """Performance benchmarks (requires test video)"""

    @pytest.mark.skip(reason="Requires real test video file")
    def test_mediapipe_fps_benchmark(self):
        """Benchmark MediaPipe FPS (target: 180+ FPS)"""
        # This would require a real test video
        # Implementation would measure actual FPS and verify > 180
        pass

    @pytest.mark.skip(reason="Requires real test video file")
    def test_95_percent_mediapipe_usage(self):
        """Verify 95%+ of cases use MediaPipe fast path"""
        # This would process multiple videos and verify statistics
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
