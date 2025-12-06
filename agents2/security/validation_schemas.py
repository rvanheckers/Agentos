#!/usr/bin/env python3
"""
Security Validation Schemas - Pydantic Models for Input Validation
==================================================================

OWASP-compliant validation schemas for AgentOS video processing system.
Implements defense-in-depth patterns validated by Context7.

Context7 References:
- OWASP Cheat Sheet Series (trust score 10)
- Pydantic validation patterns (trust score 9.6)

Security Controls:
1. JSONB Injection Prevention: Strict type validation, range limits
2. XSS Prevention: String length limits, character set validation
3. Data Integrity: Constraint validation for all numeric inputs
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, constr, confloat, conint
import re
import html


class BoundingBoxCoordinates(BaseModel):
    """
    Validated bounding box coordinates for face detection.

    Security: Prevents JSONB injection via oversized/malicious coordinates.
    OWASP Control: Input validation with strict numeric ranges.

    Constraints:
    - x, y: Must be within video frame dimensions (0-3840 for 4K)
    - width, height: Must be positive and reasonable (1-3840)
    - All values: Must be non-negative integers
    """
    x: conint(ge=0, le=3840) = Field(
        ...,
        description="X coordinate (left edge of bounding box)",
        examples=[100, 500]
    )
    y: conint(ge=0, le=3840) = Field(
        ...,
        description="Y coordinate (top edge of bounding box)",
        examples=[50, 200]
    )
    width: conint(ge=1, le=3840) = Field(
        ...,
        description="Width of bounding box in pixels",
        examples=[150, 300]
    )
    height: conint(ge=1, le=3840) = Field(
        ...,
        description="Height of bounding box in pixels",
        examples=[200, 400]
    )

    @field_validator('width', 'height')
    @classmethod
    def validate_positive_dimensions(cls, v: int) -> int:
        """Ensure dimensions are positive (defense-in-depth)."""
        if v <= 0:
            raise ValueError("Dimensions must be positive")
        return v


class FaceDetection(BaseModel):
    """
    Validated face detection result with all metadata.

    Security: Prevents injection attacks via face detection metadata.
    OWASP Control: Multi-layer validation for all face attributes.

    Constraints:
    - timestamp: 0 to 86400 seconds (24 hours max video)
    - confidence: 0.0 to 1.0 (normalized probability)
    - bbox: Validated bounding box coordinates
    """
    timestamp: confloat(ge=0.0, le=86400.0) = Field(
        ...,
        description="Timestamp in video (seconds)",
        examples=[1.5, 30.0, 120.5]
    )
    confidence: confloat(ge=0.0, le=1.0) = Field(
        ...,
        description="Detection confidence (0-1)",
        examples=[0.85, 0.92, 0.99]
    )
    bbox: BoundingBoxCoordinates = Field(
        ...,
        description="Bounding box coordinates"
    )

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: float) -> float:
        """Ensure timestamp is non-negative and reasonable."""
        if v < 0:
            raise ValueError("Timestamp must be non-negative")
        if v > 86400:  # 24 hours
            raise ValueError("Timestamp exceeds maximum video duration (24h)")
        return v


class FaceDetectionList(BaseModel):
    """
    Validated list of face detections with size limits.

    Security: Prevents DoS via oversized face detection arrays.
    OWASP Control: Array size limits, payload validation.

    Constraints:
    - faces: Maximum 10,000 detections per video (prevents DoS)
    - All faces: Must pass FaceDetection validation
    """
    faces: List[FaceDetection] = Field(
        default_factory=list,
        max_length=10000,
        description="List of face detections"
    )

    @field_validator('faces')
    @classmethod
    def validate_face_list(cls, v: List[FaceDetection]) -> List[FaceDetection]:
        """Additional validation for face detection list."""
        if len(v) > 10000:
            raise ValueError("Too many face detections (max 10,000)")
        return v


class SanitizedText(BaseModel):
    """
    Sanitized text with XSS prevention.

    Security: Prevents stored XSS attacks via AI-generated content.
    OWASP Control: HTML entity encoding, length limits, character validation.

    Context7 Pattern: OWASP Cross-Site Scripting Prevention (trust score 10)
    - HTML entity encoding for all user/AI-generated content
    - Length limits to prevent DoS
    - Character set validation

    Constraints:
    - raw_text: Original unsanitized text (max 10,000 chars)
    - sanitized_text: HTML-escaped version (safe for database/display)
    - truncated: Flag indicating if text was truncated
    """
    raw_text: str = Field(
        ...,
        max_length=10000,
        description="Original text before sanitization"
    )
    sanitized_text: str = Field(
        ...,
        max_length=10500,  # Slightly larger for HTML entities
        description="HTML-escaped text safe for storage/display"
    )
    truncated: bool = Field(
        default=False,
        description="Whether text was truncated to meet length limits"
    )

    @classmethod
    def from_untrusted_input(cls, text: str, max_length: int = 10000) -> "SanitizedText":
        """
        Factory method to create sanitized text from untrusted input.

        OWASP Pattern: Output encoding for XSS prevention
        Context7 Reference: OWASP Cheat Sheet - HTML entity encoding

        Process:
        1. Truncate if needed (DoS prevention)
        2. HTML entity encode (XSS prevention)
        3. Return validated model

        Args:
            text: Untrusted input text (AI-generated, user-provided, etc.)
            max_length: Maximum allowed length before truncation

        Returns:
            SanitizedText instance with escaped content
        """
        # Step 1: Truncate if needed
        truncated = len(text) > max_length
        if truncated:
            text = text[:max_length]

        # Step 2: HTML entity encode (XSS prevention)
        # Context7: html.escape() for HTML entity encoding
        sanitized = html.escape(text, quote=True)

        # Step 3: Additional character validation (defense-in-depth)
        # Remove any control characters except newlines/tabs
        sanitized = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', sanitized)

        return cls(
            raw_text=text,
            sanitized_text=sanitized,
            truncated=truncated
        )


class MomentDescription(BaseModel):
    """
    Validated moment description with XSS prevention.

    Security: Prevents stored XSS via AI-generated moment descriptions.
    OWASP Control: Sanitized text storage with validation.

    Constraints:
    - description: Sanitized text (max 500 chars)
    - sentence_text: Sanitized transcript excerpt (max 1000 chars)
    - reasoning: Sanitized AI reasoning (max 500 chars, optional)
    """
    description: str = Field(
        ...,
        max_length=500,
        description="Sanitized moment description"
    )
    sentence_text: str = Field(
        ...,
        max_length=1000,
        description="Sanitized transcript sentence"
    )
    reasoning: Optional[str] = Field(
        None,
        max_length=500,
        description="Sanitized AI reasoning (optional)"
    )

    @field_validator('description', 'sentence_text', 'reasoning')
    @classmethod
    def validate_no_html(cls, v: Optional[str]) -> Optional[str]:
        """
        Ensure no unescaped HTML tags present (defense-in-depth).

        This validator runs AFTER sanitization to verify no HTML passed through.
        """
        if v is None:
            return v

        # Check for common XSS patterns (should not exist after sanitization)
        dangerous_patterns = [
            r'<script', r'javascript:', r'onerror=', r'onload=',
            r'<iframe', r'<object', r'<embed'
        ]

        v_lower = v.lower()
        for pattern in dangerous_patterns:
            if pattern in v_lower:
                raise ValueError(f"Potentially dangerous HTML pattern detected: {pattern}")

        return v


class VideoMetadata(BaseModel):
    """
    Validated video metadata with security constraints.

    Security: Prevents injection via video metadata fields.
    OWASP Control: Input validation for all metadata.

    Constraints:
    - duration: 0 to 86400 seconds (24 hours)
    - title: Max 200 chars, sanitized
    - keywords: Max 50 keywords, max 50 chars each
    """
    duration: confloat(ge=0.0, le=86400.0) = Field(
        ...,
        description="Video duration in seconds"
    )
    title: constr(max_length=200) = Field(
        ...,
        description="Video title (sanitized)"
    )
    keywords: List[constr(max_length=50)] = Field(
        default_factory=list,
        max_length=50,
        description="Video keywords"
    )


def validate_face_coordinates(faces_data: Any) -> List[Dict[str, Any]]:
    """
    Validate face detection coordinates from untrusted sources.

    Security Function: Prevents JSONB injection via face coordinates.
    OWASP Control: Strict type validation, range enforcement.

    Context7 Pattern: Pydantic validation for nested structures

    Args:
        faces_data: Untrusted face detection data (from AI/external API)

    Returns:
        Validated list of face dictionaries safe for database storage

    Raises:
        ValueError: If validation fails (malicious/malformed input)
    """
    # Convert to list if needed
    if not isinstance(faces_data, list):
        faces_data = []

    # Validate using Pydantic model
    try:
        # Parse each face detection
        validated_faces = []
        for face_data in faces_data:
            # Handle both flat and nested bbox structures
            if 'bbox' in face_data and isinstance(face_data['bbox'], dict):
                # Already nested
                face = FaceDetection(**face_data)
            else:
                # Flat structure, need to nest bbox
                bbox_data = {
                    'x': face_data.get('x', face_data.get('bbox_x', 0)),
                    'y': face_data.get('y', face_data.get('bbox_y', 0)),
                    'width': face_data.get('width', face_data.get('bbox_width', 1)),
                    'height': face_data.get('height', face_data.get('bbox_height', 1))
                }

                face = FaceDetection(
                    timestamp=face_data.get('timestamp', 0.0),
                    confidence=face_data.get('confidence', 0.0),
                    bbox=bbox_data
                )

            # Convert to dict for database storage
            validated_faces.append(face)

        # Final list validation
        validated_list = FaceDetectionList(faces=validated_faces)

        # Convert all Pydantic models to dicts for JSON serialization
        return [face.model_dump() for face in validated_list.faces]

    except Exception as e:
        raise ValueError(f"Face coordinate validation failed: {str(e)}")


def sanitize_ai_text(text: str, max_length: int = 10000) -> str:
    """
    Sanitize AI-generated text to prevent XSS attacks.

    Security Function: Prevents stored XSS via AI-generated content.
    OWASP Control: HTML entity encoding with length limits.

    Context7 Pattern: OWASP XSS Prevention - Output encoding

    Args:
        text: Untrusted AI-generated text
        max_length: Maximum allowed length

    Returns:
        Sanitized text safe for database storage and HTML display
    """
    if not text:
        return ""

    # Create sanitized text using validated model
    sanitized_model = SanitizedText.from_untrusted_input(text, max_length)

    return sanitized_model.sanitized_text


# Export validation functions for easy import
__all__ = [
    'BoundingBoxCoordinates',
    'FaceDetection',
    'FaceDetectionList',
    'SanitizedText',
    'MomentDescription',
    'VideoMetadata',
    'validate_face_coordinates',
    'sanitize_ai_text'
]
