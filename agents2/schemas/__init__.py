"""
Pydantic Data Contract Schemas for AgentOS
==========================================

Centralized data validation schemas for all agents.

Available schemas:
- video_processing: CropCoordinates, SubMoment, CropsPerMoment
"""

from agents2.schemas.video_processing import (
    CropCoordinates,
    SubMoment,
    CropsPerMoment
)

__all__ = [
    'CropCoordinates',
    'SubMoment',
    'CropsPerMoment',
]
