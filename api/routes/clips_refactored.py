"""
Clips routes - Service Layer Pattern
Provides endpoints for clip management and retrieval.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from api.services.database_service import DatabaseService
from core.logging_config import get_logger

logger = get_logger("api.routes.clips")

# Create routers
router = APIRouter()
admin_router = APIRouter(prefix="/api/admin", tags=["admin-clips"])
user_router = APIRouter(prefix="/api", tags=["clips"])

# Initialize database service
db_service = DatabaseService()

@user_router.get("/clips/recent")
async def get_recent_clips(limit: int = Query(10, ge=1, le=100)):
    """
    Get recent clips from the database
    UI-v2 compatibility endpoint for loading existing video clips
    """
    try:
        clips = db_service.get_recent_clips(limit)
        
        # Transform clips data to match frontend expectations
        formatted_clips = []
        for clip in clips:
            formatted_clips.append({
                "id": clip.get("id"),
                "path": clip.get("file_path", ""),
                "filename": f"clip_{clip.get('clip_number', 'unknown')}.mp4",
                "validation": {
                    "duration": clip.get("duration", 0)
                },
                "metadata": {
                    "job_id": clip.get("job_id"),
                    "clip_type": clip.get("clip_type", "viral"),
                    "platform": clip.get("platform", "general"),
                    "confidence": clip.get("confidence", 0.8),
                    "start_time": clip.get("start_time", 0),
                    "end_time": clip.get("end_time", 0)
                },
                "created_at": clip.get("created_at")
            })
        
        return {
            "status": "success",
            "clips": formatted_clips,
            "total": len(formatted_clips)
        }
        
    except Exception as e:
        logger.error(f"Failed to get recent clips: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve clips: {str(e)}")

# NOTE: Admin /clips/recent endpoint removed per cleanup plan
# Admin should use user endpoint: /api/clips/recent
# The service layer can handle admin privileges based on authentication

@user_router.get("/clips/{clip_id}")
async def get_clip_details(clip_id: str):
    """
    Get details for a specific clip
    """
    try:
        # Get clip from database via jobs service (which has access to clips)
        from api.services.jobs_service import JobsService
        jobs_service = JobsService(db_service.db_manager)
        
        # Find clip by iterating through recent clips
        clips = db_service.get_recent_clips(100)  # Get more clips to search
        clip = next((c for c in clips if c.get("id") == clip_id), None)
        
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")
        
        return {
            "status": "success",
            "clip": clip
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get clip details: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve clip: {str(e)}")

@admin_router.get("/clips/stats")
async def get_clips_statistics():
    """
    Get statistics about clips in the system
    """
    try:
        # Get stats from database
        stats = db_service.get_stats()
        
        # Get recent clips for additional analysis
        recent_clips = db_service.get_recent_clips(50)
        
        # Analyze clip types
        clip_types = {}
        platforms = {}
        total_duration = 0
        
        for clip in recent_clips:
            # Count clip types
            clip_type = clip.get("clip_type", "unknown")
            clip_types[clip_type] = clip_types.get(clip_type, 0) + 1
            
            # Count platforms
            platform = clip.get("platform", "unknown")
            platforms[platform] = platforms.get(platform, 0) + 1
            
            # Sum durations
            duration = clip.get("duration", 0)
            if isinstance(duration, (int, float)):
                total_duration += duration
        
        return {
            "status": "success",
            "stats": {
                "total_clips": stats.get("total_clips", 0),
                "clip_types": clip_types,
                "platforms": platforms,
                "total_duration_seconds": total_duration,
                "average_duration": total_duration / len(recent_clips) if recent_clips else 0,
                "recent_clips_analyzed": len(recent_clips)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get clips statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve statistics: {str(e)}")