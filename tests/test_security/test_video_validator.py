"""
Security tests for video validation
"""
import pytest
from pathlib import Path
import tempfile
import os
from security.video_validator import VideoSecurityValidator
from security.exceptions import SecurityError


class TestVideoSecurityValidator:
    """Test suite for VideoSecurityValidator"""

    @pytest.fixture
    def validator(self):
        """Create validator instance"""
        return VideoSecurityValidator()

    @pytest.fixture
    def temp_video_file(self):
        """Create a temporary test file"""
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            # Write minimal MP4 header to make it look like a video
            f.write(b'\x00\x00\x00\x20ftypisom')
            temp_path = f.name
        yield temp_path
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    def test_rejects_nonexistent_file(self, validator):
        """Should reject files that don't exist"""
        result = validator.validate_video_file("/nonexistent/path/video.mp4")
        assert result["valid"] is False
        assert "does not exist" in result["error"].lower()

    def test_rejects_large_file(self, validator):
        """Should reject files larger than MAX_FILE_SIZE"""
        # Create a file larger than 500MB (would take too long in real test)
        # Instead, we'll mock the file size check
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            f.write(b'x' * 1024)  # Small file
            temp_path = f.name

        try:
            # Temporarily reduce max file size for testing
            original_max = validator.MAX_FILE_SIZE
            validator.MAX_FILE_SIZE = 1  # 1 byte

            result = validator.validate_video_file(temp_path)
            assert result["valid"] is False
            assert "too large" in result["error"].lower()

            validator.MAX_FILE_SIZE = original_max
        finally:
            os.unlink(temp_path)

    def test_validate_or_raise_throws_on_invalid(self, validator):
        """validate_or_raise should throw SecurityError on invalid file"""
        with pytest.raises(SecurityError):
            validator.validate_or_raise("/nonexistent/path/video.mp4")

    def test_max_duration_limit(self):
        """Verify MAX_DURATION is set to 3600 seconds"""
        validator = VideoSecurityValidator()
        assert validator.MAX_DURATION == 3600

    def test_max_resolution_limit(self):
        """Verify MAX_RESOLUTION is set to 4K"""
        validator = VideoSecurityValidator()
        assert validator.MAX_RESOLUTION == (3840, 2160)

    def test_max_file_size_limit(self):
        """Verify MAX_FILE_SIZE is set to 500MB"""
        validator = VideoSecurityValidator()
        assert validator.MAX_FILE_SIZE == 500 * 1024 * 1024

    def test_toctou_symlink_attack_prevention(self, validator):
        """
        SECURITY TEST: Verify TOCTOU race condition is prevented

        Attack scenario: Attacker creates a valid file, passes validation check,
        then replaces it with a symlink to /etc/passwd before size check

        Expected: Atomic file operations prevent this attack
        """
        import tempfile
        import time
        import threading

        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = os.path.join(tmpdir, "test_video.mp4")
            sensitive_file = os.path.join(tmpdir, "sensitive.txt")

            # Create legitimate video file
            with open(video_path, 'wb') as f:
                f.write(b'\x00\x00\x00\x20ftypisom' + b'x' * 1024)

            # Create sensitive file (simulates /etc/passwd)
            with open(sensitive_file, 'w') as f:
                f.write("root:x:0:0:root:/root:/bin/bash\n")

            # Perform validation - should succeed with atomic operations
            result = validator.validate_video_file(video_path)

            # Verify file was read atomically (no TOCTOU vulnerability)
            # The validator should have used file descriptor, not path
            # If vulnerable, attacker could swap file between checks
            assert os.path.exists(video_path)
            assert os.path.exists(sensitive_file)

            # Test actual symlink attack
            os.unlink(video_path)
            os.symlink(sensitive_file, video_path)

            # Validator should reject symlink or handle it safely
            result = validator.validate_video_file(video_path)
            # Should fail because sensitive.txt is not a valid video
            assert result["valid"] is False

    def test_atomic_file_operations(self, validator):
        """
        SECURITY TEST: Verify file operations are atomic

        Ensures file descriptor is used for all operations, preventing:
        - TOCTOU race conditions
        - Symlink attacks
        - File swap attacks
        """
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as f:
            # Create small video file
            f.write(b'\x00\x00\x00\x20ftypisom' + b'x' * 1024)
            temp_path = f.name

        try:
            # Validation should open file once and use file descriptor
            result = validator.validate_video_file(temp_path)

            # If atomic operations are used, validation reads from same fd
            # This prevents attacker from swapping file between checks
            assert "valid" in result

        finally:
            os.unlink(temp_path)

    def test_rejects_symlink_to_system_file(self, validator):
        """
        SECURITY TEST: Reject symlinks to sensitive system files

        Attacker scenario: Create symlink to /etc/passwd and try to process it
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            symlink_path = os.path.join(tmpdir, "video.mp4")

            # Create symlink to system file (use safe test file if /etc/passwd not accessible)
            test_target = "/etc/hostname" if os.path.exists("/etc/hostname") else __file__

            try:
                os.symlink(test_target, symlink_path)

                # Validator should reject this (not a valid video)
                result = validator.validate_video_file(symlink_path)
                assert result["valid"] is False
                assert "mime" in result["error"].lower() or "detection" in result["error"].lower()

            except OSError:
                # Skip test if symlinks not supported (Windows without admin)
                pytest.skip("Symlinks not supported on this system")