from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import hashlib
from core.database_manager import PostgreSQLManager, Job
from core.storage_manager import PrivacyCompliantStorage

router = APIRouter()
db_manager = PostgreSQLManager()
storage_manager = PrivacyCompliantStorage()

@router.get('/api/privacy/status')
async def get_privacy_status() -> Dict[str, Any]:
    """Show users what data we store"""
    return {
        'data_retention': {
            'video_files': 'Deleted immediately after processing',
            'generated_clips': 'Deleted after 7 days',
            'metadata': 'Anonymized after 7 days',
            'marketing_insights': 'Anonymous aggregated data only',
            'user_data': 'No personal data stored'
        },
        'gdpr_compliant': True,
        'data_location': 'EU (Netherlands)',
        'third_party_sharing': False,
        'cookies': 'Session only (no tracking)',
        'contact': 'privacy@agentos.example'
    }

@router.post('/api/privacy/delete-my-data')
async def delete_user_data(session_id: str) -> Dict[str, str]:
    """Allow users to delete their data immediately"""

    session_hash = hashlib.sha256(session_id.encode()).hexdigest()

    with db_manager.get_session() as session:
        jobs = session.query(Job).filter(
            Job.session_hash == session_hash
        ).all()

        for job in jobs:
            storage_manager.delete_job_content(str(job.id))
            session.delete(job)

        session.commit()

    return {
        'status': 'success',
        'message': f'Deleted {len(jobs)} jobs and all associated content'
    }