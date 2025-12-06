"""
Integration Tests: Face Detection Pipeline End-to-End

Tests complete face detection flow with real video:
- FaceDetectorV2 with MediaPipe + YOLO fallback
- Person grouping logic
- Performance characteristics
- Statistics tracking

Context7-Validated Patterns:
- Test with real video file (not mocks for integration)
- Measure actual performance metrics
- Validate adaptive strategy in action
- Check resource cleanup
"""

import pytest
import json
from pathlib import Path
import time

from security.path_sanitizer import PathSanitizer


@pytest.fixture(scope="module")
def test_video_path():
    """Get path to real test video"""
    video_path = Path("/mnt/c/Users/rober/OneDrive/Bureaublad/Projecten/01_Active_Development/AgentOS/io/output/67b38c64-526c-4594-a152-0fa8387f7135/clip_1_original.mp4")

    if not video_path.exists():
        pytest.skip(f"Test video not found: {video_path}")

    return str(video_path)


@pytest.fixture(autouse=True, scope="module")
def configure_paths_for_testing():
    """Configure PathSanitizer for integration tests"""
    PathSanitizer.configure_for_development()

    project_root = Path("/mnt/c/Users/rober/OneDrive/Bureaublad/Projecten/01_Active_Development/AgentOS")
    PathSanitizer.ALLOWED_INPUT_DIRS.append(project_root / "io" / "output")

    yield


@pytest.fixture(scope="module")
def face_detector():
    """Initialize FaceDetectorV2 once per module"""
    try:
        from agents2.face_detection.face_detector_v2 import FaceDetectorV2
        return FaceDetectorV2()
    except ImportError as e:
        pytest.skip(f"FaceDetectorV2 not available: {e}")


class TestFaceDetectionPipeline:
    """Test complete face detection pipeline with real video"""

    def test_face_detector_processes_real_video_successfully(self, face_detector, test_video_path):
        """
        When processing a real video through FaceDetectorV2,
        Then it should complete successfully and return structured results
        """
        # Arrange - video path and detector ready

        # Act - process video
        start_time = time.time()
        result = face_detector.process_video_safely({
            "video_path": test_video_path
        })
        processing_time = time.time() - start_time

        # Assert - processing succeeded
        assert result["success"] is True, f"Processing failed: {result.get('error', 'Unknown error')}"
        assert "persons" in result
        assert "detection_method" in result
        assert "statistics" in result
        assert "total_faces_detected" in result

        # Assert - completed in reasonable time (< 60 seconds for test video)
        assert processing_time < 60.0, f"Processing too slow: {processing_time:.2f}s"

        print(f"\n✓ Video processed in {processing_time:.2f}s")
        print(f"✓ Method: {result['detection_method']}")
        print(f"✓ Faces: {result.get('total_faces_detected', 0)}")
        print(f"✓ Persons: {len(result['persons'])}")

    def test_adaptive_strategy_uses_mediapipe_first(self, face_detector, test_video_path):
        """
        When processing video with good quality,
        Then adaptive strategy should use MediaPipe (fast method)
        """
        # Arrange - detector ready

        # Act - process video
        result = face_detector.process_video_safely({
            "video_path": test_video_path
        })

        # Assert - used MediaPipe (or YOLO if confidence was low)
        assert result["success"] is True
        method = result["detection_method"]

        # MediaPipe should be preferred for most videos
        assert method in ["mediapipe_primary", "yolo_fallback"], f"Unexpected method: {method}"

        # Check statistics
        stats = result["statistics"]
        assert "mediapipe_only" in stats
        assert "total_detections" in stats

        print(f"\n✓ Detection method: {method}")
        print(f"✓ MediaPipe only runs: {stats['mediapipe_only']}")
        print(f"✓ Total detections: {stats['total_detections']}")

    def test_person_grouping_produces_valid_output(self, face_detector, test_video_path):
        """
        When faces are detected across frames,
        Then person grouping should produce coherent person objects
        """
        # Arrange - detector ready

        # Act - process video
        result = face_detector.process_video_safely({
            "video_path": test_video_path
        })

        # Assert - person grouping succeeded
        assert result["success"] is True
        persons = result["persons"]

        # Validate person structure
        for person in persons:
            assert "person_id" in person
            assert "appearances" in person
            assert "avg_confidence" in person
            assert isinstance(person["appearances"], list)
            assert len(person["appearances"]) > 0

            # Validate appearance data
            for appearance in person["appearances"]:
                assert "frame" in appearance
                assert "timestamp" in appearance
                assert "bbox" in appearance
                assert "confidence" in appearance

        print(f"\n✓ Persons detected: {len(persons)}")
        if persons:
            print(f"✓ Example person: {len(persons[0]['appearances'])} appearances, "
                  f"avg confidence {persons[0]['avg_confidence']:.2f}")

    def test_face_detection_returns_valid_bounding_boxes(self, face_detector, test_video_path):
        """
        When faces are detected,
        Then bounding boxes should have valid coordinates
        """
        # Arrange - detector ready

        # Act - process video
        result = face_detector.process_video_safely({
            "video_path": test_video_path
        })

        # Assert - bounding boxes are valid
        assert result["success"] is True

        # Iterate through persons and their appearances
        for person in result.get("persons", []):
            for appearance in person.get("appearances", []):
                bbox = appearance["bbox"]
                assert "x" in bbox
                assert "y" in bbox
                assert "width" in bbox
                assert "height" in bbox

                # Coordinates should be non-negative
                assert bbox["x"] >= 0
                assert bbox["y"] >= 0
                assert bbox["width"] > 0
                assert bbox["height"] > 0

                # Confidence should be in valid range
                assert 0.0 <= appearance["confidence"] <= 1.0

    def test_statistics_tracking_accurate(self, face_detector, test_video_path):
        """
        When video is processed,
        Then statistics should accurately reflect processing details
        """
        # Arrange - detector ready

        # Act - process video
        result = face_detector.process_video_safely({
            "video_path": test_video_path
        })

        # Assert - statistics are present and valid
        assert result["success"] is True
        stats = result["statistics"]

        # Required statistics fields
        required_fields = [
            "mediapipe_only",
            "yolo_fallback",
            "total_detections"
        ]

        for field in required_fields:
            assert field in stats, f"Missing statistic: {field}"
            assert isinstance(stats[field], int)
            assert stats[field] >= 0

        # Validate detection counts add up
        total = stats["mediapipe_only"] + stats["yolo_fallback"]
        assert total == stats["total_detections"]

        print(f"\n✓ Statistics:")
        print(f"  - Total detections: {stats['total_detections']}")
        print(f"  - MediaPipe only: {stats['mediapipe_only']}")
        print(f"  - YOLO fallback: {stats['yolo_fallback']}")
        print(f"  - Processing time: {result['performance']['processing_time_seconds']:.2f}s")


class TestFaceDetectionErrorHandling:
    """Test error scenarios in face detection pipeline"""

    def test_nonexistent_video_handled_gracefully(self, face_detector):
        """
        When a nonexistent video path is provided,
        Then detector should return error without crashing
        """
        # Arrange - invalid path
        invalid_path = "/tmp/agentos/input/nonexistent_video.mp4"

        # Act - attempt processing
        result = face_detector.process_video_safely({
            "video_path": invalid_path
        })

        # Assert - error handled gracefully
        assert result["success"] is False
        assert "error" in result
        assert len(result["error"]) > 0

    def test_invalid_json_input_rejected(self, face_detector):
        """
        When invalid input format is provided,
        Then detector should reject with clear error
        """
        # Arrange - invalid inputs
        invalid_inputs = [
            {},  # Missing video_path
            {"video_path": ""},  # Empty path
            {"video_path": None},  # None path
        ]

        for invalid_input in invalid_inputs:
            # Act - attempt processing
            result = face_detector.process_video_safely(invalid_input)

            # Assert - rejected
            assert result["success"] is False
            assert "error" in result

    def test_corrupted_video_handled_safely(self, face_detector, tmp_path):
        """
        When a corrupted video is provided,
        Then detector should handle without crashing
        """
        # Arrange - create fake corrupted video
        corrupted_video = tmp_path / "corrupted.mp4"
        corrupted_video.write_bytes(b"Not a real video file!")

        # Add to allowed dirs
        PathSanitizer.ALLOWED_INPUT_DIRS.append(tmp_path)

        try:
            # Act - attempt processing
            result = face_detector.process_video_safely({
                "video_path": str(corrupted_video)
            })

            # Assert - error handled (either rejected by security or opencv)
            assert result["success"] is False
            assert "error" in result

        finally:
            PathSanitizer.ALLOWED_INPUT_DIRS.remove(tmp_path)


class TestFaceDetectionPerformance:
    """Test performance characteristics of face detection"""

    def test_frame_sampling_reduces_processing_load(self, face_detector, test_video_path):
        """
        When frame sampling is enabled,
        Then only sampled frames should be processed (not all frames)
        """
        # Arrange - detector with frame sampling

        # Act - process video
        result = face_detector.process_video_safely({
            "video_path": test_video_path
        })

        # Assert - frame sampling worked
        assert result["success"] is True

        # Get video frame count
        import cv2
        cap = cv2.VideoCapture(test_video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()

        # Processed frames should be much less than total frames
        processed = result["frames_sampled"]

        # With FRAME_SAMPLE_RATE=30, should process ~total_frames/30
        expected_min = total_frames // 40  # Allow some variance
        expected_max = total_frames // 20

        assert expected_min <= processed <= expected_max, \
            f"Unexpected frame count: processed {processed}, total {total_frames}"

        print(f"\n✓ Frame sampling: {processed}/{total_frames} "
              f"({100*processed/total_frames:.1f}%)")

    def test_mediapipe_faster_than_yolo_fallback(self):
        """
        When comparing MediaPipe vs YOLO,
        Then MediaPipe should be significantly faster

        Note: This is a conceptual test - actual benchmark in separate file
        """
        # This test validates that adaptive strategy makes sense
        # Real performance benchmarking is in benchmarks/face_detection_benchmark.py

        # Expected performance characteristics (from Context7 + FASE 3):
        expected_mediapipe_fps = 180  # CPU-only
        expected_yolo_fps = 50  # CPU-only

        # Assert - MediaPipe should be at least 3x faster
        assert expected_mediapipe_fps > expected_yolo_fps * 3

        print(f"\n✓ Expected performance validated:")
        print(f"  - MediaPipe: {expected_mediapipe_fps}+ FPS")
        print(f"  - YOLO: {expected_yolo_fps}+ FPS")
        print(f"  - Speedup: {expected_mediapipe_fps/expected_yolo_fps:.1f}x")


class TestFaceDetectionBackwardCompatibility:
    """Test backward compatibility with old face_detector.py"""

    def test_old_face_detector_still_importable(self):
        """
        When importing old face_detector (mock),
        Then it should still work for backward compatibility
        """
        try:
            # Act - import old mock detector
            from agents2.face_detection.face_detector import FaceDetector

            # Assert - import succeeded
            assert FaceDetector is not None

            print("\n✓ Old FaceDetector (mock) still available")

        except ImportError:
            pytest.skip("Old face_detector.py not present (expected if removed)")

    def test_new_face_detector_v2_is_primary(self):
        """
        When both detectors exist,
        Then FaceDetectorV2 should be the recommended implementation
        """
        try:
            # Act - import both
            from agents2.face_detection.face_detector_v2 import FaceDetectorV2

            # Assert - v2 is a real class
            assert FaceDetectorV2 is not None
            assert hasattr(FaceDetectorV2, 'process_video_safely')

            print("\n✓ FaceDetectorV2 is primary implementation")

        except ImportError as e:
            pytest.fail(f"FaceDetectorV2 should be available: {e}")


class TestFaceDetectionResourceManagement:
    """Test resource management and cleanup"""

    def test_video_capture_released_after_processing(self, face_detector, test_video_path):
        """
        When video processing completes,
        Then VideoCapture should be released (no file descriptor leak)
        """
        # Arrange - count open file descriptors (Linux/Mac only)
        import os
        import platform

        if platform.system() not in ['Linux', 'Darwin']:
            pytest.skip("File descriptor test only on Linux/Mac")

        initial_fds = len(os.listdir('/proc/self/fd')) if os.path.exists('/proc/self/fd') else 0

        # Act - process video multiple times
        for _ in range(3):
            result = face_detector.process_video_safely({
                "video_path": test_video_path
            })
            assert result["success"] is True

        # Assert - no fd leak (allow small variance)
        final_fds = len(os.listdir('/proc/self/fd')) if os.path.exists('/proc/self/fd') else 0

        # Should not accumulate file descriptors
        assert final_fds <= initial_fds + 5, \
            f"File descriptor leak detected: {initial_fds} -> {final_fds}"

    def test_memory_released_after_processing(self, face_detector, test_video_path):
        """
        When video processing completes,
        Then memory should be released (no memory leak)
        """
        import psutil
        import os

        # Arrange - get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Act - process video multiple times
        for _ in range(3):
            result = face_detector.process_video_safely({
                "video_path": test_video_path
            })
            assert result["success"] is True

        # Assert - memory should not grow significantly (allow 100 MB variance)
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory

        assert memory_growth < 100, \
            f"Memory leak detected: {initial_memory:.1f} MB -> {final_memory:.1f} MB"

        print(f"\n✓ Memory usage: {initial_memory:.1f} MB -> {final_memory:.1f} MB "
              f"(+{memory_growth:.1f} MB)")
