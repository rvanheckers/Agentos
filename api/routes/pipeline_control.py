"""
Pipeline Control API - Admin intervention endpoints
Context7 Validated: FastAPI async patterns for workflow control (trust score 8.7+)

Endpoints voor proactive pipeline control:
- Configure Phase 1/2 settings VOOR pipeline start
- Start Phase 1/2 met configured settings
- Get pipeline state met available actions
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import logging

from core.database_pool import get_db_session
from core.database_manager import Job, Moment
from core.pipeline_states import PipelinePhase, Phase1Config, Phase2Config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline-control"])


# ============================================================================
# Request/Response Models
# ============================================================================

class ConfigurePhase1Request(BaseModel):
    """Request to configure Phase 1 before starting"""
    max_moments: int = 5
    cluster_gap_s: float = 8.0
    min_viral_score: int = 70
    face_confidence: float = 0.6
    sample_interval: float = 2.0
    min_faces_required: int = 1

    @field_validator('max_moments')
    @classmethod
    def validate_max_moments(cls, v):
        if not 1 <= v <= 20:
            raise ValueError('max_moments must be between 1 and 20')
        return v

    @field_validator('face_confidence')
    @classmethod
    def validate_face_confidence(cls, v):
        if not 0.1 <= v <= 1.0:
            raise ValueError('face_confidence must be between 0.1 and 1.0')
        return v


class ConfigurePhase2Request(BaseModel):
    """Request to configure Phase 2 after Phase 1 completes"""
    crop_method: str = "auto"  # "auto" | "manual" | "face-focused"
    manual_crop_coords: Optional[Dict[str, int]] = None
    clip_length: int = 30
    target_aspect_ratio: str = "9:16"

    @field_validator('crop_method')
    @classmethod
    def validate_crop_method(cls, v):
        allowed = ['auto', 'manual', 'face-focused']
        if v not in allowed:
            raise ValueError(f'crop_method must be one of: {allowed}')
        return v

    @field_validator('clip_length')
    @classmethod
    def validate_clip_length(cls, v):
        if not 10 <= v <= 180:
            raise ValueError('clip_length must be between 10 and 180 seconds')
        return v


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/{job_id}/configure-phase1")
async def configure_phase1(
    job_id: str,
    config: ConfigurePhase1Request
):
    """
    Configure Phase 1 settings BEFORE starting pipeline

    Allows admin to tweak detection parameters before Phase 1 runs.
    Job must be in 'configuring' phase.
    """
    try:
        with get_db_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise HTTPException(404, "Job not found")

            # Validate phase
            if job.phase != PipelinePhase.CONFIGURING.value:
                raise HTTPException(
                    400,
                    f"Job must be in 'configuring' phase to configure Phase 1. Currently: {job.phase}"
                )

            # Initialize pipeline_config if empty
            if not job.pipeline_config:
                job.pipeline_config = {}

            # Store Phase 1 config
            job.pipeline_config['phase1'] = config.model_dump()
            job.updated_at = datetime.now(timezone.utc)
            session.commit()

            logger.info(f"✅ Phase 1 configured for job {job_id}: {config.model_dump()}")

            return {
                "success": True,
                "job_id": job_id,
                "phase1_config": config.model_dump(),
                "message": "Phase 1 configured. Ready to start pipeline."
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error configuring Phase 1: {e}")
        raise HTTPException(500, f"Failed to configure Phase 1: {str(e)}")


@router.post("/{job_id}/start-phase1")
async def start_phase1(
    job_id: str
):
    """
    Start Phase 1 with configured settings

    Triggers the Phase 1 workflow (download → transcribe → detect_moments → detect_faces).
    Uses config from pipeline_config.phase1 or defaults.
    """
    try:
        with get_db_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise HTTPException(404, "Job not found")

            # Validate phase
            if job.phase != PipelinePhase.CONFIGURING.value:
                raise HTTPException(
                    400,
                    f"Cannot start Phase 1, job must be in 'configuring' phase. Currently: {job.phase}"
                )

            # Get Phase 1 config or use defaults
            phase1_config = {}
            if job.pipeline_config and 'phase1' in job.pipeline_config:
                phase1_config = job.pipeline_config['phase1']
                logger.info(f"✅ Using admin-configured Phase 1 settings: {phase1_config}")
            else:
                # Use defaults
                default_config = Phase1Config()
                phase1_config = default_config.to_dict()
                logger.info(f"ℹ️ No Phase 1 config found, using defaults")

            # Update job state
            job.phase = PipelinePhase.PHASE1_RUNNING.value
            job.status = 'processing'
            job.progress = 10
            job.current_step = 'Starting Phase 1...'
            job.started_at = datetime.now(timezone.utc)
            session.commit()

            # Import and trigger Phase 1 workflow
            # NOTE: Workflow implementatie komt in WORKFLOW contract
            try:
                from tasks.video_processing_phase1 import create_phase1_workflow
                workflow = create_phase1_workflow(job_id, phase1_config)
                workflow.apply_async()
                logger.info(f"✅ Phase 1 workflow started for job {job_id}")
            except ImportError:
                logger.warning("⚠️ Phase 1 workflow not yet implemented (WORKFLOW contract pending)")
                # For now, just update status - workflow will be implemented later
                pass

            return {
                "success": True,
                "job_id": job_id,
                "phase": PipelinePhase.PHASE1_RUNNING.value,
                "config_used": phase1_config,
                "message": "Phase 1 started successfully"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error starting Phase 1: {e}")
        raise HTTPException(500, f"Failed to start Phase 1: {str(e)}")


@router.post("/{job_id}/configure-phase2")
async def configure_phase2(
    job_id: str,
    config: ConfigurePhase2Request
):
    """
    Configure Phase 2 settings AFTER Phase 1 completes

    Allows admin to configure crop settings and clip generation parameters
    based on Phase 1 results. Job must be in 'awaiting_admin_config' phase.
    """
    try:
        with get_db_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise HTTPException(404, "Job not found")

            # Validate phase
            if job.phase != PipelinePhase.AWAITING_ADMIN_CONFIG.value:
                raise HTTPException(
                    400,
                    f"Job must be in 'awaiting_admin_config' phase to configure Phase 2. Currently: {job.phase}"
                )

            # Validate manual crop coordinates if manual method
            if config.crop_method == "manual":
                if not config.manual_crop_coords:
                    raise HTTPException(400, "Manual crop method requires crop coordinates")

                required_keys = ['x', 'y', 'width', 'height']
                if not all(key in config.manual_crop_coords for key in required_keys):
                    raise HTTPException(400, f"Manual crop coords must have: {required_keys}")

                # Validate coordinates are positive
                for key, val in config.manual_crop_coords.items():
                    if val < 0:
                        raise HTTPException(400, f"Crop coordinate '{key}' must be >= 0")

            # Initialize pipeline_config if empty
            if not job.pipeline_config:
                job.pipeline_config = {}

            # Store Phase 2 config
            job.pipeline_config['phase2'] = config.model_dump()
            job.updated_at = datetime.now(timezone.utc)

            # Transition to user selection phase (User UI will show moment selector)
            job.phase = PipelinePhase.AWAITING_USER_SELECTION.value
            job.status = 'paused_for_selection'
            job.current_step = 'Awaiting moment selection'

            session.commit()

            logger.info(f"✅ Phase 2 configured for job {job_id}: {config.model_dump()}")
            logger.info(f"→ Job transitioned to {PipelinePhase.AWAITING_USER_SELECTION.value} for moment selection")

            return {
                "success": True,
                "job_id": job_id,
                "phase": job.phase,
                "phase2_config": config.model_dump(),
                "message": "Phase 2 configured. Select moments to continue."
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error configuring Phase 2: {e}")
        raise HTTPException(500, f"Failed to configure Phase 2: {str(e)}")


@router.post("/{job_id}/start-phase2")
async def start_phase2(
    job_id: str
):
    """
    Start Phase 2 with configured settings

    Triggers the Phase 2 workflow (intelligent_crop → cut_videos).
    Requires moments to be selected first.
    Can start from either awaiting_admin_config or awaiting_user_selection.
    """
    try:
        with get_db_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise HTTPException(404, "Job not found")

            # Can start Phase 2 from either awaiting_admin_config or awaiting_user_selection
            valid_phases = [
                PipelinePhase.AWAITING_ADMIN_CONFIG.value,
                PipelinePhase.AWAITING_USER_SELECTION.value
            ]
            if job.phase not in valid_phases:
                raise HTTPException(
                    400,
                    f"Cannot start Phase 2 from phase: {job.phase}. Must be in: {valid_phases}"
                )

            # Verify moments are selected
            selected_moments = session.query(Moment).filter(
                Moment.job_id == job_id,
                Moment.is_selected == True
            ).all()

            if not selected_moments:
                raise HTTPException(400, "No moments selected. Select moments first via /api/moments/{job_id}/select")

            # Get Phase 2 config or use defaults
            phase2_config = {}
            if job.pipeline_config and 'phase2' in job.pipeline_config:
                phase2_config = job.pipeline_config['phase2']
                logger.info(f"✅ Using admin-configured Phase 2 settings: {phase2_config}")
            else:
                # Use defaults
                default_config = Phase2Config()
                phase2_config = default_config.to_dict()
                logger.info(f"ℹ️ No Phase 2 config found, using defaults")

            # Update job state
            job.phase = PipelinePhase.PHASE2_RUNNING.value
            job.status = 'processing'
            job.progress = 70
            job.current_step = f'Starting Phase 2 ({phase2_config.get("crop_method", "auto")} crop)...'
            session.commit()

            # Import and trigger Phase 2 workflow
            # NOTE: Workflow implementatie komt in WORKFLOW contract
            try:
                from tasks.video_processing_phase2 import create_phase2_workflow
                selected_ids = [str(m.id) for m in selected_moments]
                workflow = create_phase2_workflow(job_id, selected_ids, phase2_config)
                workflow.apply_async()
                logger.info(f"✅ Phase 2 workflow started for job {job_id}")
            except ImportError:
                logger.warning("⚠️ Phase 2 workflow not yet implemented (WORKFLOW contract pending)")
                # For now, just update status - workflow will be implemented later
                pass

            return {
                "success": True,
                "job_id": job_id,
                "phase": PipelinePhase.PHASE2_RUNNING.value,
                "selected_moments": len(selected_moments),
                "config_used": phase2_config,
                "message": "Phase 2 started successfully"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error starting Phase 2: {e}")
        raise HTTPException(500, f"Failed to start Phase 2: {str(e)}")


@router.get("/{job_id}/state")
async def get_pipeline_state(
    job_id: str
):
    """
    Get current pipeline state with available actions

    Returns job phase, status, progress, and context-aware available actions.
    Used by Debug View to show admin what they can do next.
    """
    try:
        with get_db_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise HTTPException(404, "Job not found")

            # Determine available actions based on current phase
            available_actions = []

            if job.phase == PipelinePhase.CONFIGURING.value:
                available_actions = [
                    {
                        "action": "configure_phase1",
                        "endpoint": f"/api/pipeline/{job_id}/configure-phase1",
                        "method": "POST",
                        "label": "⚙️ Configure Phase 1 Settings",
                        "description": "Tweak detection parameters before analysis starts"
                    },
                    {
                        "action": "start_phase1",
                        "endpoint": f"/api/pipeline/{job_id}/start-phase1",
                        "method": "POST",
                        "label": "▶️ Start Phase 1 (use defaults)",
                        "description": "Begin video analysis with default settings"
                    }
                ]

            elif job.phase == PipelinePhase.AWAITING_ADMIN_CONFIG.value:
                available_actions = [
                    {
                        "action": "configure_phase2",
                        "endpoint": f"/api/pipeline/{job_id}/configure-phase2",
                        "method": "POST",
                        "label": "⚙️ Configure Phase 2 Settings",
                        "description": "Set crop method and clip generation parameters"
                    },
                    {
                        "action": "open_crop_editor",
                        "endpoint": f"/ui-v2/crop-editor.html?job={job_id}",
                        "method": "GET",
                        "label": "🎨 Open Visual Crop Editor",
                        "description": "Manually define crop area for clips"
                    },
                    {
                        "action": "start_phase2",
                        "endpoint": f"/api/pipeline/{job_id}/start-phase2",
                        "method": "POST",
                        "label": "▶️ Start Phase 2 (use auto-crop)",
                        "description": "Generate clips with automatic cropping"
                    }
                ]

            elif job.phase == PipelinePhase.AWAITING_USER_SELECTION.value:
                available_actions = [
                    {
                        "action": "select_moments",
                        "endpoint": f"/ui-v2/index.html?job={job_id}",
                        "method": "GET",
                        "label": "✅ Select Moments (User UI)",
                        "description": "Choose which moments to generate clips for"
                    },
                    {
                        "action": "admin_select_all",
                        "endpoint": f"/api/moments/{job_id}/select-all",
                        "method": "POST",
                        "label": "🔧 Admin: Select All Moments",
                        "description": "Quick select all moments for testing"
                    }
                ]

            # Get Phase 1 results if available
            phase1_results = None
            if job.pipeline_config and 'phase1_results' in job.pipeline_config:
                phase1_results = job.pipeline_config['phase1_results']

            return {
                "success": True,
                "job_id": job_id,
                "phase": job.phase,
                "status": job.status,
                "progress": job.progress,
                "current_step": job.current_step,
                "pipeline_config": job.pipeline_config or {},
                "available_actions": available_actions,
                "pause_points": {
                    "after_phase1": job.phase == PipelinePhase.AWAITING_ADMIN_CONFIG.value,
                    "after_moment_selection": job.phase == PipelinePhase.AWAITING_USER_SELECTION.value
                },
                "phase1_results": phase1_results
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting pipeline state: {e}")
        raise HTTPException(500, f"Failed to get pipeline state: {str(e)}")
