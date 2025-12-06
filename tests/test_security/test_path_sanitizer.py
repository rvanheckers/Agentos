"""
Security tests for path sanitization
"""
import pytest
from pathlib import Path
import tempfile
import os
from security.path_sanitizer import PathSanitizer
from security.exceptions import SecurityError


class TestPathSanitizer:
    """Test suite for PathSanitizer"""

    def test_path_traversal_attack_blocked(self):
        """Should block path traversal attempts like ../../etc/passwd"""
        with pytest.raises(SecurityError):
            PathSanitizer.validate_input_path("../../etc/passwd")

    def test_absolute_path_traversal_blocked(self):
        """Should block attempts to access system files"""
        with pytest.raises(SecurityError):
            PathSanitizer.validate_input_path("/etc/passwd")

    def test_relative_path_traversal_blocked(self):
        """Should block relative path traversal"""
        with pytest.raises(SecurityError):
            PathSanitizer.validate_input_path("../../../etc/shadow")

    def test_output_path_traversal_blocked(self):
        """Should block output path traversal"""
        with pytest.raises(SecurityError):
            PathSanitizer.validate_output_path("/etc/malicious_output")

    def test_configure_for_development(self):
        """Should add development paths when configured"""
        original_input_dirs = PathSanitizer.ALLOWED_INPUT_DIRS.copy()
        original_output_dirs = PathSanitizer.ALLOWED_OUTPUT_DIRS.copy()

        PathSanitizer.configure_for_development()

        # Check that new directories were added
        assert len(PathSanitizer.ALLOWED_INPUT_DIRS) > len(original_input_dirs)
        assert len(PathSanitizer.ALLOWED_OUTPUT_DIRS) > len(original_output_dirs)

        # Restore original state
        PathSanitizer.ALLOWED_INPUT_DIRS = original_input_dirs
        PathSanitizer.ALLOWED_OUTPUT_DIRS = original_output_dirs

    def test_nonexistent_path_rejected(self):
        """Should reject paths that don't exist for input validation"""
        with pytest.raises(SecurityError):
            PathSanitizer.validate_input_path("/var/agentos/uploads/nonexistent.mp4")

    def test_allowed_dirs_configured(self):
        """Should have default allowed directories configured"""
        assert len(PathSanitizer.ALLOWED_INPUT_DIRS) > 0
        assert len(PathSanitizer.ALLOWED_OUTPUT_DIRS) > 0

    def test_security_error_contains_helpful_message(self):
        """SecurityError should contain helpful error message"""
        try:
            PathSanitizer.validate_input_path("../../etc/passwd")
            assert False, "Should have raised SecurityError"
        except SecurityError as e:
            error_msg = str(e)
            assert len(error_msg) > 0
            assert "path" in error_msg.lower() or "invalid" in error_msg.lower()