"""
Download API Routes - Refactored with Service Layer
==================================================
Uses DownloadService to eliminate duplicate logic between admin and user endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from typing import Dict, Any, Optional
from api.services.download_service import DownloadService
import logging

logger = logging.getLogger("agentos.api.routes.download")

# Create service instance
download_service = DownloadService()

# Create separate routers for admin and user endpoints
admin_router = APIRouter(prefix="/api/admin/download", tags=["admin-download"])
user_router = APIRouter(prefix="/api/download", tags=["user-download"])

# === ADMIN ENDPOINTS ===

@admin_router.get("/clip/{job_id}/{clip_id}")
async def admin_download_clip(job_id: str, clip_id: str) -> FileResponse:
    """Download a specific clip file - Admin endpoint (can download any clip)"""
    try:
        return download_service.download_clip(job_id=job_id, clip_id=clip_id, is_admin=True)
    except Exception as e:
        logger.error(f"Admin clip download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/job/{job_id}")
async def admin_download_job_files(job_id: str) -> StreamingResponse:
    """Download all clips from a job as a zip file - Admin endpoint (can download any job)"""
    try:
        return download_service.download_job_files(job_id=job_id, is_admin=True)
    except Exception as e:
        logger.error(f"Admin job download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/stats")
async def admin_get_download_stats(job_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    """Get download statistics - Admin endpoint (full stats access)"""
    try:
        return download_service.get_download_stats(job_id=job_id, is_admin=True)
    except Exception as e:
        logger.error(f"Admin download stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# === USER ENDPOINTS ===

@user_router.get("/clip/{job_id}/{clip_id}")
async def user_download_clip(job_id: str, clip_id: str) -> FileResponse:
    """Download a specific clip file - User endpoint (own clips only)"""
    try:
        return download_service.download_clip(job_id=job_id, clip_id=clip_id, is_admin=False)
    except Exception as e:
        logger.error(f"User clip download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@user_router.get("/job/{job_id}")
async def user_download_job_files(job_id: str) -> StreamingResponse:
    """Download all clips from a job as a zip file - User endpoint (own jobs only)"""
    try:
        return download_service.download_job_files(job_id=job_id, is_admin=False)
    except Exception as e:
        logger.error(f"User job download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@user_router.get("/stats")
async def user_get_download_stats(job_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    """Get download statistics - User endpoint (limited stats access)"""
    try:
        return download_service.get_download_stats(job_id=job_id, is_admin=False)
    except Exception as e:
        logger.error(f"User download stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
