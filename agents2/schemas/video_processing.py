#!/usr/bin/env python3
"""
Pydantic Data Contract Schemas for Video Processing Pipeline
============================================================

Context7-compliant data validation for split-screen shot sequencing.

These schemas enforce:
- Type safety at component boundaries
- Runtime validation with descriptive errors
- Coordinate bounds checking
- Temporal overlap detection for sub-moments
- Self-documenting API through field descriptions

Version: 1.0.0 (Context7 Compliant)
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import List, Optional, Literal


class CropCoordinates(BaseModel):
    """
    Video crop coordinates (validated against video bounds)

    Used for smart cropping to 9:16 aspect ratio with panel switching
    in split-screen videos.
    """
    x: int = Field(ge=0, description="X-offset from top-left corner (pixels)")
    y: int = Field(ge=0, description="Y-offset from top-left corner (pixels)")
    width: int = Field(gt=0, description="Crop width in pixels")
    height: int = Field(gt=0, description="Crop height in pixels")

    @field_validator('width', 'height')
    @classmethod
    def validate_dimensions(cls, v, info):
        """Validate dimensions are within reasonable bounds"""
        if v > 7680:  # Max 8K resolution
            raise ValueError(
                f"{info.field_name} {v}px exceeds maximum allowed (7680px for 8K)"
            )
        if v < 10:  # Minimum reasonable crop size
            raise ValueError(
                f"{info.field_name} {v}px is too small (minimum 10px)"
            )
        return v

    @field_validator('x', 'y')
    @classmethod
    def validate_offsets(cls, v, info):
        """Validate offsets are within reasonable bounds"""
        if v > 7680:  # Max 8K resolution
            raise ValueError(
                f"{info.field_name} offset {v}px exceeds maximum (7680px for 8K)"
            )
        return v

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "x": 0,
                "y": 0,
                "width": 960,
                "height": 1080
            }
        }
    )


class SubMoment(BaseModel):
    """
    Sub-moment crop definition for V3.2 shot sequencing

    Represents a single shot within a moment, enabling dynamic panel
    switching in split-screen videos (establishing → single → reaction).
    """
    moment_index: int = Field(ge=0, description="Parent moment index")
    sub_moment_index: Optional[int] = Field(
        default=None, ge=0,
        description="Sub-moment index within parent moment (None for legacy)"
    )
    start_time: float = Field(
        ge=0,
        alias="moment_start",
        description="Start timestamp (seconds)"
    )
    end_time: float = Field(
        gt=0,
        alias="moment_end",
        description="End timestamp (seconds)"
    )
    crop_coordinates: CropCoordinates
    shot_type: Optional[Literal["establishing", "single", "reaction"]] = Field(
        default=None,
        description="Cinematographic shot type for sub-moment"
    )

    @model_validator(mode='after')
    def validate_time_constraints(self):
        """Ensure end_time > start_time and validate duration"""
        if self.end_time <= self.start_time:
            raise ValueError(
                f"end_time ({self.end_time}s) must be greater than start_time ({self.start_time}s)"
            )

        duration = self.end_time - self.start_time
        if duration < 1.0:
            raise ValueError(
                f"Sub-moment duration ({duration:.2f}s) is too short (minimum 1.0s)"
            )
        if duration > 120.0:
            raise ValueError(
                f"Sub-moment duration ({duration:.2f}s) exceeds maximum (120s)"
            )

        return self

    model_config = ConfigDict(
        populate_by_name=True,  # Accept both alias (moment_start) and field name (start_time)
        json_schema_extra = {
            "example": {
                "moment_index": 0,
                "sub_moment_index": 1,
                "start_time": 13.5,
                "end_time": 21.8,
                "crop_coordinates": {
                    "x": 0,
                    "y": 0,
                    "width": 960,
                    "height": 1080
                },
                "shot_type": "single"
            }
        }
    )


class CropsPerMoment(BaseModel):
    """
    Collection of crops for video cutting (with sub-moment support)

    Passed from intelligent_crop → cut_videos in Celery chain.
    Enables split-screen shot sequencing (1 moment → N sub-moments).
    """
    crops_per_moment: List[SubMoment] = Field(
        min_items=1,
        description="List of crop definitions (may include sub-moments)"
    )
    crop_mode: Literal["per_moment", "global"] = Field(
        default="per_moment",
        description="Crop mode: per-moment (V3.2) or global (legacy)"
    )
    success: bool = Field(
        default=True,
        description="Indicates if intelligent cropping succeeded"
    )

    @field_validator('crops_per_moment')
    @classmethod
    def validate_no_temporal_overlap(cls, crops):
        """
        Ensure sub-moments don't overlap in time within same parent moment

        This prevents invalid shot sequences like:
        - Sub-moment 0: 10s-20s
        - Sub-moment 1: 15s-25s  ← INVALID (overlaps with sub-moment 0)
        """
        # Group by moment_index
        moments = {}
        for crop in crops:
            moment_idx = crop.moment_index
            if moment_idx not in moments:
                moments[moment_idx] = []
            moments[moment_idx].append(
                (crop.start_time, crop.end_time, crop.sub_moment_index)
            )

        # Check for overlaps within each moment
        for moment_idx, times in moments.items():
            times_sorted = sorted(times, key=lambda x: x[0])  # Sort by start_time

            for i in range(len(times_sorted) - 1):
                current_end = times_sorted[i][1]
                next_start = times_sorted[i+1][0]

                if current_end > next_start:
                    raise ValueError(
                        f"Temporal overlap in moment {moment_idx}: "
                        f"sub-moment ends at {current_end:.2f}s but next starts at {next_start:.2f}s"
                    )

        return crops

    @field_validator('crops_per_moment')
    @classmethod
    def validate_sub_moment_indices(cls, crops):
        """
        Validate sub-moment indices are sequential within each moment

        If sub-moment indices exist, they should be 0, 1, 2, ... (no gaps)
        """
        # Group by moment_index
        moments = {}
        for crop in crops:
            moment_idx = crop.moment_index
            sub_idx = crop.sub_moment_index

            if sub_idx is not None:  # Only check if sub-moments are used
                if moment_idx not in moments:
                    moments[moment_idx] = []
                moments[moment_idx].append(sub_idx)

        # Check sequential indices
        for moment_idx, sub_indices in moments.items():
            sorted_indices = sorted(set(sub_indices))
            expected = list(range(len(sorted_indices)))

            if sorted_indices != expected:
                raise ValueError(
                    f"Sub-moment indices for moment {moment_idx} are not sequential: "
                    f"expected {expected}, got {sorted_indices}"
                )

        return crops

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "crops_per_moment": [
                    {
                        "moment_index": 0,
                        "sub_moment_index": 0,
                        "start_time": 6.2,
                        "end_time": 13.5,
                        "crop_coordinates": {"x": 0, "y": 0, "width": 1920, "height": 1080},
                        "shot_type": "establishing"
                    },
                    {
                        "moment_index": 0,
                        "sub_moment_index": 1,
                        "start_time": 13.5,
                        "end_time": 21.8,
                        "crop_coordinates": {"x": 0, "y": 0, "width": 960, "height": 1080},
                        "shot_type": "single"
                    }
                ],
                "crop_mode": "per_moment",
                "success": True
            }
        }
    )
