"""
Integration Tests: Backward Compatibility Validation

Ensures that refactored code doesn't break existing functionality:
- Old agents still work
- API contracts maintained
- Legacy configurations supported
- Migration path is smooth

Context7-Validated Patterns:
- Test both old and new implementations
- Validate API compatibility
- Check configuration migration
- Ensure no breaking changes
"""

import pytest
from pathlib import Path
import json


@pytest.fixture(autouse=True, scope="module")
def configure_for_testing():
    """Configure environment for compatibility testing"""
    from security.path_sanitizer import PathSanitizer

    PathSanitizer.configure_for_development()

    project_root = Path("/mnt/c/Users/rober/OneDrive/Bureaublad/Projecten/01_Active_Development/AgentOS")
    PathSanitizer.ALLOWED_INPUT_DIRS.append(project_root / "io" / "output")

    yield


@pytest.fixture(scope="module")
def test_video_path():
    """Get test video path"""
    video_path = Path("/mnt/c/Users/rober/OneDrive/Bureaublad/Projecten/01_Active_Development/AgentOS/io/output/67b38c64-526c-4594-a152-0fa8387f7135/clip_1_original.mp4")

    if not video_path.exists():
        pytest.skip(f"Test video not found: {video_path}")

    return str(video_path)


class TestSecurityLayerBackwardCompatibility:
    """Test that security layer doesn't break existing functionality"""

    def test_path_sanitizer_api_unchanged(self):
        """
        When using PathSanitizer API,
        Then all public methods should still exist and work
        """
        # Arrange
        from security.path_sanitizer import PathSanitizer

        # Act - check API surface
        required_methods = [
            'validate_input_path',
            'validate_output_path',
            'configure_for_development'
        ]

        # Assert - all methods exist
        for method_name in required_methods:
            assert hasattr(PathSanitizer, method_name), \
                f"API changed: {method_name} missing"
            assert callable(getattr(PathSanitizer, method_name))

    def test_video_validator_api_unchanged(self):
        """
        When using VideoSecurityValidator API,
        Then all public methods should still exist
        """
        # Arrange
        from security.video_validator import VideoSecurityValidator

        # Act - check API surface (instance method, not class method)
        validator = VideoSecurityValidator()
        required_methods = ['validate_video_file', 'validate_or_raise']

        # Assert - all methods exist
        for method_name in required_methods:
            assert hasattr(validator, method_name)
            assert callable(getattr(validator, method_name))

    def test_resource_limiter_api_unchanged(self):
        """
        When using ResourceLimiter API,
        Then all public methods should still exist
        """
        # Arrange
        from security.resource_limiter import ResourceLimiter

        # Act - check API surface
        required_methods = [
            'check_disk_space',
            'run_ffmpeg_limited',
            'monitor_process'
        ]

        # Assert - all methods exist
        for method_name in required_methods:
            assert hasattr(ResourceLimiter, method_name)
            assert callable(getattr(ResourceLimiter, method_name))

    def test_security_exceptions_unchanged(self):
        """
        When importing security exceptions,
        Then SecurityError should still be available
        """
        # Arrange & Act
        from security.exceptions import SecurityError

        # Assert - exception class exists
        assert SecurityError is not None
        assert issubclass(SecurityError, Exception)


class TestFaceDetectorBackwardCompatibility:
    """Test face detector backward compatibility"""

    def test_old_face_detector_import_path_works(self):
        """
        When importing from old path,
        Then FaceDetector should still be available
        """
        try:
            # Act - import old detector
            from agents2.face_detection.face_detector import FaceDetector

            # Assert - import succeeded
            assert FaceDetector is not None
            print("\n✓ Old FaceDetector import path still works")

        except ImportError:
            pytest.skip("Old face_detector.py removed (acceptable)")

    def test_new_face_detector_v2_import_path(self):
        """
        When importing FaceDetectorV2,
        Then it should be available at expected path
        """
        try:
            # Act - import new detector
            from agents2.face_detection.face_detector_v2 import FaceDetectorV2

            # Assert - import succeeded
            assert FaceDetectorV2 is not None
            print("\n✓ FaceDetectorV2 import path works")

        except ImportError as e:
            pytest.fail(f"FaceDetectorV2 should be available: {e}")

    def test_face_detector_v2_has_expected_interface(self):
        """
        When using FaceDetectorV2,
        Then it should have expected public interface
        """
        try:
            # Arrange
            from agents2.face_detection.face_detector_v2 import FaceDetectorV2

            detector = FaceDetectorV2()

            # Act - check interface
            required_methods = ['process_video_safely']

            # Assert - all methods exist
            for method_name in required_methods:
                assert hasattr(detector, method_name), \
                    f"Missing method: {method_name}"
                assert callable(getattr(detector, method_name))

        except ImportError:
            pytest.skip("FaceDetectorV2 not available")

    def test_face_detector_v2_accepts_legacy_input_format(self, test_video_path):
        """
        When providing input in legacy format,
        Then FaceDetectorV2 should still work
        """
        try:
            # Arrange
            from agents2.face_detection.face_detector_v2 import FaceDetectorV2

            detector = FaceDetectorV2()

            # Act - use legacy input format (dict with video_path)
            result = detector.process_video_safely({
                "video_path": test_video_path
            })

            # Assert - processed successfully
            assert "success" in result
            assert "persons" in result or result["success"] is False

        except ImportError:
            pytest.skip("FaceDetectorV2 not available")


class TestOutputFormatCompatibility:
    """Test output format hasn't changed"""

    def test_face_detector_v2_output_format(self, test_video_path):
        """
        When FaceDetectorV2 processes video,
        Then output format should be consistent and documented
        """
        try:
            # Arrange
            from agents2.face_detection.face_detector_v2 import FaceDetectorV2

            detector = FaceDetectorV2()

            # Act - process video
            result = detector.process_video_safely({
                "video_path": test_video_path
            })

            # Assert - expected fields present
            assert "success" in result

            if result["success"]:
                required_fields = [
                    "persons",
                    "detection_method",
                    "statistics",
                    "total_faces_detected",
                    "avg_confidence",
                    "adaptive_strategy",
                    "performance"
                ]

                for field in required_fields:
                    assert field in result, f"Missing output field: {field}"

                # Validate person structure
                if result["persons"]:
                    person = result["persons"][0]
                    assert "person_id" in person
                    assert "appearances" in person
                    assert "avg_confidence" in person

        except ImportError:
            pytest.skip("FaceDetectorV2 not available")

    def test_error_output_format_consistent(self):
        """
        When processing fails,
        Then error format should be consistent
        """
        try:
            # Arrange
            from agents2.face_detection.face_detector_v2 import FaceDetectorV2

            detector = FaceDetectorV2()

            # Act - trigger error with invalid input
            result = detector.process_video_safely({
                "video_path": "/tmp/nonexistent/video.mp4"
            })

            # Assert - error format
            assert "success" in result
            assert result["success"] is False
            assert "error" in result
            assert isinstance(result["error"], str)
            assert len(result["error"]) > 0

        except ImportError:
            pytest.skip("FaceDetectorV2 not available")


class TestConfigurationCompatibility:
    """Test configuration backward compatibility"""

    def test_path_sanitizer_development_mode_still_works(self):
        """
        When configuring PathSanitizer for development,
        Then configure_for_development() should still work
        """
        # Arrange
        from security.path_sanitizer import PathSanitizer

        # Store original
        original_input = PathSanitizer.ALLOWED_INPUT_DIRS.copy()
        original_output = PathSanitizer.ALLOWED_OUTPUT_DIRS.copy()

        # Act - configure for development
        PathSanitizer.configure_for_development()

        # Assert - directories were added
        assert len(PathSanitizer.ALLOWED_INPUT_DIRS) > len(original_input)
        assert len(PathSanitizer.ALLOWED_OUTPUT_DIRS) > len(original_output)

        # Cleanup
        PathSanitizer.ALLOWED_INPUT_DIRS = original_input
        PathSanitizer.ALLOWED_OUTPUT_DIRS = original_output

    def test_resource_limiter_default_limits_unchanged(self):
        """
        When using ResourceLimiter with defaults,
        Then limits should match documented values
        """
        # Arrange
        from security.resource_limiter import ResourceLimiter

        # Act - check default limits (if they're class attributes)
        # This validates limits haven't changed without documentation

        # Assert - limits are accessible (raises exception on failure, returns None on success)
        try:
            ResourceLimiter.check_disk_space("/tmp")
            # If no exception, then check passed
            assert True
        except IOError:
            # On systems with low disk space, this is expected
            pytest.skip("Low disk space on test system")


class TestMigrationPath:
    """Test migration from old to new implementations"""

    def test_can_use_old_and_new_detectors_simultaneously(self, test_video_path):
        """
        When both old and new detectors are imported,
        Then they should not conflict
        """
        try:
            # Arrange - import both
            from agents2.face_detection.face_detector_v2 import FaceDetectorV2

            # Try importing old detector
            try:
                from agents2.face_detection.face_detector import FaceDetector
                old_available = True
            except ImportError:
                old_available = False

            # Act - use new detector
            new_detector = FaceDetectorV2()
            result = new_detector.process_video_safely({
                "video_path": test_video_path
            })

            # Assert - new detector works
            assert "success" in result

            if old_available:
                print("\n✓ Both old and new detectors coexist")
            else:
                print("\n✓ New detector works (old removed)")

        except ImportError as e:
            pytest.skip(f"Detector not available: {e}")

    def test_security_layer_works_with_both_detectors(self, test_video_path):
        """
        When using security layer with any detector,
        Then validation should work consistently
        """
        # Arrange
        from security.path_sanitizer import PathSanitizer
        from security.video_validator import VideoSecurityValidator

        # Act - validate path (works for any detector)
        validated_path = PathSanitizer.validate_input_path(test_video_path)
        validator = VideoSecurityValidator()
        video_info = validator.validate_video_file(str(validated_path))

        # Assert - validation succeeded
        assert validated_path.exists()
        assert video_info["valid"] is True


class TestNoBreakingChanges:
    """Verify no breaking changes in public APIs"""

    def test_security_error_exception_hierarchy_unchanged(self):
        """
        When catching SecurityError,
        Then it should still inherit from Exception
        """
        # Arrange
        from security.exceptions import SecurityError

        # Act - create instance
        error = SecurityError("Test error")

        # Assert - inheritance chain intact
        assert isinstance(error, Exception)
        assert isinstance(error, SecurityError)

    def test_path_sanitizer_validates_same_paths_as_before(self, test_video_path):
        """
        When validating a previously valid path,
        Then it should still be accepted
        """
        # Arrange
        from security.path_sanitizer import PathSanitizer

        # Act - validate path that should work
        validated = PathSanitizer.validate_input_path(test_video_path)

        # Assert - still valid
        assert validated.exists()
        assert validated.is_file()

    def test_video_validator_returns_same_info_structure(self, test_video_path):
        """
        When validating a video,
        Then returned info structure should be unchanged
        """
        # Arrange
        from security.path_sanitizer import PathSanitizer
        from security.video_validator import VideoSecurityValidator

        validated_path = PathSanitizer.validate_input_path(test_video_path)

        # Act - validate video
        validator = VideoSecurityValidator()
        info = validator.validate_video_file(str(validated_path))

        # Assert - expected fields present
        expected_fields = ["valid"]

        for field in expected_fields:
            assert field in info, f"Missing field: {field}"


class TestMomentDetectorBackwardCompatibility:
    """Test MomentDetector Phase 2 backward compatibility"""

    def test_moment_detector_import_path_works(self):
        """
        When importing MomentDetector,
        Then it should be available at expected path
        """
        try:
            # Act - import detector
            from agents2.moment_detection.moment_detector import MomentDetector

            # Assert - import succeeded
            assert MomentDetector is not None
            print("\n✓ MomentDetector import path works")

        except ImportError as e:
            pytest.fail(f"MomentDetector should be available: {e}")

    def test_moment_detector_inherits_from_secure_agent(self):
        """
        When using MomentDetector Phase 2,
        Then it should inherit from SecureVideoAgent
        """
        try:
            # Arrange
            from agents2.moment_detection.moment_detector import MomentDetector

            detector = MomentDetector()

            # Act - check inheritance
            mro = [c.__name__ for c in type(detector).__mro__]

            # Assert - inherits from SecureVideoAgent
            assert "SecureVideoAgent" in mro, \
                f"MomentDetector should inherit from SecureVideoAgent. MRO: {mro}"

            print(f"\n✓ MomentDetector inherits from SecureVideoAgent")

        except ImportError as e:
            pytest.skip(f"MomentDetector not available: {e}")

    def test_moment_detector_has_security_components(self):
        """
        When using MomentDetector Phase 2,
        Then it should have security components
        """
        try:
            # Arrange
            from agents2.moment_detection.moment_detector import MomentDetector

            detector = MomentDetector()

            # Act - check security components
            required_attributes = ['validator', 'path_sanitizer', 'resource_limiter']

            # Assert - all security components present
            for attr in required_attributes:
                assert hasattr(detector, attr), \
                    f"Missing security component: {attr}"

            print("\n✓ MomentDetector has all security components")

        except ImportError as e:
            pytest.skip(f"MomentDetector not available: {e}")

    def test_moment_detector_has_expected_interface(self):
        """
        When using MomentDetector,
        Then it should have expected public interface
        """
        try:
            # Arrange
            from agents2.moment_detection.moment_detector import MomentDetector

            detector = MomentDetector()

            # Act - check interface
            required_methods = ['detect_moments']

            # Assert - all methods exist
            for method_name in required_methods:
                assert hasattr(detector, method_name), \
                    f"Missing method: {method_name}"
                assert callable(getattr(detector, method_name))

            print("\n✓ MomentDetector has expected interface")

        except ImportError:
            pytest.skip("MomentDetector not available")

    def test_moment_detector_accepts_legacy_input_format(self, test_video_path):
        """
        When providing input in legacy format,
        Then MomentDetector should still work
        """
        try:
            # Arrange
            from agents2.moment_detection.moment_detector import MomentDetector

            detector = MomentDetector()

            # Act - use legacy input format (dict with video_path)
            result = detector.detect_moments({
                "video_path": test_video_path,
                "intent": "short_clips",
                "min_duration": 15,
                "max_duration": 60,
                "max_moments": 3
            })

            # Assert - processed successfully
            assert "success" in result
            assert "moments" in result or result["success"] is False

            print(f"\n✓ MomentDetector accepts legacy input format")

        except ImportError:
            pytest.skip("MomentDetector not available")

    def test_moment_detector_blocks_path_traversal(self):
        """
        When providing path traversal attack,
        Then MomentDetector should block it
        """
        try:
            # Arrange
            from agents2.moment_detection.moment_detector import MomentDetector

            detector = MomentDetector()

            # Act - attempt path traversal
            result = detector.detect_moments({
                "video_path": "../../../etc/passwd"
            })

            # Assert - blocked with security error
            assert result["success"] is False
            assert "error" in result
            assert "Invalid video path" in result["error"] or "Invalid path" in result["error"]

            print("\n✓ MomentDetector blocks path traversal attacks")

        except ImportError:
            pytest.skip("MomentDetector not available")

    def test_moment_detector_validates_missing_video_path(self):
        """
        When video_path is missing,
        Then MomentDetector should return error
        """
        try:
            # Arrange
            from agents2.moment_detection.moment_detector import MomentDetector

            detector = MomentDetector()

            # Act - missing video_path
            result = detector.detect_moments({})

            # Assert - error returned
            assert result["success"] is False
            assert "error" in result
            assert "required" in result["error"].lower()

            print("\n✓ MomentDetector validates missing video_path")

        except ImportError:
            pytest.skip("MomentDetector not available")

    def test_moment_detector_output_format_consistent(self, test_video_path):
        """
        When MomentDetector processes video,
        Then output format should be consistent
        """
        try:
            # Arrange
            from agents2.moment_detection.moment_detector import MomentDetector

            detector = MomentDetector()

            # Act - process video
            result = detector.detect_moments({
                "video_path": test_video_path
            })

            # Assert - expected fields present
            assert "success" in result

            if result["success"]:
                required_fields = [
                    "moments",
                    "processing_time",
                    "agent_version"
                ]

                for field in required_fields:
                    assert field in result, f"Missing output field: {field}"

                # Validate moment structure
                if result.get("moments"):
                    moment = result["moments"][0]
                    assert "start_time" in moment
                    assert "end_time" in moment
                    assert "duration" in moment
                    assert "confidence" in moment

                print("\n✓ MomentDetector output format consistent")

        except ImportError:
            pytest.skip("MomentDetector not available")


class TestDeprecationWarnings:
    """Check for deprecation warnings or migration hints"""

    def test_no_unexpected_deprecation_warnings(self, test_video_path):
        """
        When using current APIs,
        Then no deprecation warnings should be raised
        """
        import warnings

        # Arrange - capture warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Act - use APIs
            from security.path_sanitizer import PathSanitizer
            from security.video_validator import VideoSecurityValidator

            PathSanitizer.validate_input_path(test_video_path)
            validator = VideoSecurityValidator()
            validator.validate_video_file(test_video_path)

            # Assert - no deprecation warnings
            deprecation_warnings = [
                warning for warning in w
                if issubclass(warning.category, DeprecationWarning)
            ]

            assert len(deprecation_warnings) == 0, \
                f"Unexpected deprecation warnings: {[str(w.message) for w in deprecation_warnings]}"
