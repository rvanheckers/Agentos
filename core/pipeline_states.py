"""
Pipeline State Machine for Admin-Controllable Workflows
Context7 Validated: State machine patterns for data pipelines (trust score 8.5+)

Dit bestand definieert de state machine voor de proactive pipeline architectuur.
De pipeline kan nu pauzeren op specifieke punten voor admin configuratie.
"""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime, timezone


class PipelinePhase(str, Enum):
    """
    Main pipeline phases with pause points

    Flow:
    CONFIGURING → PHASE1_RUNNING → AWAITING_ADMIN_CONFIG →
    AWAITING_USER_SELECTION → PHASE2_RUNNING → COMPLETED/FAILED
    """
    CONFIGURING = "configuring"                             # NEW: Before pipeline starts
    PHASE1_RUNNING = "phase1_running"                       # During Phase 1
    AWAITING_ADMIN_CONFIG = "awaiting_admin_config"         # NEW: Pause after Phase 1
    AWAITING_USER_SELECTION = "awaiting_user_selection"     # User selects moments
    PHASE2_RUNNING = "phase2_running"                       # During Phase 2
    COMPLETED = "completed"                                 # Success
    FAILED = "failed"                                       # Error occurred


class PipelineStep(str, Enum):
    """Individual pipeline steps for granular tracking"""
    # Phase 1 steps
    DOWNLOAD_VIDEO = "download_video"
    TRANSCRIBE_AUDIO = "transcribe_audio"
    DETECT_MOMENTS = "detect_moments"
    DETECT_FACES = "detect_faces"

    # Phase 2 steps
    INTELLIGENT_CROP = "intelligent_crop"
    CUT_VIDEOS = "cut_videos"


class StepStatus(str, Enum):
    """Status of individual pipeline steps"""
    PENDING = "pending"
    CONFIGURABLE = "configurable"
    IN_PROGRESS = "in_progress"
    PAUSED_FOR_CONFIG = "paused_for_config"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class Phase1Config:
    """
    Pre-flight configuration for Phase 1 (analysis phase)

    Deze settings bepalen HOE Phase 1 de video analyseert.
    Admin kan deze aanpassen VOORDAT Phase 1 start.
    """

    def __init__(self):
        # Moment detection settings
        self.max_moments = 5                    # Maximum aantal viral moments te detecteren
        self.cluster_gap_s = 8.0                # Minimale afstand tussen momenten (seconds)
        self.min_viral_score = 70               # Threshold voor viral score (0-100)

        # Face detection settings
        self.face_confidence = 0.6              # Confidence threshold voor face detection (0.0-1.0)
        self.sample_interval = 2.0              # Frame sampling interval (seconds)
        self.min_faces_required = 1             # Minimum aantal gezichten vereist

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage"""
        return {
            "max_moments": self.max_moments,
            "cluster_gap_s": self.cluster_gap_s,
            "min_viral_score": self.min_viral_score,
            "face_confidence": self.face_confidence,
            "sample_interval": self.sample_interval,
            "min_faces_required": self.min_faces_required
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Phase1Config':
        """Create from dictionary (from database)"""
        config = cls()
        config.max_moments = data.get('max_moments', 5)
        config.cluster_gap_s = data.get('cluster_gap_s', 8.0)
        config.min_viral_score = data.get('min_viral_score', 70)
        config.face_confidence = data.get('face_confidence', 0.6)
        config.sample_interval = data.get('sample_interval', 2.0)
        config.min_faces_required = data.get('min_faces_required', 1)
        return config


class Phase2Config:
    """
    Configuration for Phase 2 (clip generation)

    Deze settings worden ingesteld NA Phase 1 compleet is.
    Admin kan Phase 1 results reviewen en dan Phase 2 configureren.
    """

    def __init__(self):
        # Crop settings
        self.crop_method = "auto"                           # "auto" | "manual" | "face-focused"
        self.manual_crop_coords: Optional[Dict[str, int]] = None  # {x, y, width, height}

        # Clip generation settings
        self.clip_length = 30                               # Seconds per clip
        self.target_aspect_ratio = "9:16"                   # For social media (vertical)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage"""
        return {
            "crop_method": self.crop_method,
            "manual_crop_coords": self.manual_crop_coords,
            "clip_length": self.clip_length,
            "target_aspect_ratio": self.target_aspect_ratio
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Phase2Config':
        """Create from dictionary (from database)"""
        config = cls()
        config.crop_method = data.get('crop_method', 'auto')
        config.manual_crop_coords = data.get('manual_crop_coords')
        config.clip_length = data.get('clip_length', 30)
        config.target_aspect_ratio = data.get('target_aspect_ratio', '9:16')
        return config


class PipelineConfig:
    """
    Complete pipeline configuration container

    Deze class bundelt alle configuratie voor de hele pipeline.
    Wordt opgeslagen in Job.pipeline_config als JSONB.
    """

    def __init__(self, job_id: str):
        self.job_id = job_id
        self.phase1_config = Phase1Config()
        self.phase2_config = Phase2Config()
        self.created_at = datetime.now(timezone.utc)

        # Workflow flags
        self.auto_flow = False  # True = User UI (auto-continue), False = Admin flow (pause for config)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            "job_id": self.job_id,
            "phase1": self.phase1_config.to_dict(),
            "phase2": self.phase2_config.to_dict(),
            "auto_flow": self.auto_flow,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, job_id: str, data: Dict[str, Any]) -> 'PipelineConfig':
        """Create from dictionary (from database)"""
        config = cls(job_id)

        # Load phase configs
        if 'phase1' in data:
            config.phase1_config = Phase1Config.from_dict(data['phase1'])
        if 'phase2' in data:
            config.phase2_config = Phase2Config.from_dict(data['phase2'])

        # Load workflow flags
        config.auto_flow = data.get('auto_flow', False)

        # Load timestamp
        if 'created_at' in data:
            config.created_at = datetime.fromisoformat(data['created_at'])

        return config


# Backwards compatibility mapping (old phase names → new phase names)
LEGACY_PHASE_MAPPING = {
    'phase1_analysis': PipelinePhase.PHASE1_RUNNING,
    'awaiting_selection': PipelinePhase.AWAITING_USER_SELECTION,
    'phase2_generation': PipelinePhase.PHASE2_RUNNING,
    'completed': PipelinePhase.COMPLETED,
    'failed': PipelinePhase.FAILED
}


def migrate_legacy_phase(old_phase: str) -> PipelinePhase:
    """
    Convert legacy phase names to new PipelinePhase enum

    Voor backwards compatibility met oude database records.
    """
    return LEGACY_PHASE_MAPPING.get(old_phase, PipelinePhase.CONFIGURING)
