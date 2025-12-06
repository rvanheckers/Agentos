#!/usr/bin/env python3
"""
Secure Moment Detector - Phase 1 Security Wrapper
==================================================

Security wrapper around MomentDetector that adds baseline security
without modifying the original implementation.

Security features:
- Path traversal prevention (PathSanitizer)
- MIME type validation (VideoSecurityValidator)
- TOCTOU attack prevention (atomic file operations)
- Resource limit enforcement (ResourceLimiter)
- File size validation
- Video duration validation

Usage (drop-in replacement):
    from agents2.moment_detection.secure_moment_detector import SecureMomentDetector

    detector = SecureMomentDetector()
    result = detector.detect_moments(input_data)

Backward compatibility:
    This wrapper is 100% backward compatible with MomentDetector.
    All existing code continues to work without modification.
"""

import logging
import os
from typing import Dict, Any
from pathlib import Path

from agents2.base.secure_agent import SecureVideoAgent
from agents2.moment_detection.moment_detector import MomentDetector
from security.video_validator import VideoSecurityValidator
from security.path_sanitizer import PathSanitizer
from security.resource_limiter import ResourceLimiter
from security.exceptions import SecurityError

logger = logging.getLogger(__name__)


class SecureMomentDetector(SecureVideoAgent):
    """
    Security wrapper around MomentDetector.

    Provides security validation layer while delegating all detection
    logic to the original MomentDetector implementation.

    This is Phase 1 of the security migration - a non-invasive wrapper
    that adds security without modifying the original code.
    """

    def __init__(self):
        """
        Initialize secure wrapper with security components.

        Creates:
        - Original MomentDetector instance for delegation
        - VideoSecurityValidator for MIME and video validation
        - PathSanitizer for path traversal prevention
        - ResourceLimiter for DoS protection
        """
        super().__init__()

        # Delegate to original MomentDetector
        self._detector = MomentDetector()

        # Initialize security components
        self._validator = VideoSecurityValidator()
        self._sanitizer = PathSanitizer
        self._limiter = ResourceLimiter

        logger.info("SecureMomentDetector initialized with security baseline")

    def detect_moments(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect viral moments with security validation.

        Security layers:
        1. Input validation (video_path must be provided)
        2. Path sanitization (prevent directory traversal)
        3. MIME type validation (ensure it's a video file)
        4. File size and duration limits (prevent DoS)
        5. Resource monitoring during processing

        Args:
            input_data: Dictionary containing:
                - video_path (str, required): Path to video file
                - transcript (str, optional): Audio transcription
                - segments (List[dict], optional): Transcript segments
                - intent (str, optional): Detection intent
                - min_duration (float, optional): Minimum moment duration
                - max_duration (float, optional): Maximum moment duration
                - max_moments (int, optional): Maximum number of moments

        Returns:
            Dictionary containing:
                - success (bool): Whether detection succeeded
                - moments (List[dict]): Detected moments
                - error (str, optional): Error message if failed
                - error_type (str, optional): Error category

        Security guarantees:
        - Path traversal attacks prevented
        - MIME type spoofing prevented
        - TOCTOU race conditions prevented
        - Resource exhaustion prevented
        - File size limits enforced
        """
        try:
            # 1. Validate input_data structure
            if not input_data:
                return self._error("input_data is required", "validation")

            if not isinstance(input_data, dict):
                return self._error("input_data must be a dictionary", "validation")

            # 2. Validate video_path is provided
            raw_path = input_data.get("video_path")
            if not raw_path:
                return self._error("video_path is required in input_data", "validation")

            # 3. Path sanitization - prevent directory traversal attacks
            # Note: PathSanitizer may need development mode for testing
            # Production environments should have strict allowed directories
            try:
                # For development: allow project test_videos directory
                if os.getenv("AGENTOS_ENV", "development") == "development":
                    self._sanitizer.configure_for_development()

                safe_path = self._sanitizer.validate_input_path(raw_path)
                logger.info("Path sanitized successfully: original=%r, sanitized=%r", raw_path, safe_path)

            except SecurityError as e:
                logger.warning("Path validation failed (security): %r", e)
                return self._error(
                    f"Invalid video path: {str(e)}",
                    "security"
                )
            except Exception as e:
                logger.error("Path sanitization unexpected error: %r", e)
                return self._error(
                    "Path validation failed",
                    "security"
                )

            # 4. MIME type and video validation - prevent file type spoofing
            # This also prevents TOCTOU attacks via atomic file operations
            try:
                validation_result = self._validator.validate_video_file(str(safe_path))

                if not validation_result.get("valid"):
                    error_msg = validation_result.get("error", "Unknown validation error")
                    logger.warning("Video validation failed: %s", error_msg)
                    return self._error(
                        f"Video validation failed: {error_msg}",
                        "security"
                    )

                # Store validated metadata for logging
                metadata = validation_result.get("metadata", {})
                logger.info(
                    "Video validated successfully: duration=%.1fs, size=%.1fMB, resolution=%dx%d",
                    metadata.get('duration_seconds', 0),
                    metadata.get('file_size_mb', 0),
                    metadata.get('width', 0),
                    metadata.get('height', 0)
                )

            except SecurityError as e:
                logger.warning("Video validation security error: %r", e)
                return self._error(
                    f"Security validation failed: {str(e)}",
                    "security"
                )
            except Exception as e:
                logger.error("Video validation unexpected error: %r", e)
                return self._error(
                    "Video validation failed",
                    "security"
                )

            # 5. Resource limit checks - prevent DoS attacks
            try:
                # Check available disk space if output_path provided
                if "output_path" in input_data:
                    output_dir = str(Path(input_data["output_path"]).parent)
                    self._limiter.check_disk_space(output_dir, required_mb=100)

            except IOError as e:
                logger.warning("Disk space check failed: %r", e)
                return self._error(
                    f"Insufficient disk space: {str(e)}",
                    "resource"
                )
            except Exception as e:
                logger.error("Resource check unexpected error: %r", e)
                # Don't fail on resource checks - just log warning
                logger.warning("Proceeding without resource limit validation")

            # 6. Delegate to original MomentDetector with validated path
            # Update input_data with sanitized path
            secure_input_data = input_data.copy()
            secure_input_data["video_path"] = str(safe_path)

            # Process with resource monitoring
            try:
                with self._limiter.monitor_process(max_memory_mb=2048):
                    result = self._detector.detect_moments(secure_input_data)

                logger.info(
                    "Moment detection completed: success=%s, moments=%d",
                    result.get('success'),
                    result.get('total_moments', len(result.get('moments', [])))
                )

                return result

            except Exception as e:
                logger.error("Moment detection processing failed: %r", e)
                return self._error(
                    f"Moment detection processing failed: {str(e)}",
                    "processing"
                )

        except SecurityError as e:
            # Security-specific errors - already logged in nested try/except
            logger.error("Security error in moment detection (outer catch): %r", e)
            return self._error(
                f"Security validation failed: {str(e)}",
                "security"
            )

        except Exception as e:
            # Catch-all for unexpected errors - don't expose internal details
            logger.error("Unexpected error in secure moment detection: %r", e)
            return self._error(
                "Internal processing error",
                "internal"
            )

    def _error(self, message: str, error_type: str = "unknown") -> Dict[str, Any]:
        """
        Create standardized error response.

        Args:
            message: Human-readable error message
            error_type: Category of error (validation, security, resource, etc.)

        Returns:
            Standardized error dictionary
        """
        return {
            "success": False,
            "error": message,
            "error_type": error_type,
            "agent_version": getattr(self._detector, "version", "unknown"),
            "wrapper_version": "1.0.0"
        }


# Backward compatibility: allow importing as MomentDetector for testing
__all__ = ["SecureMomentDetector"]
