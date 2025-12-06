"""
Clean Job routes - Admin duplicates removed
Only user endpoints remain to eliminate duplicate chaos
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Any
from pydantic import BaseModel, field_validator

from services.jobs_service import JobsService
from api.services.auth_dependencies import get_current_user

router = APIRouter(prefix="/api", tags=["jobs"])

# Service instance
jobs_service = JobsService()

# ---------- Helpers & Schemas ----------
class CreateJobIn(BaseModel):
    video_url: str
    video_title: str | None = None

    @field_validator("video_url")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("video_url is required")
        return v

def ok(data: Any, message: str = "ok"):
    return {"success": True, "message": message, "data": data}

def fail(message: str, status_code: int = 400):
    raise HTTPException(status_code=status_code, detail=message)

# User Endpoints (filtered by user)
@router.get("/jobs/today")
async def user_get_today_jobs(current_user = Depends(get_current_user)):
    """Get user's jobs created today"""
    try:
        uid = current_user["id"]
        jobs = jobs_service.get_todays_jobs(user_id=uid, is_admin=False)

        # Calculate stats
        completed = len([job for job in jobs if job["status"] == "completed"])
        processing = len([job for job in jobs if job["status"] == "processing"])
        pending = len([job for job in jobs if job["status"] in ["pending", "queued"]])
        failed = len([job for job in jobs if job["status"] == "failed"])

        return ok({
            "completed": completed,
            "processing": processing,
            "pending": pending,
            "failed": failed,
            "total": len(jobs),
            "jobs": jobs
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/history")
async def user_get_job_history(
    current_user = Depends(get_current_user),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get user's job history with pagination"""
    try:
        return ok(jobs_service.get_job_history(
            user_id=current_user["id"],
            is_admin=False,
            limit=limit,
            offset=offset
        ))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# DISABLED: Admin compatibility endpoints - USE SSOT INSTEAD
# Admin data is now served via /api/admin/ssot endpoint
# @user_router.get("/admin/jobs/history") - DISABLED FOR SSOT ARCHITECTURE


@router.get("/jobs/{job_id}")
async def user_get_job(job_id: str, current_user = Depends(get_current_user)):
    """Get specific job details"""
    job = jobs_service.get_job_by_id(job_id, user_id=current_user["id"], is_admin=False)
    if not job:
        fail("Job not found", 404)
    return ok(job)


@router.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str, current_user=Depends(get_current_user)):
    """Poll job status (used by frontend)"""
    status = jobs_service.get_job_status(job_id, user_id=current_user["id"], is_admin=False)
    if not status:
        fail("Job not found", 404)
    return ok(status)


@router.get("/jobs/status/{status}")
async def user_get_jobs_by_status(status: str, current_user = Depends(get_current_user)):
    """Get user's jobs with specific status"""
    data = jobs_service.get_jobs_by_status(status, user_id=current_user["id"], is_admin=False)
    return ok({"status": status, "jobs": data})


@router.get("/jobs/{job_id}/clips")
async def get_job_clips(job_id: str, current_user=Depends(get_current_user)):
    """Fetch clips + analysis (used by frontend)"""
    clips = jobs_service.get_job_clips(job_id, user_id=current_user["id"], is_admin=False)

    # Extract metadata from first clip that has it
    metadata = {}
    if clips and len(clips) > 0:
        for clip in clips:
            analysis = clip.get("analysis", {})
            if analysis.get("analysis_mode"):
                metadata = {
                    "analysis_mode": analysis.get("analysis_mode"),
                    "keywords": analysis.get("keywords", []),
                    "viral_score": analysis.get("viral_score"),
                    "total_moments": analysis.get("total_moments"),
                    "video_duration": analysis.get("video_duration"),
                    "totalDuration": analysis.get("totalDuration", analysis.get("video_duration", 0))
                }
                break

    # --- ALIGNMENT FIX: total_moments vs actual clips ---
    actual_clips_count = len(clips or [])
    reported_total_moments = metadata.get("total_moments")
    # Als moments bekend zijn maar niet matchen met clips, harmoniseer naar 'actual_clips_count'
    if isinstance(reported_total_moments, int) and reported_total_moments != actual_clips_count:
        metadata["total_moments"] = actual_clips_count
        # voorkom negatieve UI-effecten wanneer viral_score/keywords ontbreken
        metadata.setdefault("viral_score", 0)
        metadata.setdefault("keywords", [])

    # extra guard: als er geen metadata was maar we hebben wél clips,
    # vul basisvelden zodat de frontend geen nulls ziet
    if not metadata and actual_clips_count > 0:
        metadata = {
            "analysis_mode": "viral_ai",
            "keywords": [],
            "viral_score": 0,
            "total_moments": actual_clips_count,
            "video_duration": 0,
            "totalDuration": 0
        }

    response_payload = {
        "jobId": job_id,
        "clips": clips,
        "analysis": {
            "totalDuration": metadata.get("totalDuration", 0),
            "confidence": 0.95,
            "intent": "visual_clips"
        }
    }

    if metadata.get("analysis_mode"):
        response_payload["analysis_mode"] = metadata["analysis_mode"]
    if metadata.get("keywords"):
        response_payload["keywords"] = metadata["keywords"]
    if metadata.get("viral_score") is not None:
        response_payload["viral_score"] = metadata["viral_score"]
    if metadata.get("total_moments") is not None:
        response_payload["total_moments"] = metadata["total_moments"]
    if metadata.get("video_duration") is not None:
        response_payload["video_duration"] = metadata["video_duration"]

    return ok(response_payload)


@router.get("/jobs/summary/stats")
async def user_get_jobs_summary(current_user = Depends(get_current_user)):
    """Get user's job summary statistics"""
    return ok(jobs_service.get_jobs_summary(user_id=current_user["id"], is_admin=False))


@router.post("/jobs/{job_id}/cancel")
async def user_cancel_job(job_id: str, current_user = Depends(get_current_user)):
    """Cancel user's job"""
    res = jobs_service.cancel_job(job_id, user_id=current_user["id"], is_admin=False)
    if not res.get("success"):
        fail(res.get("message", "Job cannot be cancelled"), 400)
    return ok(res, "Job cancelled")


@router.post("/jobs/{job_id}/retry")
async def user_retry_job(job_id: str, current_user = Depends(get_current_user)):
    """Retry user's failed job"""
    res = jobs_service.retry_job(job_id, user_id=current_user["id"], is_admin=False)
    if not res.get("success"):
        fail(res.get("message", "Job cannot be retried"), 400)
    return ok(res, "Job queued for retry")


@router.get("/jobs/recent/{limit}")
async def user_get_recent_jobs(limit: int, current_user = Depends(get_current_user)):
    """Get user's recent jobs"""
    return ok(jobs_service.get_recent_jobs(limit, user_id=current_user["id"], is_admin=False))


@router.post("/jobs/create")
async def create_job(job_data: Dict[str, Any], current_user=Depends(get_current_user)):
    """Create job (used by frontend)"""
    job_data["user_id"] = current_user["id"]
    if not job_data.get("video_url") or not str(job_data["video_url"]).strip():
        return ok({"success": False, "error": "❌ Geen video input opgegeven. Upload een bestand of voer een URL in.", "message": "Invalid video input"})
    try:
        job = jobs_service.create_job(job_data, is_admin=False)
        return ok({"job_id": job["id"], "status": job["status"], **job}, "Job created")
    except Exception as e:
        return ok({"success": False, "error": str(e), "message": "Failed to create job"})
