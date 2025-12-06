"""
Workflow API Routes - Refactored with Service Layer
==================================================
Uses WorkflowService to eliminate duplicate logic between admin and user endpoints
"""

from fastapi import APIRouter, HTTPException, Request, Query
from typing import Dict, Any, Optional
from api.services.workflow_service import WorkflowService
import logging

logger = logging.getLogger("agentos.api.routes.workflow")

# Create service instance
workflow_service = WorkflowService()

# Create separate routers for admin and user endpoints
admin_router = APIRouter(prefix="/api/admin/workflows", tags=["admin-workflows"])
user_router = APIRouter(prefix="/api/workflows", tags=["user-workflows"])

# === ADMIN ENDPOINTS ===

@admin_router.post("/youtube-to-tiktok")
async def admin_create_youtube_to_tiktok_workflow(request: Request) -> Dict[str, Any]:
    """Create YouTube to TikTok conversion workflow - Admin endpoint (enhanced features)"""
    try:
        data = await request.json()
        return workflow_service.create_youtube_to_tiktok_workflow(data, is_admin=True)
    except Exception as e:
        logger.error(f"Admin YouTube to TikTok workflow creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/youtube-to-tiktok/{workflow_id}")
async def admin_get_workflow_status(workflow_id: str) -> Dict[str, Any]:
    """Get YouTube to TikTok workflow status - Admin endpoint (full details)"""
    try:
        return workflow_service.get_workflow_status(workflow_id, is_admin=True)
    except Exception as e:
        logger.error(f"Admin workflow status retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.post("/batch")
async def admin_create_batch_workflow(request: Request) -> Dict[str, Any]:
    """Create batch processing workflow - Admin endpoint (unlimited batch size)"""
    try:
        data = await request.json()
        return workflow_service.create_batch_workflow(data, is_admin=True)
    except Exception as e:
        logger.error(f"Admin batch workflow creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@admin_router.get("/list")
async def admin_get_workflow_list(user_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    """Get list of all workflows - Admin endpoint (all workflows visible)"""
    try:
        return workflow_service.get_workflow_list(user_id=user_id, is_admin=True)
    except Exception as e:
        logger.error(f"Admin workflow list retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# === USER ENDPOINTS ===

@user_router.post("/youtube-to-tiktok")
async def user_create_youtube_to_tiktok_workflow(request: Request) -> Dict[str, Any]:
    """Create YouTube to TikTok conversion workflow - User endpoint (standard features)"""
    try:
        data = await request.json()
        return workflow_service.create_youtube_to_tiktok_workflow(data, is_admin=False)
    except Exception as e:
        logger.error(f"User YouTube to TikTok workflow creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@user_router.get("/youtube-to-tiktok/{workflow_id}")
async def user_get_workflow_status(workflow_id: str) -> Dict[str, Any]:
    """Get YouTube to TikTok workflow status - User endpoint (basic details)"""
    try:
        return workflow_service.get_workflow_status(workflow_id, is_admin=False)
    except Exception as e:
        logger.error(f"User workflow status retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@user_router.post("/batch")
async def user_create_batch_workflow(request: Request) -> Dict[str, Any]:
    """Create batch processing workflow - User endpoint (limited batch size)"""
    try:
        data = await request.json()
        return workflow_service.create_batch_workflow(data, is_admin=False)
    except Exception as e:
        logger.error(f"User batch workflow creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@user_router.get("/list")
async def user_get_workflow_list() -> Dict[str, Any]:
    """Get list of user's workflows - User endpoint (own workflows only)"""
    try:
        return workflow_service.get_workflow_list(user_id="anonymous", is_admin=False)
    except Exception as e:
        logger.error(f"User workflow list retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
