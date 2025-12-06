from fastapi import APIRouter, HTTPException
from typing import Optional
from core.database_manager import PostgreSQLManager, Job
from datetime import datetime
import json

router = APIRouter()
db_manager = PostgreSQLManager()

@router.get('/api/jobs/{job_id}/complete-metadata')
async def get_complete_metadata(job_id: str):
    """Single source of truth for all job metadata"""

    with db_manager.get_session() as session:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(404, 'Job not found')

        if job.is_deleted or (job.expires_at and job.expires_at < datetime.now()):
            raise HTTPException(410, 'Content has expired and been deleted for privacy')

        metadata = {
            'job': {
                'id': str(job.id),
                'status': job.status,
                'progress': job.progress,
                'created_at': job.created_at.isoformat(),
                'expires_at': job.expires_at.isoformat() if job.expires_at else None,
                'video_url': job.video_url
            },
            'content': {
                'type': job.content_type,
                'analysis_mode': job.analysis_mode,
                'viral_score': job.viral_score,
                'title': job.youtube_title,
                'total_moments': job.total_moments,
                'video_duration': float(job.video_duration) if job.video_duration else None
            },
            'privacy': {
                'expires_in_days': (job.expires_at - datetime.now()).days if job.expires_at else None,
                'storage_tier': job.storage_tier,
                'auto_delete': True
            },
            'keywords': job.keywords or [],
            'clips': [
                {
                    'id': str(clip.id),
                    'number': clip.clip_number,
                    'file_path': clip.file_path,
                    'duration': clip.duration,
                    'title': clip.title,
                    'description': clip.description,
                    'expires_with_job': True
                }
                for clip in job.clips
            ],
            'processing_steps': [
                {
                    'name': step.step_name,
                    'status': step.status,
                    'duration': step.duration_seconds
                }
                for step in job.processing_steps
            ]
        }

        return metadata