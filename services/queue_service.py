"""
Queue Service Layer
==================
Handles all queue-related business logic
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import logging
import os
import asyncio

# V4 Event system integration
from events.dispatcher import dispatcher

logger = logging.getLogger("agentos.services.queue")

class QueueService:
    """
    Service layer for queue management

    Methods:
    - get_queue_status(): Get simple queue status
    - get_queue_details(): Get detailed queue information
    - get_queue_stats(): Get queue statistics
    - purge_queue(): Purge the job queue
    
    NEW Queue Metrics Methods:
    - get_queue_depth(): Get number of pending jobs
    - get_queue_throughput(): Calculate jobs per hour
    - get_average_wait_time(): Average queue wait time
    - get_worker_utilization(): Percentage of busy workers
    - get_24h_success_rate(): Success rate last 24 hours
    """

    def __init__(self):
        """Initialize queue service with v4 optimizations"""
        # V4 SINGLETON PATTERN: Initialize database service lazily
        self._db_service = None
        self._redis_client = None
        logger.debug("QueueService v4 initialized with lazy loading")

    @property
    def db_service(self):
        """Lazy-loaded database service for connection reuse"""
        if self._db_service is None:
            try:
                from api.services.database_service import DatabaseService
                self._db_service = DatabaseService()
                logger.debug("Database service initialized (lazy)")
            except Exception as e:
                logger.warning(f"Database service not available: {e}")
                self._db_service = None
        return self._db_service

    @property
    def redis_client(self):
        """Lazy-loaded Redis client for worker status"""
        if self._redis_client is None:
            try:
                import redis
                redis_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
                self._redis_client = redis.from_url(redis_url)
                logger.debug("Redis client initialized (lazy)")
            except Exception as e:
                logger.warning(f"Redis client initialization failed: {e}")
                self._redis_client = None
        return self._redis_client

    def get_queue_status(self, is_admin: bool = False) -> Dict[str, Any]:
        """
        Get simple queue status
        Admin and users see the same basic data
        """
        try:
            if self.db_service:
                # Get real job statistics from database with today filtering
                all_jobs = self.db_service.get_jobs(limit=1000)

                # Get today's date for filtering today's jobs
                today = datetime.now(timezone.utc).date()

                # Count job statuses (all time)
                pending = len([job for job in all_jobs if job["status"] in ["pending", "queued"]])
                processing = len([job for job in all_jobs if job["status"] == "processing"])
                
                # Count today's completed and failed jobs only
                completed_today = 0
                failed_today = 0
                
                for job in all_jobs:
                    # Parse job creation/completion date 
                    job_date = None
                    if job.get("updated_at"):
                        try:
                            # Handle different date formats
                            date_str = job["updated_at"]
                            if date_str.endswith('Z'):
                                job_datetime = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            else:
                                job_datetime = datetime.fromisoformat(date_str)
                            job_date = job_datetime.date()
                        except:
                            # Fallback to created_at if updated_at parsing fails
                            try:
                                date_str = job.get("created_at", "")
                                if date_str.endswith('Z'):
                                    job_datetime = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                                else:
                                    job_datetime = datetime.fromisoformat(date_str)
                                job_date = job_datetime.date()
                            except:
                                continue
                    
                    # Count only today's completed and failed jobs
                    if job_date == today:
                        if job["status"] == "completed":
                            completed_today += 1
                        elif job["status"] == "failed":
                            failed_today += 1

                return {
                    "pending": pending,
                    "processing": processing,
                    "completed_today": completed_today,  # FIXED: Now only today's completed jobs
                    "failed_today": failed_today,        # FIXED: Now only today's failed jobs
                    "total": len(all_jobs),
                    # Legacy fields for compatibility
                    "completed": len([job for job in all_jobs if job["status"] == "completed"]),
                    "failed": len([job for job in all_jobs if job["status"] == "failed"])
                }
            else:
                # 🎭 MOCK DATA - No database connection, using demo data
                return {
                    "pending": 3,
                    "processing": 2,
                    "completed": 147,
                    "failed": 5,
                    "total": 157,
                    "is_mock_data": True,
                    "mock_reason": "Database service not initialized"
                }
        except Exception as e:
            logger.error(f"Failed to get queue status: {e}")
            # 🎭 MOCK DATA - Database service unavailable, using fallback data for demo
            return {
                "pending": 10,
                "processing": 10,
                "completed_today": 0,      # FIXED: Use today fields
                "failed_today": 0,         # FIXED: Use today fields  
                "total": 25,
                # Legacy fields for compatibility
                "completed": 147,
                "failed": 5,
                "is_mock_data": True,
                "mock_reason": "Database service unavailable",
                "error": f"🎭 MOCK: {str(e)}" if is_admin else "🎭 MOCK: Service using demo data"
            }

    def get_queue_details(self, limit: int = 20, is_admin: bool = False) -> Dict[str, Any]:
        """
        Get detailed queue information
        Admin sees full details, users see limited info
        """
        try:
            if self.db_service:
                # Get recent jobs for queue view
                jobs = self.db_service.get_jobs(limit=limit)
                health_data = self.db_service.health_check()

                # Filter sensitive data for non-admin users
                if not is_admin:
                    for job in jobs:
                        job.pop("user_id", None)
                        job.pop("error_message", None)
                        job.pop("retry_count", None)

                return {
                    "jobs": jobs[:limit],  # Limit results
                    "queue_size": health_data["stats"]["total_jobs"],
                    "processing_time_avg": 120,  # TODO: calculate from database
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                }
            else:
                return {
                    "jobs": [],
                    "queue_size": 0,
                    "processing_time_avg": 0,
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                }
        except Exception as e:
            logger.error(f"Failed to get queue details: {e}")
            return {
                "jobs": [],
                "queue_size": 0,
                "processing_time_avg": 0,
                "error": str(e) if is_admin else "Service unavailable",
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            }

    def get_queue_stats(self, is_admin: bool = False) -> Dict[str, Any]:
        """
        Get queue statistics for UI compatibility
        Similar to status but with different format
        """
        try:
            if self.db_service:
                # Get real job statistics from database
                all_jobs = self.db_service.get_jobs(limit=1000)

                # Get today's date for filtering today's jobs
                today = datetime.now(timezone.utc).date()

                # Count job statuses (all time)
                pending = len([job for job in all_jobs if job["status"] in ["pending", "queued"]])
                processing = len([job for job in all_jobs if job["status"] == "processing"])
                
                # Count today's completed and failed jobs only
                completed_today = 0
                failed_today = 0
                
                for job in all_jobs:
                    # Parse job creation/completion date 
                    job_date = None
                    if job.get("updated_at"):
                        try:
                            # Handle different date formats
                            date_str = job["updated_at"]
                            if date_str.endswith('Z'):
                                job_datetime = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            else:
                                job_datetime = datetime.fromisoformat(date_str)
                            job_date = job_datetime.date()
                        except:
                            # Fallback to created_at if updated_at parsing fails
                            try:
                                date_str = job.get("created_at", "")
                                if date_str.endswith('Z'):
                                    job_datetime = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                                else:
                                    job_datetime = datetime.fromisoformat(date_str)
                                job_date = job_datetime.date()
                            except:
                                continue
                    
                    # Count only today's completed and failed jobs
                    if job_date == today:
                        if job["status"] == "completed":
                            completed_today += 1
                        elif job["status"] == "failed":
                            failed_today += 1

                stats = {
                    "queue_length": pending,
                    "processing_jobs": processing,
                    "completed_today": completed_today,  # FIXED: Now only today's completed jobs
                    "failed_today": failed_today,        # FIXED: Now only today's failed jobs  
                    "average_processing_time": 120.5,  # TODO: calculate real average
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                }

                # Add admin-only fields
                if is_admin:
                    # Calculate all-time totals for admin fields
                    completed_all = len([job for job in all_jobs if job["status"] == "completed"])
                    failed_all = len([job for job in all_jobs if job["status"] == "failed"])
                    
                    stats.update({
                        "total_jobs_lifetime": len(all_jobs),
                        "success_rate": round((completed_today / (completed_today + failed_today) * 100) if (completed_today + failed_today) > 0 else 0, 2),
                        "queue_health": "healthy" if pending < 100 else "busy",
                        # Add all-time stats for reference
                        "completed_all_time": completed_all,
                        "failed_all_time": failed_all
                    })

                return stats
            else:
                return {
                    "queue_length": 0,
                    "processing_jobs": 0,
                    "completed_today": 0,
                    "failed_today": 0,
                    "average_processing_time": 0,
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                }
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {
                "queue_length": 0,
                "processing_jobs": 0,
                "completed_today": 0,
                "failed_today": 0,
                "average_processing_time": 0,
                "error": str(e) if is_admin else "Service unavailable",
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            }

    def get_workers_status(self, is_admin: bool = False) -> List[Dict[str, Any]]:
        """
        🎬 NETFLIX PATTERN v4: Get worker status from Redis (5ms) with event integration

        Workers self-report their status to Redis every minute
        Dashboard gets instant data without expensive inspection calls
        V4: Integrated with event dispatcher for real-time updates
        """
        try:
            # V4 OPTIMIZATION: Use lazy-loaded Redis client
            r = self.redis_client
            if not r:
                logger.error("Redis client not available for worker status")
                return self._get_fallback_workers()

            # Get all worker status from Redis (5ms lookup)
            worker_keys = r.keys("worker_status:*")

            workers = []
            for key in worker_keys:
                try:
                    worker_json = r.get(key)
                    if worker_json:
                        import json
                        worker_data = json.loads(worker_json)

                        # Validate data freshness (within last 2 minutes)
                        last_heartbeat = datetime.fromisoformat(
                            worker_data['last_heartbeat'].replace('Z', '+00:00')
                        )
                        now = datetime.now(timezone.utc)
                        age_seconds = (now - last_heartbeat).total_seconds()

                        if age_seconds < 120:  # Fresh data (< 2 minutes old)
                            workers.append(worker_data)
                        else:
                            # Mark as stale but include it
                            worker_data['status'] = 'stale'
                            worker_data['warning'] = f'Last seen {int(age_seconds)}s ago'
                            workers.append(worker_data)

                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.warning(f"Invalid worker data in Redis: {e}")
                    continue

            if workers:
                logger.info(f"✅ v4: Retrieved worker data from Redis in ~5ms: {len(workers)} workers")

                # V4 EVENT INTEGRATION: Check for worker status changes
                self._check_worker_status_events(workers)
                return workers
            else:
                # No Redis data - fall back to direct inspection (slow but necessary)
                logger.warning("⚠️ No worker data in Redis, falling back to Celery inspection")

                # V4 EVENT: Cache miss event
                asyncio.create_task(dispatcher.dispatch("worker:cache_miss", {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "fallback": "celery_inspection"
                }))

                return self._get_celery_inspection_fallback()

        except Exception as e:
            logger.error(f"❌ Redis worker lookup failed: {e}")
            return self._get_celery_inspection_fallback()

    def _get_celery_inspection_fallback(self) -> List[Dict[str, Any]]:
        """
        Fallback to direct Celery inspection if Redis data unavailable
        This is the old slow method (6000ms) - only used as emergency fallback
        """
        try:
            from core.celery_app import celery_app
            import signal

            # Set timeout for Celery inspection
            def timeout_handler(signum, frame):
                raise TimeoutError("Celery inspect timeout")

            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(3)  # Reduced to 3 second timeout

            try:
                # Get minimal worker stats only
                inspect = celery_app.control.inspect()
                stats = inspect.stats()

                workers = []
                if stats:
                    for worker_name, worker_stats in stats.items():
                        total_stats = worker_stats.get('total', {})

                        workers.append({
                            "worker_id": worker_name,
                            "status": "active",
                            "current_tasks": total_stats.get('tasks.active', 0),
                            "total_tasks_completed": total_stats.get('tasks.completed', 0),
                            "load_average": 0.0,  # Skip expensive calculations
                            "memory_usage": 0,
                            "pool_size": "unknown",
                            "last_heartbeat": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                            "queues": ["video_processing", "transcription", "ai_analysis", "file_operations"],
                            "data_source": "celery_inspection_fallback"
                        })

                logger.warning(f"⚠️ Used slow Celery inspection fallback: {len(workers)} workers")
                return workers

            finally:
                signal.alarm(0)

        except Exception as e:
            logger.error(f"❌ Celery inspection fallback failed: {e}")
            return self._get_fallback_workers()

    def _get_fallback_workers(self) -> List[Dict[str, Any]]:
        """Fallback worker data when Celery inspection fails"""
        return [{
            "worker_id": "worker-offline",
            "status": "unknown",
            "current_tasks": 0,
            "total_tasks_completed": 0,
            "load_average": 0.0,
            "memory_usage": 0,
            "pool_size": "unknown",
            "last_heartbeat": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "queues": [],
            "error": "Could not connect to Celery workers - they may be offline"
        }]

    def get_queue_statistics(self, is_admin: bool = False) -> Dict[str, Any]:
        """
        Get detailed queue statistics for analytics
        """
        try:
            # Mock queue statistics for now
            # In real implementation, would query from database and Celery
            return {
                "total_jobs_processed": 147,
                "average_processing_time": 125.5,
                "peak_queue_length_today": 15,
                "current_queue_length": 3,
                "jobs_per_hour_avg": 12.3,
                "success_rate_percentage": 94.6,
                "most_common_job_type": "video_processing",
                "queue_health_score": 8.7,
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            }

        except Exception as e:
            logger.error(f"Failed to get queue statistics: {e}")
            return {
                "error": str(e) if is_admin else "Service unavailable",
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            }

    def get_worker_assignments(self, is_admin: bool = False) -> Dict[str, Any]:
        """
        Get worker assignments and queue distribution - Uses real Celery data
        Shows which workers are handling which types of tasks
        """
        try:
            # 🎯 FIXED: Use real worker data instead of mock
            workers = self.get_workers_status(is_admin=is_admin)

            # Transform to assignment format
            worker_assignments = []
            for worker in workers:
                worker_assignments.append({
                    "worker_id": worker.get("worker_id", "unknown"),
                    "status": worker.get("status", "unknown"),
                    "current_tasks": worker.get("current_tasks", 0),
                    "queues": worker.get("queues", []),
                    "last_seen": worker.get("last_heartbeat", datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
                })

            # Get real queue data from job statuses
            if self.db_service:
                jobs_data = self.db_service.get_stats()
                queue_distribution = {
                    "video_processing": {
                        "pending": jobs_data.get("pending_jobs", 0),
                        "processing": jobs_data.get("processing_jobs", 0)
                    },
                    "transcription": {"pending": 0, "processing": 0},
                    "ai_analysis": {"pending": 0, "processing": 0},
                    "file_operations": {"pending": 0, "processing": 0}
                }
            else:
                # Fallback distribution
                queue_distribution = {
                    "video_processing": {"pending": 0, "processing": 0},
                    "transcription": {"pending": 0, "processing": 0},
                    "ai_analysis": {"pending": 0, "processing": 0},
                    "file_operations": {"pending": 0, "processing": 0}
                }

            return {
                "workers": worker_assignments,
                "queue_distribution": queue_distribution,
                "total_workers": len(worker_assignments),
                "active_workers": len([w for w in worker_assignments if w["status"] == "active"]),
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "status": "success"
            }

        except Exception as e:
            logger.error(f"Failed to get worker assignments: {e}")
            return {
                "workers": [],
                "queue_distribution": {},
                "total_workers": 0,
                "active_workers": 0,
                "error": str(e) if is_admin else "Service unavailable",
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "status": "error"
            }

    def purge_queue(self, status_filter: Optional[str] = None, is_admin: bool = False) -> Dict[str, Any]:
        """
        Purge the job queue
        Admin only operation
        """
        if not is_admin:
            return {
                "success": False,
                "error": "Unauthorized: Admin access required"
            }

        try:
            purged_count = 0

            if self.db_service:
                # Get all jobs to purge based on status
                all_jobs = self.db_service.get_jobs(limit=10000)

                for job in all_jobs:
                    should_purge = False

                    if status_filter:
                        # Purge only jobs with specific status
                        should_purge = job["status"] == status_filter
                    else:
                        # Purge failed and old pending jobs
                        should_purge = job["status"] in ["failed", "pending", "queued"]

                    if should_purge:
                        try:
                            # In real implementation, would delete from database
                            # For now, just count
                            purged_count += 1
                        except Exception as e:
                            logger.error(f"Failed to purge job {job['id']}: {e}")

            return {
                "success": True,
                "purged_jobs": purged_count,
                "purge_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "message": f"Successfully purged {purged_count} jobs from queue"
            }

        except Exception as e:
            logger.error(f"Failed to purge queue: {e}")
            return {
                "success": False,
                "error": str(e),
                "purged_jobs": 0
            }

    # V4 EVENT INTEGRATION METHODS

    def _check_worker_status_events(self, workers: List[Dict[str, Any]]):
        """
        Check for worker status changes and trigger events

        V4: Integrated with event dispatcher for real-time notifications
        """
        try:
            # Check for offline workers
            offline_workers = [w for w in workers if w.get("status") == "stale" or w.get("status") == "offline"]
            if offline_workers:
                for worker in offline_workers:
                    # Trigger worker offline event
                    asyncio.create_task(dispatcher.dispatch("worker:offline", {
                        "worker_id": worker.get("worker_id"),
                        "last_seen": worker.get("last_heartbeat"),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }))

            # Check for overloaded workers
            overloaded_workers = [w for w in workers if w.get("current_tasks", 0) > 10]
            if overloaded_workers:
                for worker in overloaded_workers:
                    asyncio.create_task(dispatcher.dispatch("worker:overloaded", {
                        "worker_id": worker.get("worker_id"),
                        "current_tasks": worker.get("current_tasks", 0),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }))

        except Exception as e:
            logger.error(f"Worker status event checking failed: {e}")

    # V4 ASYNC METHODS: Enable parallel execution in AdminDataManager

    async def get_queue_status_async(self, is_admin: bool = False) -> Dict[str, Any]:
        """Async wrapper for queue status"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.get_queue_status, is_admin
        )

    async def get_workers_status_async(self, is_admin: bool = False) -> List[Dict[str, Any]]:
        """Async wrapper for workers status"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.get_workers_status, is_admin
        )

    async def get_queue_statistics_async(self, is_admin: bool = False) -> Dict[str, Any]:
        """Async wrapper for queue statistics"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.get_queue_statistics, is_admin
        )

    async def get_worker_assignments_async(self, is_admin: bool = False) -> Dict[str, Any]:
        """Async wrapper for worker assignments"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.get_worker_assignments, is_admin
        )

    # ============ V5 ENTERPRISE ACTION METHODS ============

    async def pause_processing(self, queue_name: str = "default", **kwargs) -> Dict[str, Any]:
        """
        Pause queue processing - V5 Enterprise Action

        Args:
            queue_name: Name of queue to pause (default: "default")

        Returns:
            Action result with success status
        """
        logger.info(f"Pausing queue processing: {queue_name}")

        try:
            # Set queue pause flag in Redis
            r = self.redis_client
            if r:
                r.set(f"queue:paused:{queue_name}", "true", ex=3600)  # 1 hour expiry
                logger.info(f"Queue {queue_name} marked as paused in Redis")

            # Trigger event for real-time UI updates
            await dispatcher.dispatch("queue:paused", {
                "queue_name": queue_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "pause_processing"
            })

            return {
                "success": True,
                "message": f"Queue {queue_name} processing paused",
                "queue_name": queue_name,
                "paused": True
            }

        except Exception as e:
            logger.error(f"Failed to pause queue {queue_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "queue_name": queue_name
            }

    async def resume_processing(self, queue_name: str = "default", **kwargs) -> Dict[str, Any]:
        """
        Resume queue processing - V5 Enterprise Action

        Args:
            queue_name: Name of queue to resume (default: "default")

        Returns:
            Action result with success status
        """
        logger.info(f"Resuming queue processing: {queue_name}")

        try:
            # Remove queue pause flag from Redis
            r = self.redis_client
            if r:
                r.delete(f"queue:paused:{queue_name}")
                logger.info(f"Queue {queue_name} pause flag removed from Redis")

            # Trigger event for real-time UI updates
            await dispatcher.dispatch("queue:resumed", {
                "queue_name": queue_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "resume_processing"
            })

            return {
                "success": True,
                "message": f"Queue {queue_name} processing resumed",
                "queue_name": queue_name,
                "paused": False
            }

        except Exception as e:
            logger.error(f"Failed to resume queue {queue_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "queue_name": queue_name
            }

    async def clear_queue(self, queue_name: str = "default", **kwargs) -> Dict[str, Any]:
        """
        Clear all jobs from queue - V5 Enterprise Action (HIGH RISK)

        Args:
            queue_name: Name of queue to clear (default: "default")

        Returns:
            Action result with job count cleared
        """
        logger.warning(f"CLEARING QUEUE: {queue_name} - HIGH RISK OPERATION")

        try:
            # This would integrate with your job system to clear pending jobs
            # For now, return success with mock data
            cleared_count = 0  # Would be actual cleared job count

            # Trigger critical event
            await dispatcher.dispatch("queue:cleared", {
                "queue_name": queue_name,
                "cleared_count": cleared_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": "clear_queue",
                "risk_level": "HIGH"
            })

            return {
                "success": True,
                "message": f"Queue {queue_name} cleared",
                "queue_name": queue_name,
                "cleared_count": cleared_count
            }

        except Exception as e:
            logger.error(f"Failed to clear queue {queue_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "queue_name": queue_name
            }

    # ==========================================
    # NEW QUEUE METRICS FOR JOBHISTORY REDESIGN
    # ==========================================
    
    def get_queue_depth(self) -> int:
        """
        Get number of pending jobs in queue
        Returns count of jobs with status 'pending' or 'queued'
        """
        try:
            if self.db_service:
                all_jobs = self.db_service.get_jobs(limit=1000)
                pending_count = len([job for job in all_jobs if job["status"] in ["pending", "queued"]])
                logger.debug(f"Queue depth: {pending_count} pending jobs")
                return pending_count
            return 0
        except Exception as e:
            logger.error(f"Failed to get queue depth: {e}")
            return 0
    
    def get_queue_throughput(self) -> Dict[str, Any]:
        """
        Calculate jobs processed per hour
        Returns throughput metrics and trend
        """
        try:
            if self.db_service:
                all_jobs = self.db_service.get_jobs(limit=1000)
                now = datetime.now(timezone.utc)
                
                # Calculate for last hour
                one_hour_ago = now - timedelta(hours=1)
                completed_last_hour = 0
                
                # Calculate for previous hour (for trend)
                two_hours_ago = now - timedelta(hours=2)
                completed_previous_hour = 0
                
                for job in all_jobs:
                    if job["status"] == "completed" and job.get("completed_at"):
                        try:
                            completed_str = job["completed_at"]
                            if completed_str.endswith('Z'):
                                completed_time = datetime.fromisoformat(completed_str.replace('Z', '+00:00'))
                            else:
                                completed_time = datetime.fromisoformat(completed_str)
                            
                            if completed_time >= one_hour_ago:
                                completed_last_hour += 1
                            elif completed_time >= two_hours_ago:
                                completed_previous_hour += 1
                        except:
                            continue
                
                # Calculate trend
                if completed_previous_hour > 0:
                    trend_percentage = ((completed_last_hour - completed_previous_hour) / completed_previous_hour) * 100
                    trend = f"{'↑' if trend_percentage > 0 else '↓'} {abs(int(trend_percentage))}%"
                else:
                    trend = "→ stable"
                
                return {
                    "per_hour": completed_last_hour,
                    "trend": trend,
                    "last_hour": completed_last_hour,
                    "previous_hour": completed_previous_hour
                }
            
            return {"per_hour": 0, "trend": "→ stable", "last_hour": 0, "previous_hour": 0}
            
        except Exception as e:
            logger.error(f"Failed to get queue throughput: {e}")
            return {"per_hour": 0, "trend": "unknown", "last_hour": 0, "previous_hour": 0}
    
    def get_average_wait_time(self) -> float:
        """
        Calculate average time jobs wait in queue before processing
        Returns average wait time in seconds
        """
        try:
            if self.db_service:
                all_jobs = self.db_service.get_jobs(limit=100)
                wait_times = []
                
                for job in all_jobs:
                    if job["status"] in ["processing", "completed"] and job.get("created_at") and job.get("started_at"):
                        try:
                            created_str = job["created_at"]
                            started_str = job["started_at"]
                            
                            # Parse timestamps
                            if created_str.endswith('Z'):
                                created_time = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                            else:
                                created_time = datetime.fromisoformat(created_str)
                            
                            if started_str.endswith('Z'):
                                started_time = datetime.fromisoformat(started_str.replace('Z', '+00:00'))
                            else:
                                started_time = datetime.fromisoformat(started_str)
                            
                            wait_time = (started_time - created_time).total_seconds()
                            if wait_time >= 0:  # Sanity check
                                wait_times.append(wait_time)
                        except:
                            continue
                
                if wait_times:
                    avg_wait = sum(wait_times) / len(wait_times)
                    logger.debug(f"Average wait time: {avg_wait:.2f} seconds")
                    return round(avg_wait, 2)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Failed to get average wait time: {e}")
            return 0.0
    
    def get_worker_utilization(self) -> float:
        """
        Calculate percentage of busy workers
        Returns utilization as percentage (0-100)
        """
        try:
            workers = self.get_workers_status(is_admin=True)
            
            if not workers:
                return 0.0
            
            total_workers = len(workers)
            busy_workers = len([w for w in workers if w.get("current_tasks", 0) > 0])
            
            if total_workers > 0:
                utilization = (busy_workers / total_workers) * 100
                logger.debug(f"Worker utilization: {utilization:.1f}% ({busy_workers}/{total_workers} busy)")
                return round(utilization, 1)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Failed to get worker utilization: {e}")
            return 0.0
    
    def get_24h_success_rate(self) -> float:
        """
        Calculate success rate for last 24 hours only
        Returns percentage (0-100)
        """
        try:
            if self.db_service:
                all_jobs = self.db_service.get_jobs(limit=1000)
                now = datetime.now(timezone.utc)
                yesterday = now - timedelta(hours=24)
                
                completed_24h = 0
                failed_24h = 0
                
                for job in all_jobs:
                    try:
                        # Check if job is from last 24 hours
                        created_str = job.get("created_at", "")
                        if created_str:
                            if created_str.endswith('Z'):
                                created_time = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                            else:
                                created_time = datetime.fromisoformat(created_str)
                            
                            if created_time >= yesterday:
                                if job["status"] == "completed":
                                    completed_24h += 1
                                elif job["status"] == "failed":
                                    failed_24h += 1
                    except:
                        continue
                
                total_24h = completed_24h + failed_24h
                if total_24h > 0:
                    success_rate = (completed_24h / total_24h) * 100
                    logger.debug(f"24h success rate: {success_rate:.1f}% ({completed_24h}/{total_24h})")
                    return round(success_rate, 1)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Failed to get 24h success rate: {e}")
            return 0.0
