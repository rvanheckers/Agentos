from celery import Celery
from celery.schedules import crontab
from datetime import datetime, timedelta
from core.database_manager import PostgreSQLManager, Job, ContentInsights
from core.storage_manager import PrivacyCompliantStorage
from sqlalchemy import text
import logging
import hashlib
import sys
from pathlib import Path

# Add scripts directory for IO cleanup
sys.path.append(str(Path(__file__).parent.parent / "scripts"))
from io_cleanup import IOCleanup

logger = logging.getLogger(__name__)

celery_app = Celery('cleanup')
db_manager = PostgreSQLManager()
storage_manager = PrivacyCompliantStorage()

@celery_app.task
def cleanup_expired_content():
    """Daily cleanup of expired content (GDPR compliance)"""

    logger.info('Starting daily cleanup task')

    with db_manager.get_session() as session:
        expired_jobs = session.query(Job).filter(
            Job.expires_at < datetime.now(),
            Job.is_deleted == False
        ).all()

        logger.info(f'Found {len(expired_jobs)} expired jobs to clean up')

        for job in expired_jobs:
            try:
                # Extract marketing insights before deletion
                insights = storage_manager.extract_marketing_insights({
                    'video_url': job.video_url,
                    'content_type': job.content_type,
                    'viral_score': job.viral_score,
                    'keywords': job.keywords
                })

                # Save anonymous insights
                save_marketing_insights(session, insights)

                # Delete actual content
                storage_manager.delete_job_content(str(job.id))

                # Mark as deleted in database
                job.is_deleted = True
                job.video_url = f'DELETED_{job.id}'

                # Delete associated clips
                for clip in job.clips:
                    session.delete(clip)

                logger.info(f'Successfully cleaned up job {job.id}')

            except Exception as e:
                logger.error(f'Failed to cleanup job {job.id}: {e}')

        session.commit()

    logger.info('Daily cleanup task completed')
    return {'cleaned_jobs': len(expired_jobs)}

@celery_app.task
def cleanup_io_folders():
    """Cleanup IO folders - keep only 3 most recent job folders"""

    logger.info('🧹 Starting IO folders cleanup')

    try:
        # Run IO cleanup - keep max 3 jobs per folder
        cleaner = IOCleanup(max_jobs=3, dry_run=False)
        stats = cleaner.run()

        logger.info(f"✅ IO cleanup completed: {stats['folders_deleted']} folders deleted, "
                   f"{stats['space_freed_mb']:.2f} MB freed")

        return {
            'folders_scanned': stats['folders_scanned'],
            'folders_deleted': stats['folders_deleted'],
            'space_freed_mb': round(stats['space_freed_mb'], 2)
        }

    except Exception as e:
        logger.error(f"❌ IO cleanup failed: {e}")
        return {'error': str(e)}

def save_marketing_insights(session, insights: dict):
    """Save anonymous marketing data"""

    query = text("""
        INSERT INTO content_insights
        (content_fingerprint, content_category, viral_score,
         detected_trends, region, device_category, processed_date)
        VALUES
        (:fingerprint, :category, :score, :trends, :region, :device, :date)
        ON CONFLICT (content_fingerprint, processed_date) DO UPDATE
        SET viral_score = EXCLUDED.viral_score
    """)

    session.execute(query, {
        'fingerprint': insights['content_fingerprint'],
        'category': insights['content_category'],
        'score': insights['viral_score'],
        'trends': insights['detected_trends'],
        'region': insights['region'],
        'device': insights['device_category'],
        'date': insights['processed_date']
    })

# Schedule automatic cleanups
celery_app.conf.beat_schedule = {
    'daily-cleanup': {
        'task': 'tasks.cleanup_expired_content.cleanup_expired_content',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'io-folders-cleanup': {
        'task': 'tasks.cleanup_expired_content.cleanup_io_folders',
        'schedule': crontab(hour=3, minute=30),  # Daily at 3:30 AM (after main cleanup)
    }
}