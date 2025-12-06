#!/usr/bin/env python3
"""
Celery Maintenance Tasks
=======================

Periodieke maintenance taken voor system health.

FEATURES:
- Database cleanup
- Log rotation
- Health monitoring
- Performance metrics
- Error alerting
"""

import os
import sys
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import text

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.celery_app import celery_app
from core.database_pool import get_db_session

logger = logging.getLogger(__name__)

@celery_app.task(name='tasks.maintenance.cleanup_old_results')
def cleanup_old_results():
    """Cleanup oude Celery results en completed jobs ouder dan 24 uur"""
    try:
        # Using shared database pool

        # Cleanup jobs ouder dan 7 dagen
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)

        with get_db_session() as session:
            # Count jobs to be cleaned
            old_jobs_count = session.execute(
                text("SELECT COUNT(*) FROM jobs WHERE completed_at < :cutoff_date AND status IN ('completed', 'failed')"),
                {"cutoff_date": cutoff_date}
            ).fetchone()[0]

            # Delete old completed/failed jobs
            session.execute(
                text("DELETE FROM jobs WHERE completed_at < :cutoff_date AND status IN ('completed', 'failed')"),
                {"cutoff_date": cutoff_date}
            )

            logger.info(f"🧹 Cleaned up {old_jobs_count} old jobs")

        return {'cleaned_jobs': old_jobs_count}

    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        raise

@celery_app.task(name='tasks.maintenance.system_health_check')
def system_health_check():
    """System health check - monitors database, queue, workers"""
    try:
        health_status = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'database': 'unknown',
            'redis': 'unknown',
            'workers': 'unknown'
        }

        # Check database
        try:
            # Using shared database pool
            with get_db_session() as session:
                session.execute(text("SELECT 1")).fetchone()
                health_status['database'] = 'healthy'
        except Exception as e:
            health_status['database'] = f'error: {e}'

        # Check Redis
        try:
            import redis
            r = redis.Redis(host='localhost', port=6379, decode_responses=True)
            r.ping()
            health_status['redis'] = 'healthy'
        except Exception as e:
            health_status['redis'] = f'error: {e}'

        # Check active workers
        try:
            from core.celery_app import celery_app
            inspect = celery_app.control.inspect()
            active_workers = inspect.active()
            health_status['workers'] = f"{len(active_workers or {})} active"
        except Exception as e:
            health_status['workers'] = f'error: {e}'

        logger.info(f"💓 System health check: {health_status}")
        return health_status

    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        raise

@celery_app.task(name='tasks.maintenance.cleanup_old_clips')
def cleanup_old_clips():
    """🗑️ INDUSTRY STANDARD: Daily cleanup of old video clips and jobs"""
    try:
        import shutil

        # Using shared database pool
        cleanup_stats = {
            'clips_removed': 0,
            'files_removed': 0,
            'jobs_cleaned': 0,
            'bytes_freed': 0,
            'errors': []
        }

        # Configuration - industry standard retention policies
        CLIP_RETENTION_DAYS = 30  # Keep clips for 30 days
        JOB_RETENTION_DAYS = 90   # Keep job records for 90 days
        TEMP_RETENTION_HOURS = 24 # Clean temp files after 24 hours

        cutoff_clips = datetime.now(timezone.utc) - timedelta(days=CLIP_RETENTION_DAYS)
        cutoff_jobs = datetime.now(timezone.utc) - timedelta(days=JOB_RETENTION_DAYS)
        cutoff_temp = datetime.now(timezone.utc) - timedelta(hours=TEMP_RETENTION_HOURS)

        with get_db_session() as session:
            # 1. Clean old clips from database and filesystem
            old_clips = session.execute(
                text("SELECT id, file_path FROM clips WHERE created_at < :cutoff_clips"),
                {"cutoff_clips": cutoff_clips}
            ).fetchall()

            for clip in old_clips:
                clip_id, file_path = clip

                # Remove file from filesystem
                if file_path and os.path.exists(file_path):
                    try:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        cleanup_stats['files_removed'] += 1
                        cleanup_stats['bytes_freed'] += file_size
                        logger.info(f"🗑️ Removed clip file: {file_path}")
                    except Exception as e:
                        cleanup_stats['errors'].append(f"File removal failed {file_path}: {e}")

                # Remove from database
                try:
                    session.execute(text("DELETE FROM clips WHERE id = :clip_id"), {"clip_id": clip_id})
                    cleanup_stats['clips_removed'] += 1
                except Exception as e:
                    cleanup_stats['errors'].append(f"DB clip removal failed {clip_id}: {e}")

            # 2. Clean old job directories
            output_dir = './io/output'
            if os.path.exists(output_dir):
                for item in os.listdir(output_dir):
                    item_path = os.path.join(output_dir, item)
                    if os.path.isdir(item_path):
                        # Check if directory is older than retention period
                        dir_mtime = datetime.fromtimestamp(os.path.getmtime(item_path), tz=timezone.utc)
                        if dir_mtime < cutoff_clips:
                            try:
                                shutil.rmtree(item_path)
                                logger.info(f"🗑️ Removed old job directory: {item_path}")
                            except Exception as e:
                                cleanup_stats['errors'].append(f"Directory removal failed {item_path}: {e}")

            # 3. Clean old completed/failed jobs from database
            old_jobs_count = session.execute(
                text("SELECT COUNT(*) FROM jobs WHERE completed_at < :cutoff_jobs AND status IN ('completed', 'failed')"),
                {"cutoff_jobs": cutoff_jobs}
            ).fetchone()[0]

            if old_jobs_count > 0:
                session.execute(
                    text("DELETE FROM jobs WHERE completed_at < :cutoff_jobs AND status IN ('completed', 'failed')"),
                    {"cutoff_jobs": cutoff_jobs}
                )
                cleanup_stats['jobs_cleaned'] = old_jobs_count

            # 4. Clean temp files
            temp_dirs = ['./io/temp', './io/downloads']
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    for item in os.listdir(temp_dir):
                        item_path = os.path.join(temp_dir, item)
                        item_mtime = datetime.fromtimestamp(os.path.getmtime(item_path), tz=timezone.utc)
                        if item_mtime < cutoff_temp:
                            try:
                                if os.path.isfile(item_path):
                                    file_size = os.path.getsize(item_path)
                                    os.remove(item_path)
                                    cleanup_stats['bytes_freed'] += file_size
                                elif os.path.isdir(item_path):
                                    shutil.rmtree(item_path)
                                logger.info(f"🗑️ Removed temp item: {item_path}")
                            except Exception as e:
                                cleanup_stats['errors'].append(f"Temp cleanup failed {item_path}: {e}")

        # Convert bytes to MB for logging
        mb_freed = cleanup_stats['bytes_freed'] / (1024 * 1024)

        logger.info(f"🧹 CLEANUP COMPLETE: {cleanup_stats['clips_removed']} clips, "
                   f"{cleanup_stats['files_removed']} files, {cleanup_stats['jobs_cleaned']} jobs, "
                   f"{mb_freed:.1f}MB freed")

        if cleanup_stats['errors']:
            logger.warning(f"⚠️ Cleanup errors: {len(cleanup_stats['errors'])} errors occurred")
            for error in cleanup_stats['errors'][:5]:  # Log first 5 errors
                logger.warning(f"   - {error}")

        return cleanup_stats

    except Exception as e:
        logger.error(f"❌ Cleanup task failed: {e}")
        raise

@celery_app.task(name='tasks.maintenance.disk_usage_monitor')
def disk_usage_monitor():
    """🔍 Monitor disk usage and trigger emergency cleanup if needed"""
    try:

        # Using shared database pool
        # Check disk usage for key directories
        directories_to_check = {
            'output': './io/output',
            'input': './io/input',
            'temp': './io/temp',
            'downloads': './io/downloads'
        }

        usage_stats = {}
        total_usage_mb = 0

        for name, path in directories_to_check.items():
            if os.path.exists(path):
                # Get directory size
                total_size = 0
                file_count = 0

                for dirpath, dirnames, filenames in os.walk(path):
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        try:
                            total_size += os.path.getsize(filepath)
                            file_count += 1
                        except (OSError, IOError):
                            pass  # Skip files we can't read

                size_mb = total_size / (1024 * 1024)
                usage_stats[name] = {
                    'size_mb': round(size_mb, 2),
                    'file_count': file_count,
                    'path': path
                }
                total_usage_mb += size_mb

        # Emergency cleanup if usage exceeds threshold
        EMERGENCY_THRESHOLD_MB = 5000  # 5GB threshold

        if total_usage_mb > EMERGENCY_THRESHOLD_MB:
            logger.warning(f"⚠️ EMERGENCY: Disk usage {total_usage_mb:.1f}MB exceeds {EMERGENCY_THRESHOLD_MB}MB threshold")

            # Trigger immediate cleanup
            cleanup_result = cleanup_old_clips.delay()
            logger.info(f"🚨 Emergency cleanup triggered: task {cleanup_result.id}")

            usage_stats['emergency_cleanup'] = {
                'triggered': True,
                'task_id': cleanup_result.id,
                'threshold_mb': EMERGENCY_THRESHOLD_MB
            }

        usage_stats['total_usage_mb'] = round(total_usage_mb, 2)
        usage_stats['timestamp'] = datetime.now(timezone.utc).isoformat()

        logger.info(f"💾 Disk usage: {total_usage_mb:.1f}MB across {sum(s['file_count'] for s in usage_stats.values() if isinstance(s, dict) and 'file_count' in s)} files")

        return usage_stats

    except Exception as e:
        logger.error(f"❌ Disk usage monitor failed: {e}")
        raise

@celery_app.task(name='tasks.maintenance.performance_metrics')
def performance_metrics():
    """Collect performance metrics voor monitoring"""
    try:
        # Using shared database pool
        metrics = {}

        with get_db_session() as session:
            # Job completion rates (last 24h)
            yesterday = datetime.now(timezone.utc) - timedelta(days=1)

            total_jobs = session.execute(
                text("SELECT COUNT(*) FROM jobs WHERE created_at > :yesterday"),
                {"yesterday": yesterday}
            ).fetchone()[0]

            completed_jobs = session.execute(
                text("SELECT COUNT(*) FROM jobs WHERE created_at > :yesterday AND status = 'completed'"),
                {"yesterday": yesterday}
            ).fetchone()[0]

            failed_jobs = session.execute(
                text("SELECT COUNT(*) FROM jobs WHERE created_at > :yesterday AND status = 'failed'"),
                {"yesterday": yesterday}
            ).fetchone()[0]

            # Average processing time
            avg_time = session.execute(
                text("""SELECT AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))
                   FROM jobs
                   WHERE status = 'completed' AND started_at > :yesterday"""),
                {"yesterday": yesterday}
            ).fetchone()[0]

            metrics = {
                'period': '24h',
                'total_jobs': total_jobs,
                'completed_jobs': completed_jobs,
                'failed_jobs': failed_jobs,
                'success_rate': (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0,
                'avg_processing_time_seconds': float(avg_time or 0),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        logger.info(f"📊 Performance metrics: {metrics}")
        return metrics

    except Exception as e:
        logger.error(f"❌ Performance metrics failed: {e}")
        raise
