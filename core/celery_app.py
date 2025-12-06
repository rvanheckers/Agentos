#!/usr/bin/env python3
"""
AgentOS Celery Application
=========================

Industry-standard distributed task queue voor video processing.
Compatible met Netflix/YouTube architectures.

FEATURES:
- Redis als message broker
- PostgreSQL voor result backend
- Auto-retry met exponential backoff
- Task routing naar verschillende queues
- Monitoring en health checks
- Production-ready configuratie

GEBRUIK:
    # Start Celery worker
    celery -A celery_app worker --loglevel=info --concurrency=4

    # Start Celery Beat (scheduler)
    celery -A celery_app beat --loglevel=info

    # Monitor tasks
    celery -A celery_app flower
"""

import os
import sys
from celery import Celery
from celery.schedules import crontab
from celery.signals import task_prerun, task_postrun, task_failure
from kombu import Queue

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# Load .env file for environment variables
def load_env_file():
    """Load environment variables from .env file"""
    env_path = os.path.join(project_root, '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Strip inline comments (e.g., "true  # comment" -> "true")
                    value = value.split('#')[0].strip()
                    os.environ[key.strip()] = value
        print(f"✅ Loaded environment variables from {env_path}")
    else:
        print(f"⚠️ No .env file found at {env_path}")

# Load environment variables before creating Celery app
load_env_file()

# Celery configuratie - AgentOS dedicated port (6380)
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6380/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6380/1')

# Create Celery app
celery_app = Celery('agentos')

# Celery configuratie
celery_app.conf.update(
    # Broker settings
    broker_url=CELERY_BROKER_URL,
    result_backend=CELERY_RESULT_BACKEND,

    # Task routing - verschillende queues voor verschillende taken
    # NB: gebruik specifieke routes zodat decorator 'queue=' en routes niet conflicteren
    task_routes={
        # video pipeline
        'tasks.video_processing.download_video':   {'queue': 'file_operations'},
        'tasks.video_processing.transcribe_audio': {'queue': 'transcription'},
        'tasks.video_processing.transcribe_audio_completed': {'queue': 'transcription'},
        'tasks.video_processing.detect_moments':   {'queue': 'ai_analysis'},
        'tasks.video_processing.detect_faces':     {'queue': 'ai_analysis'},
        'tasks.video_processing.intelligent_crop': {'queue': 'video_processing'},
        'tasks.video_processing.cut_videos':       {'queue': 'video_processing'},
        'tasks.video_processing.finalize_workflow': {'queue': 'video_processing'},
        'tasks.video_processing.cleanup_temp_files': {'queue': 'file_operations'},
        # NEW: Phase 1/2 workflow tasks
        'tasks.video_processing_phase1.save_moments_to_db': {'queue': 'video_processing'},
        'tasks.video_processing_phase2.load_selected_moments': {'queue': 'video_processing'},
        'tasks.video_processing_phase2.finalize_phase2': {'queue': 'video_processing'},
        # overige namespaces (maintenance/monitoring/cache)
        'tasks.maintenance.*': {'queue': 'file_operations'},
        'tasks.monitoring.*':  {'queue': 'celery'},
        'tasks.cache_warming.*': {'queue': 'celery'},
    },

    # Queue definities
    task_queues=(
        Queue('video_processing', routing_key='video_processing'),
        Queue('transcription', routing_key='transcription'),
        Queue('ai_analysis', routing_key='ai_analysis'),
        Queue('file_operations', routing_key='file_operations'),
        Queue('celery', routing_key='celery'),  # Default queue
    ),

    # Task execution settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,  # toon STARTED state (handig voor UI/progress)
    result_extended=True,     # meer metadata in AsyncResult

    # Retry policy - industry standard
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,

    # Task expiration
    task_soft_time_limit=300,  # 5 minuten soft limit
    task_time_limit=600,       # 10 minuten hard limit

    # Result expiration
    result_expires=3600,       # Results blijven 1 uur beschikbaar

    # Worker settings
    worker_max_tasks_per_child=1000,  # Restart worker na 1000 tasks
    worker_disable_rate_limits=False,

    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,

    # Beat schedule (voor periodieke taken) - INDUSTRY STANDARD CLEANUP
    beat_schedule={
        # 🗑️ DAILY CLEANUP (2 AM) - Industry standard retention policies
        'daily-cleanup-clips': {
            'task': 'tasks.maintenance.cleanup_old_clips',
            'schedule': crontab(hour=2, minute=0),  # 2 AM daily
            'options': {'queue': 'file_operations'}
        },

        # 📊 HOURLY DISK MONITORING - Proactive disk management
        'hourly-disk-monitor': {
            'task': 'tasks.maintenance.disk_usage_monitor',
            'schedule': crontab(minute=0),  # Every hour
            'options': {'queue': 'file_operations'}
        },

        # 🧹 LEGACY: Old results cleanup (keep for compatibility)
        'cleanup-old-results': {
            'task': 'tasks.maintenance.cleanup_old_results',
            'schedule': 3600.0,  # Elk uur
        },

        # 💓 HEALTH CHECK - System monitoring
        'health-check': {
            'task': 'tasks.maintenance.system_health_check',
            'schedule': 300.0,   # Elke 5 minuten
        },

        # 📈 PERFORMANCE METRICS - Daily reporting
        'daily-performance-report': {
            'task': 'tasks.maintenance.performance_metrics',
            'schedule': crontab(hour=1, minute=0),  # 1 AM daily
        },

        # 🎬 NETFLIX PATTERN: Worker self-reporting via Redis
        'worker-status-report': {
            'task': 'tasks.monitoring.report_worker_status',
            'schedule': 60.0,  # Every minute - Netflix-style real-time
            'options': {'queue': 'celery'}
        },

        # 🧹 NETFLIX PATTERN: Cleanup dead workers from Redis
        'cleanup-dead-workers': {
            'task': 'tasks.monitoring.cleanup_dead_workers',
            'schedule': 300.0,  # Every 5 minutes
            'options': {'queue': 'celery'}
        },

        # 🚀 V4 ARCHITECTURE: Cache warming for <50ms dashboard loads
        'warm-admin-cache': {
            'task': 'tasks.cache_warming.warm_admin_cache',
            'schedule': 5.0,  # Every 5 seconds - aggressive cache warming
            'options': {'queue': 'celery'}
        },

        # 🏥 V4 ARCHITECTURE: Cache health monitoring
        'cache-health-check': {
            'task': 'tasks.cache_warming.cache_health_check',
            'schedule': 60.0,  # Every minute - monitor cache performance
            'options': {'queue': 'celery'}
        },
    },
)

# Explicit task imports - ensure all tasks are registered
import tasks.video_processing
import tasks.video_processing_phase1  # NEW: Phase 1 workflow tasks
import tasks.video_processing_phase2  # NEW: Phase 2 workflow tasks
import tasks.maintenance
import tasks.monitoring
import tasks.cache_warming

# Celery signals voor logging en monitoring

@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Log task start"""
    print(f"🚀 Task {task.name} ({task_id}) starting...")

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """Log task completion"""
    print(f"✅ Task {task.name} ({task_id}) completed with state: {state}")

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """Log task failures"""
    print(f"❌ Task {sender.name} ({task_id}) failed: {exception}")

if __name__ == '__main__':
    celery_app.start()
