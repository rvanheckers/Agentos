"""
Queue API Routes - Refactored with Service Layer
===============================================
Uses QueueService to eliminate duplicate logic between admin and user endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
from services.queue_service import QueueService
import logging

logger = logging.getLogger("agentos.api.routes.queue")

# Create service instance
queue_service = QueueService()

# Create separate routers for admin and user endpoints
admin_router = APIRouter(prefix="/api/admin", tags=["admin-queue"])
user_router = APIRouter(prefix="/api", tags=["user-queue"])

# === ADMIN ENDPOINTS ===
# NOTE: Admin queue status/details/stats endpoints removed per cleanup plan
# Admin should use user endpoints: /api/queue/status, /api/queue/details, /api/queue/stats
# The service layer already handles admin privileges based on authentication

@admin_router.post("/queue-purge")
async def admin_purge_queue(status: Optional[str] = None) -> Dict[str, Any]:
    """Purge job queue - Admin only endpoint"""
    try:
        return queue_service.purge_queue(status_filter=status, is_admin=True)
    except Exception as e:
        logger.error(f"Failed to purge queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === USER ENDPOINTS ===

@user_router.get("/queue/status")
async def user_get_queue_status() -> Dict[str, Any]:
    """Get queue status - User endpoint"""
    try:
        return queue_service.get_queue_status(is_admin=False)
    except Exception as e:
        logger.error(f"Failed to get user queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@user_router.get("/queue/details")
async def user_get_queue_details(limit: int = Query(10, ge=1, le=20)) -> Dict[str, Any]:
    """Get queue details - User endpoint (limited)"""
    try:
        return queue_service.get_queue_details(limit=limit, is_admin=False)
    except Exception as e:
        logger.error(f"Failed to get user queue details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@user_router.get("/queue/stats")
async def user_get_queue_stats() -> Dict[str, Any]:
    """Get queue statistics - User endpoint"""
    try:
        return queue_service.get_queue_stats(is_admin=False)
    except Exception as e:
        logger.error(f"Failed to get user queue stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))