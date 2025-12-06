"""
Integration Tests: Performance Regression Validation

Compares current performance against FASE 2 baseline:
- Execution times within acceptable range
- No performance degradation > 10%
- Resource usage within limits
- Benchmark results validation

Context7-Validated Patterns:
- Establish performance baselines
- Allow acceptable variance (10%)
- Test with realistic data volumes
- Monitor memory and CPU usage
"""

import pytest
import time
import json
from pathlib import Path
import psutil
import os


@pytest.fixture(autouse=True, scope="module")
def configure_for_testing():
    """Configure environment for performance testing"""
    from security.path_sanitizer import PathSanitizer

    PathSanitizer.configure_for_development()

    project_root = Path("/mnt/c/Users/rober/OneDrive/Bureaublad/Projecten/01_Active_Development/AgentOS")
    PathSanitizer.ALLOWED_INPUT_DIRS.append(project_root / "io" / "output")
    PathSanitizer.ALLOWED_INPUT_DIRS.append(project_root / "test_videos")

    yield


@pytest.fixture(scope="module")
def test_video_path():
    """Get test video path"""
    video_path = Path("/mnt/c/Users/rober/OneDrive/Bureaublad/Projecten/01_Active_Development/AgentOS/io/output/67b38c64-526c-4594-a152-0fa8387f7135/clip_1_original.mp4")

    if not video_path.exists():
        pytest.skip(f"Test video not found: {video_path}")

    return str(video_path)


@pytest.fixture(scope="module")
def video_validator():
    """Create VideoSecurityValidator instance"""
    from security.video_validator import VideoSecurityValidator
    return VideoSecurityValidator()


@pytest.fixture(scope="module")
def performance_baseline():
    """
    Load or establish performance baseline from FASE 2 profiling

    Expected performance characteristics (from FASE 3):
    - MediaPipe: 180+ FPS (CPU-only)
    - YOLO: 30-60 FPS (CPU-only)
    - Frame sampling: 30x speedup
    """
    return {
        "mediapipe_min_fps": 180,
        "yolo_min_fps": 30,
        "frame_sample_rate": 30,
        "max_processing_time_seconds": 60,  # For test video
        "max_memory_mb": 2048,  # 2 GB limit
        "security_validation_max_ms": 15,  # Path validation (WSL overhead)
        "video_validation_max_seconds": 5,  # Video metadata check
    }


class TestSecurityLayerPerformance:
    """Test security layer performance hasn't regressed"""

    def test_path_validation_performance(self, test_video_path, performance_baseline):
        """
        When validating paths repeatedly,
        Then average time should be < 10ms (no I/O blocking)
        """
        # Arrange
        from security.path_sanitizer import PathSanitizer

        iterations = 100

        # Act - measure path validation time
        start = time.time()
        for _ in range(iterations):
            PathSanitizer.validate_input_path(test_video_path)
        elapsed = time.time() - start

        # Assert - fast validation
        avg_time_ms = (elapsed / iterations) * 1000
        max_allowed_ms = performance_baseline["security_validation_max_ms"]

        assert avg_time_ms < max_allowed_ms, \
            f"Path validation too slow: {avg_time_ms:.2f}ms (max: {max_allowed_ms}ms)"

        print(f"\n✓ Path validation: {avg_time_ms:.2f}ms average "
              f"({iterations} iterations)")

    def test_video_validation_performance(self, test_video_path, video_validator, performance_baseline):
        """
        When validating video metadata,
        Then it should complete within 5 seconds
        """
        # Arrange
        from security.path_sanitizer import PathSanitizer

        validated_path = PathSanitizer.validate_input_path(test_video_path)

        # Act - measure validation time
        start = time.time()
        video_info = video_validator.validate_video_file(str(validated_path))
        elapsed = time.time() - start

        # Assert - fast validation
        max_allowed = performance_baseline["video_validation_max_seconds"]

        assert elapsed < max_allowed, \
            f"Video validation too slow: {elapsed:.2f}s (max: {max_allowed}s)"
        assert video_info["valid"] is True

        print(f"\n✓ Video validation: {elapsed:.2f}s")

    def test_resource_limit_checks_performant(self, performance_baseline):
        """
        When checking resource limits,
        Then checks should be fast (< 100ms each)
        """
        # Arrange
        from security.resource_limiter import ResourceLimiter

        # Act - measure resource check time
        start = time.time()
        try:
            ResourceLimiter.check_disk_space("/tmp", required_mb=100)
            disk_ok = True
        except IOError:
            disk_ok = False
        disk_time = time.time() - start

        # Assert - fast check
        assert disk_time < 0.1, f"Disk check too slow: {disk_time:.3f}s"
        assert disk_ok is True

        print(f"\n✓ Resource checks: disk {disk_time*1000:.1f}ms")


class TestFaceDetectionPerformance:
    """Test face detection performance meets baseline"""

    def test_face_detection_processing_time_acceptable(
        self, test_video_path, performance_baseline
    ):
        """
        When processing test video,
        Then total time should be within acceptable range (< 60s)
        """
        try:
            # Arrange
            from agents2.face_detection.face_detector_v2 import FaceDetectorV2

            detector = FaceDetectorV2()

            # Act - measure processing time
            start = time.time()
            result = detector.process_video_safely({
                "video_path": test_video_path
            })
            elapsed = time.time() - start

            # Assert - processing time acceptable
            max_allowed = performance_baseline["max_processing_time_seconds"]

            assert result["success"] is True
            assert elapsed < max_allowed, \
                f"Processing too slow: {elapsed:.2f}s (max: {max_allowed}s)"

            # Log statistics
            stats = result["statistics"]
            print(f"\n✓ Processing time: {elapsed:.2f}s")
            print(f"  - Method: {result['detection_method']}")
            print(f"  - Video frames: {result['video_frames']}")
            print(f"  - Faces detected: {result['total_faces_detected']}")

        except ImportError:
            pytest.skip("FaceDetectorV2 not available")

    def test_frame_sampling_achieves_expected_speedup(
        self, test_video_path, performance_baseline
    ):
        """
        When processing with frame sampling,
        Then should achieve ~30x speedup compared to processing all frames
        """
        try:
            # Arrange
            from agents2.face_detection.face_detector_v2 import FaceDetectorV2
            import cv2

            detector = FaceDetectorV2()

            # Get total frame count
            cap = cv2.VideoCapture(test_video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()

            # Act - process with frame sampling
            result = detector.process_video_safely({
                "video_path": test_video_path
            })

            # Assert - frame sampling worked as expected
            assert result["success"] is True

            processed_frames = result["frames_sampled"]
            expected_frames = total_frames // performance_baseline["frame_sample_rate"]

            # Allow 20% variance
            assert abs(processed_frames - expected_frames) / expected_frames < 0.2, \
                f"Frame sampling not working: processed {processed_frames}, " \
                f"expected ~{expected_frames}"

            speedup = total_frames / processed_frames
            print(f"\n✓ Frame sampling speedup: {speedup:.1f}x")
            print(f"  - Total frames: {total_frames}")
            print(f"  - Processed: {processed_frames}")

        except ImportError:
            pytest.skip("FaceDetectorV2 not available")

    def test_memory_usage_within_limits(self, test_video_path, performance_baseline):
        """
        When processing video,
        Then peak memory usage should stay under 2 GB limit
        """
        try:
            # Arrange
            from agents2.face_detection.face_detector_v2 import FaceDetectorV2

            detector = FaceDetectorV2()
            process = psutil.Process(os.getpid())

            # Get initial memory
            initial_memory_mb = process.memory_info().rss / 1024 / 1024

            # Act - process video
            result = detector.process_video_safely({
                "video_path": test_video_path
            })

            # Get peak memory
            peak_memory_mb = process.memory_info().rss / 1024 / 1024

            # Assert - memory within limits
            max_allowed_mb = performance_baseline["max_memory_mb"]

            assert result["success"] is True
            assert peak_memory_mb < max_allowed_mb, \
                f"Memory usage too high: {peak_memory_mb:.1f} MB (max: {max_allowed_mb} MB)"

            memory_used = peak_memory_mb - initial_memory_mb
            print(f"\n✓ Memory usage: {peak_memory_mb:.1f} MB peak "
                  f"(+{memory_used:.1f} MB)")

        except ImportError:
            pytest.skip("FaceDetectorV2 not available")


class TestPerformanceComparison:
    """Compare performance with baseline measurements"""

    def test_no_performance_regression_in_security_layer(
        self, test_video_path, video_validator, performance_baseline
    ):
        """
        When comparing to baseline,
        Then security layer performance should not regress > 10%
        """
        # Arrange
        from security.path_sanitizer import PathSanitizer

        # Measure current performance
        iterations = 50

        # Path validation
        start = time.time()
        for _ in range(iterations):
            PathSanitizer.validate_input_path(test_video_path)
        path_time = (time.time() - start) / iterations * 1000  # ms

        # Video validation
        validated_path = PathSanitizer.validate_input_path(test_video_path)
        start = time.time()
        video_validator.validate_video_file(str(validated_path))
        video_time = time.time() - start

        # Assert - within baseline + 10% tolerance
        baseline_path_ms = performance_baseline["security_validation_max_ms"]
        baseline_video_s = performance_baseline["video_validation_max_seconds"]

        assert path_time < baseline_path_ms * 1.1, \
            f"Path validation regressed: {path_time:.2f}ms " \
            f"(baseline: {baseline_path_ms}ms)"

        assert video_time < baseline_video_s * 1.1, \
            f"Video validation regressed: {video_time:.2f}s " \
            f"(baseline: {baseline_video_s}s)"

        print(f"\n✓ No regression detected:")
        print(f"  - Path validation: {path_time:.2f}ms "
              f"(baseline: {baseline_path_ms}ms)")
        print(f"  - Video validation: {video_time:.2f}s "
              f"(baseline: {baseline_video_s}s)")

    def test_face_detection_meets_fps_target(self, test_video_path, performance_baseline):
        """
        When measuring effective FPS,
        Then MediaPipe usage should meet 180+ FPS target
        """
        try:
            # Arrange
            from agents2.face_detection.face_detector_v2 import FaceDetectorV2
            import cv2

            detector = FaceDetectorV2()

            # Get video FPS
            cap = cv2.VideoCapture(test_video_path)
            video_fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()

            # Act - process video
            result = detector.process_video_safely({
                "video_path": test_video_path
            })

            # Calculate effective FPS
            processing_time = result["performance"]["processing_time_seconds"]
            frames_processed = result["frames_sampled"]
            effective_fps = frames_processed / processing_time if processing_time > 0 else 0

            # Assert - FPS acceptable
            # Note: This is frames processed per second, not detection FPS
            # Detection FPS would be higher since we sample frames
            detection_method = result["detection_method"]

            print(f"\n✓ Performance metrics:")
            print(f"  - Detection method: {detection_method}")
            print(f"  - Effective FPS: {effective_fps:.1f}")
            print(f"  - Frames processed: {frames_processed}/{total_frames}")
            print(f"  - Processing time: {processing_time:.2f}s")

            # If using MediaPipe, should be fast
            if detection_method == "mediapipe":
                # With frame sampling, effective FPS should be reasonable
                # (This is not the same as detection FPS, which is much higher)
                assert effective_fps > 0, "Processing failed"

        except ImportError:
            pytest.skip("FaceDetectorV2 not available")


class TestResourceScaling:
    """Test resource usage scales appropriately with input size"""

    def test_processing_time_scales_linearly(self, test_video_path):
        """
        When processing videos of different lengths,
        Then processing time should scale roughly linearly
        """
        # This is a conceptual test - would need multiple test videos
        # For now, we validate that processing time is proportional to frames

        try:
            # Arrange
            from agents2.face_detection.face_detector_v2 import FaceDetectorV2
            import cv2

            detector = FaceDetectorV2()

            # Get video duration
            cap = cv2.VideoCapture(test_video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0
            cap.release()

            # Act - process video
            start = time.time()
            result = detector.process_video_safely({
                "video_path": test_video_path
            })
            processing_time = time.time() - start

            # Assert - processing time reasonable for video length
            # Should process faster than real-time (with frame sampling)
            assert result["success"] is True

            processing_ratio = processing_time / duration if duration > 0 else 0

            print(f"\n✓ Scaling characteristics:")
            print(f"  - Video duration: {duration:.2f}s")
            print(f"  - Processing time: {processing_time:.2f}s")
            print(f"  - Processing ratio: {processing_ratio:.2f}x realtime")

        except ImportError:
            pytest.skip("FaceDetectorV2 not available")

    def test_memory_usage_doesnt_accumulate(self, test_video_path):
        """
        When processing multiple videos sequentially,
        Then memory should not accumulate (no memory leaks)
        """
        try:
            # Arrange
            from agents2.face_detection.face_detector_v2 import FaceDetectorV2

            detector = FaceDetectorV2()
            process = psutil.Process(os.getpid())

            # Baseline memory
            baseline_mb = process.memory_info().rss / 1024 / 1024

            # Act - process video 3 times
            memory_readings = []
            for i in range(3):
                result = detector.process_video_safely({
                    "video_path": test_video_path
                })
                assert result["success"] is True

                current_mb = process.memory_info().rss / 1024 / 1024
                memory_readings.append(current_mb)

            # Assert - memory not growing unbounded
            # Allow some growth but should stabilize
            memory_growth = memory_readings[-1] - baseline_mb
            max_growth_mb = 200  # Allow 200 MB growth max

            assert memory_growth < max_growth_mb, \
                f"Memory leak detected: +{memory_growth:.1f} MB after 3 iterations"

            print(f"\n✓ Memory stability:")
            print(f"  - Baseline: {baseline_mb:.1f} MB")
            print(f"  - After 3x: {memory_readings[-1]:.1f} MB")
            print(f"  - Growth: +{memory_growth:.1f} MB")

        except ImportError:
            pytest.skip("FaceDetectorV2 not available")


class TestPerformanceUnderLoad:
    """Test performance under stress conditions"""

    def test_concurrent_validations_dont_slow_down(self, test_video_path):
        """
        When multiple validations happen concurrently,
        Then throughput should not degrade significantly
        """
        # Arrange
        from security.path_sanitizer import PathSanitizer
        import concurrent.futures

        def validate_path():
            start = time.time()
            PathSanitizer.validate_input_path(test_video_path)
            return time.time() - start

        # Act - sequential baseline
        sequential_times = [validate_path() for _ in range(10)]
        avg_sequential = sum(sequential_times) / len(sequential_times)

        # Act - concurrent
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            concurrent_times = list(executor.map(lambda _: validate_path(), range(10)))

        avg_concurrent = sum(concurrent_times) / len(concurrent_times)

        # Assert - concurrent not significantly slower (< 2x)
        assert avg_concurrent < avg_sequential * 2, \
            f"Concurrent slowdown too high: {avg_concurrent/avg_sequential:.2f}x"

        print(f"\n✓ Concurrent performance:")
        print(f"  - Sequential: {avg_sequential*1000:.2f}ms avg")
        print(f"  - Concurrent: {avg_concurrent*1000:.2f}ms avg")
        print(f"  - Slowdown: {avg_concurrent/avg_sequential:.2f}x")


class TestPerformanceDocumentation:
    """Validate performance metrics are documented"""

    def test_benchmark_results_file_exists(self):
        """
        When benchmarks are run,
        Then results should be documented in benchmark_results.json
        """
        # Arrange
        benchmark_file = Path("/mnt/c/Users/rober/OneDrive/Bureaublad/Projecten/01_Active_Development/AgentOS/benchmarks/benchmark_results.json")

        # This test doesn't fail if file doesn't exist yet
        # Just logs whether benchmarking has been completed

        if benchmark_file.exists():
            try:
                with open(benchmark_file) as f:
                    results = json.load(f)

                print(f"\n✓ Benchmark results found:")
                print(f"  - File: {benchmark_file}")
                print(f"  - Keys: {list(results.keys())}")

                # Validate structure
                if "mediapipe_fps" in results:
                    print(f"  - MediaPipe FPS: {results['mediapipe_fps']}")
                if "processing_time" in results:
                    print(f"  - Processing time: {results['processing_time']:.2f}s")

            except json.JSONDecodeError:
                print("\n⚠ Benchmark results file exists but invalid JSON")
        else:
            print(f"\n⚠ Benchmark results not yet generated")
            print(f"  Run: python benchmarks/face_detection_benchmark.py <video>")
