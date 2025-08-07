"""
Clean Job routes - Admin duplicates removed 
Only user endpoints remain to eliminate duplicate chaos
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional, Dict, Any
from datetime import datetime

from services.jobs_service import JobsService
from api.services.auth_dependencies import get_current_user, get_admin_user

# Single router - user endpoints only (admin can use these too)
user_router = APIRouter(prefix="/api", tags=["jobs"])

# Service instance
jobs_service = JobsService()

# User Endpoints (filtered by user)
@user_router.get("/jobs/today")
async def user_get_today_jobs():
    """Get user's jobs created today - Temporarily allow anonymous access for frontend compatibility"""
    # TODO: Re-enable auth when frontend sends proper auth headers
    try:
        jobs = jobs_service.get_todays_jobs(user_id="user1", is_admin=False)
        
        # Calculate stats
        completed = len([job for job in jobs if job["status"] == "completed"])
        processing = len([job for job in jobs if job["status"] == "processing"])
        pending = len([job for job in jobs if job["status"] in ["pending", "queued"]])
        failed = len([job for job in jobs if job["status"] == "failed"])
        
        return {
            "completed": completed,
            "processing": processing,
            "pending": pending,
            "failed": failed,
            "total": len(jobs),
            "jobs": jobs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@user_router.get("/jobs/history")
async def user_get_job_history(
    current_user = Depends(get_current_user),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """Get user's job history with pagination"""
    try:
        return jobs_service.get_job_history(
            user_id=current_user["id"], 
            is_admin=False, 
            limit=limit, 
            offset=offset
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# DISABLED: Admin compatibility endpoints - USE SSOT INSTEAD
# Admin data is now served via /api/admin/ssot endpoint
# @user_router.get("/admin/jobs/history") - DISABLED FOR SSOT ARCHITECTURE


@user_router.get("/jobs/{job_id}")
async def user_get_job(job_id: str):
    """Get specific job details - Temporarily allow anonymous access for frontend compatibility"""
    # TODO: Re-enable auth when frontend sends proper auth headers
    job = jobs_service.get_job_by_id(job_id, is_admin=False)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@user_router.get("/jobs/{job_id}/status")
async def user_get_job_status(job_id: str):
    """Get job status - Temporarily allow anonymous access for frontend compatibility"""
    # TODO: Re-enable auth when frontend sends proper auth headers
    status = jobs_service.get_job_status(job_id, is_admin=False)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status


@user_router.get("/jobs/status/{status}")
async def user_get_jobs_by_status(status: str):
    """Get user's jobs with specific status"""
    # TODO: Re-enable auth when frontend sends proper auth headers
    return jobs_service.get_jobs_by_status(status, user_id="user1", is_admin=False)


@user_router.get("/jobs/{job_id}/clips")
async def user_get_job_clips(job_id: str):
    """Get clips for a job - Temporarily allow anonymous access for frontend compatibility"""
    # TODO: Re-enable auth when frontend sends proper auth headers
    return jobs_service.get_job_clips(job_id, is_admin=True)


@user_router.get("/jobs/summary/stats")
async def user_get_jobs_summary():
    """Get user's job summary statistics"""
    # TODO: Re-enable auth when frontend sends proper auth headers
    return jobs_service.get_jobs_summary(user_id="user1", is_admin=False)


@user_router.post("/jobs/{job_id}/cancel")
async def user_cancel_job(job_id: str, current_user = Depends(get_current_user)):
    """Cancel user's job"""
    if not jobs_service.cancel_job(job_id, user_id=current_user["id"], is_admin=False):
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")
    return {"message": "Job cancelled"}


@user_router.post("/jobs/{job_id}/retry")
async def user_retry_job(job_id: str, current_user = Depends(get_current_user)):
    """Retry user's failed job"""
    if not jobs_service.retry_job(job_id, user_id=current_user["id"], is_admin=False):
        raise HTTPException(status_code=400, detail="Job cannot be retried")
    return {"message": "Job queued for retry"}


@user_router.get("/jobs/recent/{limit}")
async def user_get_recent_jobs(limit: int):
    """Get user's recent jobs"""
    # TODO: Re-enable auth when frontend sends proper auth headers
    return jobs_service.get_recent_jobs(limit, user_id="user1", is_admin=False)


@user_router.post("/jobs/create")
async def user_create_job(job_data: Dict[str, Any]):
    """Create a new job - Temporarily allow anonymous access for frontend compatibility"""
    # TODO: Re-enable auth when frontend sends proper auth headers
    job_data["user_id"] = "user1"  # Default user for anonymous access
    
    # Validate video_url at API level (fail fast)
    video_url = job_data.get("video_url")
    if video_url is None or (isinstance(video_url, str) and not video_url.strip()):
        return {
            "success": False,
            "error": "❌ Geen video input opgegeven. Upload een bestand of voer een URL in.",
            "message": "Invalid video input"
        }
    
    try:
        job = jobs_service.create_job(job_data, is_admin=False)
        
        # Return consistent API response format
        return {
            "success": True,
            "job_id": job["id"],
            "status": job["status"],
            "message": f"Job {job['id']} created successfully",
            "data": job
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to create job"
        }