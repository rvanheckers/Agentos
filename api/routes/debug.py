"""
Debug API Routes - Job Debug Viewer
====================================

Provides real-time debug information for video processing pipeline.
Exposes step-by-step outputs, visual data, and error context for debugging.

Priority 3 (DEBUG_VIEWER_V2.md): Re-run system for pipeline steps

Context7 Validated:
- FastAPI response_model pattern (trust score 9.9)
- Proper error handling with HTTPException
- Clear endpoint documentation
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from core.database_manager import PostgreSQLManager, Job
from api.services.auth_dependencies import get_current_user
from sqlalchemy import text

router = APIRouter(prefix="/api/jobs", tags=["debug"])


# Response Models
class StepOutput(BaseModel):
    """Individual processing step output"""
    status: str  # 'success', 'failed', 'in_progress', 'pending'
    timestamp: Optional[str] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "timestamp": "2025-10-16T05:00:00Z",
                "output": {
                    "video_path": "/io/videos/example.mp4",
                    "thumbnail": "/io/thumbnails/example_thumb.jpg",
                    "duration": 300.5,
                    "resolution": "1920x1080"
                }
            }
        }


class JobDebugResponse(BaseModel):
    """Complete debug information for a job"""
    job_id: str
    status: str
    phase: str
    progress: int
    current_step: Optional[str] = None
    steps: Dict[str, StepOutput]

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "processing",
                "phase": "phase1_analysis",
                "progress": 45,
                "current_step": "transcribe_audio",
                "steps": {
                    "download_video": {
                        "status": "success",
                        "timestamp": "2025-10-16T05:00:00Z",
                        "output": {"video_path": "/io/videos/example.mp4"}
                    }
                }
            }
        }


@router.get("/{job_id}/debug", response_model=JobDebugResponse)
async def get_job_debug_output(
    job_id: str
    # DEVELOPMENT: Auth disabled for testing
    # current_user = Depends(get_current_user)
):
    """
    Get step-by-step debug output for a job

    Returns visual debugging information for each pipeline step including:
    - Status (success/failed/pending/in_progress)
    - Timestamps
    - Output data (paths, thumbnails, metadata)
    - Error messages with context

    **Access**: DEVELOPMENT MODE - Auth disabled for testing

    **Use Case**:
    Frontend debug viewer polls this endpoint every 5 seconds to show
    real-time progress and visual feedback during video processing.
    """
    db = PostgreSQLManager()

    try:
        with db.get_session() as session:
            # Query job
            job = session.query(Job).filter(Job.id == job_id).first()

            if not job:
                raise HTTPException(status_code=404, detail="Job not found")

            # DEVELOPMENT: Skip auth check for testing
            # user_id = current_user.get("id")
            # is_admin = current_user.get("role") == "admin"
            #
            # if not is_admin and str(job.user_id) != str(user_id):
            #     raise HTTPException(
            #         status_code=403,
            #         detail="You don't have permission to view this job"
            #     )

            # Get step outputs (defaults to empty dict if None)
            step_outputs = job.step_outputs or {}

            # Convert to StepOutput models for validation
            steps_validated = {}
            for step_name, step_data in step_outputs.items():
                try:
                    steps_validated[step_name] = StepOutput(**step_data)
                except Exception as e:
                    # If step data is malformed, return raw data with error flag
                    steps_validated[step_name] = StepOutput(
                        status="error",
                        error=f"Malformed step data: {str(e)}",
                        output=step_data
                    )

            return JobDebugResponse(
                job_id=str(job.id),
                status=job.status,
                phase=job.phase or "unknown",
                progress=job.progress or 0,
                current_step=job.current_step,
                steps=steps_validated
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/{job_id}/debug/summary")
async def get_job_debug_summary(
    job_id: str
    # DEVELOPMENT: Auth disabled for testing
    # current_user = Depends(get_current_user)
):
    """
    Get quick summary of job debug status

    Returns lightweight summary for dashboard widgets showing:
    - Total steps
    - Completed steps
    - Failed steps
    - Current processing step

    **Access**: DEVELOPMENT MODE - Auth disabled for testing
    """
    db = PostgreSQLManager()

    try:
        with db.get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()

            if not job:
                raise HTTPException(status_code=404, detail="Job not found")

            # DEVELOPMENT: Skip auth check for testing
            # user_id = current_user.get("id")
            # is_admin = current_user.get("role") == "admin"
            #
            # if not is_admin and str(job.user_id) != str(user_id):
            #     raise HTTPException(status_code=403, detail="Access denied")

            step_outputs = job.step_outputs or {}

            # Calculate summary stats
            total_steps = len(step_outputs)
            completed = sum(1 for s in step_outputs.values() if s.get("status") == "success")
            failed = sum(1 for s in step_outputs.values() if s.get("status") == "failed")
            in_progress = sum(1 for s in step_outputs.values() if s.get("status") == "in_progress")

            return {
                "success": True,
                "data": {
                    "job_id": str(job.id),
                    "total_steps": total_steps,
                    "completed_steps": completed,
                    "failed_steps": failed,
                    "in_progress_steps": in_progress,
                    "current_step": job.current_step,
                    "overall_status": job.status,
                    "progress": job.progress
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PRIORITY 3: RE-RUN SYSTEM (DEBUG_VIEWER_V2.md)
# ============================================================================

class StepRerunRequest(BaseModel):
    """Request to re-run a specific processing step with new config"""
    step_name: str  # 'detect_moments' | 'detect_faces' | 'intelligent_crop' | 'cut_videos'
    config: Dict[str, Any]  # New configuration to apply

    class Config:
        json_schema_extra = {
            "example": {
                "step_name": "detect_moments",
                "config": {
                    "user_preferences": {
                        "target_len": 45,
                        "max_moments": 3,
                        "cluster_gap_s": 5.0
                    },
                    "constraints_override": {
                        "max_moments": 3,
                        "cluster_gap_s": 5.0
                    }
                }
            }
        }


class StepRerunResponse(BaseModel):
    """Response for step re-run request"""
    success: bool
    message: str
    rerun_steps: List[str]  # List of steps that will be re-run (including dependencies)
    estimated_time: int  # Estimated completion time in seconds

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Re-running detect_moments and dependent steps",
                "rerun_steps": ["detect_moments", "detect_faces", "intelligent_crop", "cut_videos"],
                "estimated_time": 120
            }
        }


@router.post("/{job_id}/rerun-step", response_model=StepRerunResponse)
async def rerun_processing_step(job_id: str, request: StepRerunRequest):
    """
    Re-run a specific processing step with new configuration

    **Priority 3 Feature**: Allows developers to re-run pipeline steps with
    custom settings without re-uploading/re-downloading videos.

    **Automatically re-runs dependent steps**:
    - Re-run detect_moments → triggers: detect_faces, intelligent_crop, cut_videos
    - Re-run detect_faces → triggers: intelligent_crop, cut_videos
    - Re-run intelligent_crop → triggers: cut_videos
    - Re-run cut_videos → no dependencies

    **Args**:
        job_id: Job UUID
        request: Step name + new configuration

    **Returns**:
        Success status + list of steps that will be re-run

    **Example Usage**:
    ```bash
    POST /api/jobs/{job_id}/rerun-step
    {
      "step_name": "detect_faces",
      "config": {
        "user_preferences": {
          "face_confidence": 0.7,
          "sample_interval": 1.5
        }
      }
    }
    ```
    """
    db = PostgreSQLManager()

    try:
        with db.get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()

            if not job:
                raise HTTPException(status_code=404, detail="Job not found")

            if job.status == 'processing':
                raise HTTPException(
                    status_code=409,
                    detail="Job is currently processing, cannot re-run. Wait for completion."
                )

            # Validate step name
            valid_steps = ['detect_moments', 'detect_faces', 'intelligent_crop', 'cut_videos']
            if request.step_name not in valid_steps:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid step name. Must be one of: {valid_steps}"
                )

            # Save new config to job_processing_config table (upsert)
            config_json = json.dumps(request.config)
            session.execute(
                text("""
                    INSERT INTO job_processing_config (job_id, config, updated_at)
                    VALUES (:job_id, CAST(:config AS jsonb), NOW())
                    ON CONFLICT (job_id)
                    DO UPDATE SET config = CAST(:config AS jsonb), updated_at = NOW()
                """),
                {"job_id": job_id, "config": config_json}
            )
            session.commit()

            # Determine dependent steps (what needs to re-run)
            step_dependencies = {
                'detect_moments': ['detect_moments', 'detect_faces', 'intelligent_crop', 'cut_videos'],
                'detect_faces': ['detect_faces', 'intelligent_crop', 'cut_videos'],
                'intelligent_crop': ['intelligent_crop', 'cut_videos'],
                'cut_videos': ['cut_videos']
            }

            rerun_steps = step_dependencies[request.step_name]

            # Update job status to processing
            job.status = 'processing'
            job.phase = f'rerun_{request.step_name}'
            job.progress = 0
            job.current_step = request.step_name
            session.commit()

            # Trigger Celery task to re-run steps
            from tasks.video_processing import rerun_processing_steps_task

            rerun_processing_steps_task.delay(
                job_id=str(job_id),
                start_step=request.step_name,
                config_override=request.config
            )

            return StepRerunResponse(
                success=True,
                message=f"Re-running {request.step_name} and dependent steps",
                rerun_steps=rerun_steps,
                estimated_time=len(rerun_steps) * 30  # Rough estimate: 30s per step
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start re-run: {str(e)}"
        )


@router.get("/{job_id}/config", response_model=Dict[str, Any])
async def get_job_config(job_id: str):
    """
    Get current per-job configuration overrides

    **Priority 3 Feature**: Returns the config stored in job_processing_config
    table for displaying current settings in debug viewer.

    **Returns**:
        JSONB config object or empty dict if no custom config exists

    **Example Response**:
    ```json
    {
      "user_preferences": {
        "target_len": 45,
        "crop_method": "face_based"
      },
      "constraints_override": {
        "max_moments": 8
      }
    }
    ```
    """
    db = PostgreSQLManager()

    try:
        with db.get_session() as session:
            # Check if job exists
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")

            # Get config from job_processing_config table
            result = session.execute(
                text("SELECT config FROM job_processing_config WHERE job_id = :job_id"),
                {"job_id": job_id}
            ).fetchone()

            if not result:
                # No custom config yet, return empty dict
                return {}

            # Return JSONB config
            return result[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job config: {str(e)}"
        )
