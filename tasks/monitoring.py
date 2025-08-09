#!/usr/bin/env python3
"""
Netflix-Pattern Worker Monitoring Tasks
======================================

Self-reporting worker tasks die status naar Redis schrijven voor
snelle dashboard data access (5ms i.p.v. 6000ms Celery inspection).

NETFLIX PATTERN:
- Workers rapporteren ZELF hun status
- Redis als fast lookup layer
- Real-time scaling visibility
- No expensive Celery inspection needed
"""

import os
import sys
import json
import redis
import socket
import psutil
from datetime import datetime, timezone
from celery import current_app
from celery.utils.log import get_task_logger

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from core.celery_app import celery_app

logger = get_task_logger(__name__)

@celery_app.task(bind=True)
def report_worker_status(self):
    """
    Netflix-pattern worker self-reporting

    Every worker reports its own status to Redis every minute
    This allows dashboard to get worker data in 5ms instead of 6000ms
    """
    try:
        # Get Redis connection (same as Celery broker)
        redis_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url)

        # Get current worker info
        worker_name = self.request.hostname or socket.gethostname()
        worker_id = f"celery@{worker_name}"

        # Get active tasks from current worker
        inspect = current_app.control.inspect([worker_id])
        active_tasks = inspect.active() or {}
        current_task_count = len(active_tasks.get(worker_id, []))

        # Get system stats (lightweight version)
        try:
            cpu_percent = psutil.cpu_percent(interval=None)
            memory_info = psutil.virtual_memory()
            memory_usage_mb = round(memory_info.used / (1024 * 1024), 1)
        except:
            cpu_percent = 0.0
            memory_usage_mb = 0.0

        # Worker status data (Netflix-style minimal but complete)
        worker_data = {
            "worker_id": worker_id,
            "hostname": worker_name,
            "status": "active",
            "current_tasks": current_task_count,
            "total_tasks_completed": 0,  # TODO: Get from worker stats if needed
            "load_average": round(cpu_percent, 2),
            "memory_usage": memory_usage_mb,
            "pool_size": os.getenv('CELERY_WORKER_CONCURRENCY', 4),
            "last_heartbeat": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "queues": ["video_processing", "transcription", "ai_analysis", "file_operations"],
            "uptime_seconds": 0,  # TODO: Calculate worker uptime
            "pid": os.getpid(),
            "version": "1.0.0"
        }

        # Store in Redis with TTL (expires after 2 minutes if worker dies)
        redis_key = f"worker_status:{worker_id}"
        r.setex(redis_key, 120, json.dumps(worker_data))  # 2 minute TTL

        # Also update global worker list
        r.sadd("active_workers", worker_id)
        r.expire("active_workers", 120)  # Expire set after 2 minutes

        logger.info(f"✅ Worker {worker_id} reported status to Redis")

        return {
            "success": True,
            "worker_id": worker_id,
            "current_tasks": current_task_count,
            "timestamp": worker_data["last_heartbeat"]
        }

    except Exception as e:
        logger.error(f"❌ Worker status reporting failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "worker_id": getattr(self.request, 'hostname', 'unknown')
        }

@celery_app.task
def cleanup_dead_workers():
    """
    Cleanup dead workers from Redis
    Runs every 5 minutes to remove stale worker data
    """
    try:
        redis_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url)

        # Get all worker status keys
        worker_keys = r.keys("worker_status:*")

        cleaned_count = 0
        for key in worker_keys:
            # Check if key is expired (TTL based cleanup)
            ttl = r.ttl(key)
            if ttl == -2:  # Key doesn't exist
                cleaned_count += 1
            elif ttl == -1:  # Key has no expiration (shouldn't happen)
                r.delete(key)
                cleaned_count += 1

        logger.info(f"🧹 Cleaned {cleaned_count} dead worker records")

        return {
            "success": True,
            "cleaned_workers": cleaned_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Worker cleanup failed: {e}")
        return {"success": False, "error": str(e)}

@celery_app.task
def get_worker_statistics():
    """
    Get aggregated worker statistics from Redis
    Used for monitoring and alerting
    """
    try:
        redis_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url)

        # Get all active workers
        worker_keys = r.keys("worker_status:*")

        total_workers = len(worker_keys)
        total_active_tasks = 0
        total_memory_usage = 0.0
        avg_load = 0.0

        workers_data = []

        for key in worker_keys:
            try:
                worker_json = r.get(key)
                if worker_json:
                    worker_data = json.loads(worker_json)
                    workers_data.append(worker_data)

                    total_active_tasks += worker_data.get('current_tasks', 0)
                    total_memory_usage += worker_data.get('memory_usage', 0)
                    avg_load += worker_data.get('load_average', 0)
            except json.JSONDecodeError:
                continue

        # Calculate averages
        if total_workers > 0:
            avg_load = avg_load / total_workers
            avg_memory = total_memory_usage / total_workers
        else:
            avg_memory = 0

        statistics = {
            "total_workers": total_workers,
            "active_workers": total_workers,  # All in Redis are active
            "total_active_tasks": total_active_tasks,
            "avg_load_percentage": round(avg_load, 2),
            "avg_memory_mb": round(avg_memory, 1),
            "total_memory_mb": round(total_memory_usage, 1),
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "workers_detail": workers_data
        }

        return {
            "success": True,
            "statistics": statistics
        }

    except Exception as e:
        logger.error(f"❌ Worker statistics failed: {e}")
        return {"success": False, "error": str(e)}

# Health check task to verify monitoring system
@celery_app.task
def monitoring_health_check():
    """
    Health check for the monitoring system itself
    Verifies Redis connectivity and data freshness
    """
    try:
        redis_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url)

        # Test Redis connectivity
        r.ping()

        # Check for recent worker data
        worker_keys = r.keys("worker_status:*")
        fresh_workers = 0

        now = datetime.now(timezone.utc)

        for key in worker_keys:
            try:
                worker_json = r.get(key)
                if worker_json:
                    worker_data = json.loads(worker_json)
                    last_heartbeat = datetime.fromisoformat(
                        worker_data['last_heartbeat'].replace('Z', '+00:00')
                    )

                    # Consider fresh if updated within last 2 minutes
                    if (now - last_heartbeat).total_seconds() < 120:
                        fresh_workers += 1
            except:
                continue

        return {
            "success": True,
            "redis_healthy": True,
            "total_worker_records": len(worker_keys),
            "fresh_worker_records": fresh_workers,
            "monitoring_system": "healthy",
            "timestamp": now.isoformat().replace("+00:00", "Z")
        }

    except Exception as e:
        logger.error(f"❌ Monitoring health check failed: {e}")
        return {
            "success": False,
            "redis_healthy": False,
            "error": str(e),
            "monitoring_system": "unhealthy"
        }
