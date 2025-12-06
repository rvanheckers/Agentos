"""
API endpoints voor moment selection workflow
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
import logging
from core.database_manager import PostgreSQLManager, Job, Moment, Clip
from api.services.auth_dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["moments"])

# Request/Response models
class MomentResponse(BaseModel):
    id: str
    moment_index: int
    start_time: float
    end_time: float
    duration: float
    description: Optional[str]
    sentence_text: Optional[str]
    keywords: Optional[List[str]]
    viral_score: Optional[int]
    is_selected: bool
    created_at: datetime
    # AI Transparency (DEBUG_VIEWER_V2)
    reasoning: Optional[str] = None
    engagement_drivers: Optional[List[str]] = None

    class Config:
        from_attributes = True

class MomentsListResponse(BaseModel):
    job_id: str
    job_status: str
    phase: str
    total_moments: int
    moments: List[MomentResponse]

class GenerateClipsRequest(BaseModel):
    selected_moments: List[int]  # List of moment_index values (e.g., [0, 2, 4])

class GenerateClipsResponse(BaseModel):
    job_id: str
    selected_count: int
    message: str
    phase: str

# GET /api/jobs/{job_id}/moments
@router.get("/{job_id}/moments", response_model=MomentsListResponse)
async def get_moments(job_id: str, current_user=Depends(get_current_user)):
    """
    Get all detected moments for a job.

    Returns moments list when job is in 'awaiting_selection' phase.
    """
    db = PostgreSQLManager()

    with db.get_session() as session:
        # Get job
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Verify user owns this job (unless admin)
        if not current_user.get("is_admin") and str(job.user_id) != str(current_user["id"]):
            raise HTTPException(status_code=403, detail="Not authorized to access this job")

        # Check phase (accept both old and new phase names)
        if job.phase not in ['awaiting_selection', 'awaiting_user_selection', 'phase2_generation', 'completed']:
            raise HTTPException(
                status_code=400,
                detail=f"Job is in phase '{job.phase}'. Moments available only after phase1_analysis."
            )

        # Get moments
        moments = session.query(Moment).filter(
            Moment.job_id == job_id
        ).order_by(Moment.moment_index).all()

        if not moments:
            raise HTTPException(
                status_code=404,
                detail="No moments found for this job. Phase 1 may not be complete."
            )

        return MomentsListResponse(
            job_id=str(job.id),
            job_status=job.status,
            phase=job.phase,
            total_moments=len(moments),
            moments=[
                MomentResponse(
                    id=str(m.id),
                    moment_index=m.moment_index,
                    start_time=m.start_time,
                    end_time=m.end_time,
                    duration=m.duration,
                    description=m.description,
                    sentence_text=m.sentence_text,
                    keywords=m.keywords if isinstance(m.keywords, list) else [],
                    viral_score=m.viral_score,
                    is_selected=m.is_selected,
                    created_at=m.created_at,
                    # AI Transparency (DEBUG_VIEWER_V2)
                    reasoning=m.reasoning,
                    engagement_drivers=m.engagement_drivers if isinstance(m.engagement_drivers, list) else []
                )
                for m in moments
            ]
        )

# POST /api/jobs/{job_id}/generate-clips
@router.post("/{job_id}/generate-clips", response_model=GenerateClipsResponse)
async def generate_clips(job_id: str, request: GenerateClipsRequest, current_user=Depends(get_current_user)):
    """
    Generate clips for selected moments.

    Triggers Phase 2 workflow with only the selected moments.
    """
    db = PostgreSQLManager()

    with db.get_session() as session:
        # Get job
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Verify user owns this job (unless admin)
        if not current_user.get("is_admin") and str(job.user_id) != str(current_user["id"]):
            raise HTTPException(status_code=403, detail="Not authorized to access this job")

        # Validate phase (accept both old and new phase names)
        if job.phase not in ['awaiting_selection', 'awaiting_user_selection']:
            raise HTTPException(
                status_code=400,
                detail=f"Job phase is '{job.phase}'. Expected 'awaiting_selection' or 'awaiting_user_selection'."
            )

        # Validate selection
        if not request.selected_moments:
            raise HTTPException(
                status_code=400,
                detail="No moments selected. Please select at least one moment."
            )

        # Get moments and validate selection
        all_moments = session.query(Moment).filter(Moment.job_id == job_id).all()
        valid_indices = [m.moment_index for m in all_moments]

        invalid = [idx for idx in request.selected_moments if idx not in valid_indices]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid moment indices: {invalid}. Valid: {valid_indices}"
            )

        # Mark selected moments
        for moment in all_moments:
            if moment.moment_index in request.selected_moments:
                moment.is_selected = True
                moment.selected_at = datetime.now(timezone.utc)
            else:
                moment.is_selected = False

        # Update job phase
        job.phase = 'phase2_generation'
        job.status = 'processing'
        job.progress = 50  # Phase 1 done, Phase 2 starting

        session.commit()

        # Trigger Phase 2 workflow
        selected_moment_ids = [
            str(m.id) for m in all_moments
            if m.moment_index in request.selected_moments
        ]

        # Trigger Phase 2 workflow
        from tasks.video_processing_phase2 import create_phase2_workflow
        workflow = create_phase2_workflow(str(job_id), selected_moment_ids)
        workflow.apply_async()

        logger.info(f"[{job_id}] Phase 2 workflow triggered for {len(selected_moment_ids)} moments")

        return GenerateClipsResponse(
            job_id=str(job.id),
            selected_count=len(request.selected_moments),
            message=f"Generating {len(request.selected_moments)} clips from selected moments",
            phase=job.phase
        )
