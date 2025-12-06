"""
Analytics API Routes - Refactored with Service Layer
===================================================
Uses AnalyticsService to eliminate duplicate logic between admin and user endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any
from services.analytics_service import AnalyticsService
import logging

logger = logging.getLogger("agentos.api.routes.analytics")

# Create service instance
analytics_service = AnalyticsService()

# Create separate routers for admin and user endpoints
admin_router = APIRouter(prefix="/api/admin", tags=["admin-analytics"])
user_router = APIRouter(prefix="/api", tags=["user-analytics"])

# === ADMIN ENDPOINTS ===

@admin_router.get("/analytics")
async def admin_get_analytics(timeframe: str = Query("7d", regex="^(24h|7d|30d)$")) -> Dict[str, Any]:
    """Get comprehensive analytics - Admin endpoint"""
    try:
        return analytics_service.get_analytics(timeframe=timeframe, is_admin=True)
    except Exception as e:
        logger.error(f"Failed to get admin analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@admin_router.get("/config")
async def admin_get_system_config() -> Dict[str, Any]:
    """Get system configuration - Admin only endpoint"""
    try:
        return analytics_service.get_system_config(is_admin=True)
    except Exception as e:
        logger.error(f"Failed to get system config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === USER ENDPOINTS ===


@user_router.get("/analytics")
async def user_get_analytics_v2(timeframe: str = Query("7d", regex="^(24h|7d|30d)$")) -> Dict[str, Any]:
    """Get basic analytics - User endpoint (v2 API)"""
    try:
        return analytics_service.get_analytics(timeframe=timeframe, is_admin=False)
    except Exception as e:
        logger.error(f"Failed to get user analytics v2: {e}")
        raise HTTPException(status_code=500, detail=str(e))
