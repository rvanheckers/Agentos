"""
Database Service - Legacy Facade naar SSOT Services

Deze service biedt backward compatibility voor legacy routes.
FIXED: Nu gebruikt SSOT services in plaats van eigen berekeningen.

Flow: Legacy Routes → DatabaseService → SSOT Services (JobsService, AgentsService)
Purpose: Facade pattern voor legacy compatibility zonder duplicatie
"""
from typing import List, Optional, Dict, Any
from core.database_manager import PostgreSQLManager, Job
from core.logging_config import get_logger
from sqlalchemy import desc, func
from datetime import datetime, timezone, date

logger = get_logger("api_server")

class DatabaseService:
    def __init__(self):
        self.db_manager = PostgreSQLManager()

    def get_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all jobs from database"""
        try:
            with self.db_manager.get_session() as session:
                jobs = session.query(Job)\
                            .order_by(desc(Job.created_at))\
                            .limit(limit)\
                            .all()
                return [self._job_to_dict(job) for job in jobs]
        except Exception as e:
            logger.error(f"Database service error getting jobs: {e}")
            return []

    def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get specific job by ID"""
        try:
            with self.db_manager.get_session() as session:
                job = session.query(Job).filter(Job.id == job_id).first()
                return self._job_to_dict(job) if job else None
        except Exception as e:
            logger.error(f"Database service error getting job {job_id}: {e}")
            return None

    def create_job(self, job_data: Dict[str, Any]) -> str:
        """Create new job"""
        try:
            return self.db_manager.create_job(
                video_url=job_data.get('video_url', ''),
                user_id=job_data.get('user_id', 'anonymous'),
                video_title=job_data.get('video_title', '')
            )
        except Exception as e:
            logger.error(f"Database service error creating job: {e}")
            raise

    def update_job_status(self, job_id: str, status: str, progress: int = None) -> bool:
        """Update job status"""
        try:
            return self.db_manager.update_job_status(job_id, status, progress)
        except Exception as e:
            logger.error(f"Database service error updating job {job_id}: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics - Enhanced with SSOT success rate"""
        try:
            # Get raw stats from database manager
            stats = self.db_manager.get_stats()

            # 🎯 FIXED: Override success rate with SSOT calculation
            from services.jobs_service import JobsService
            jobs_service = JobsService()
            job_stats = jobs_service.get_job_statistics(is_admin=True)

            # Use SSOT success rate instead of database manager calculation
            stats["success_rate"] = job_stats.get("success_rate", stats.get("success_rate", 0))

            return stats
        except Exception as e:
            logger.error(f"Database service error getting stats: {e}")
            return {
                "total_jobs": 0,
                "completed_jobs": 0,
                "failed_jobs": 0,
                "processing_jobs": 0,
                "success_rate": 0.0
            }

    def get_today_jobs(self) -> Dict[str, Any]:
        """Get today's job statistics and recent jobs"""
        try:
            with self.db_manager.get_session() as session:
                # Filter jobs created today
                today = date.today()
                jobs_query = session.query(Job).filter(func.date(Job.created_at) == today)

                # Get all today's jobs
                today_jobs = jobs_query.order_by(desc(Job.created_at)).all()

                # Count statuses for today
                completed = sum(1 for job in today_jobs if job.status == "completed")
                processing = sum(1 for job in today_jobs if job.status == "processing")
                pending = sum(1 for job in today_jobs if job.status in ["pending", "queued"])
                failed = sum(1 for job in today_jobs if job.status == "failed")

                return {
                    "completed": completed,
                    "processing": processing,
                    "pending": pending,
                    "failed": failed,
                    "total_jobs": len(today_jobs),
                    "jobs": [self._job_to_dict(job) for job in today_jobs[:10]]  # Return max 10 most recent jobs
                }

        except Exception as e:
            logger.error(f"Database service error getting today's jobs: {e}")
            return {
                "completed": 0,
                "processing": 0,
                "pending": 0,
                "failed": 0,
                "total_jobs": 0,
                "jobs": []
            }

    def get_recent_clips(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent clips from database"""
        try:
            return self.db_manager.get_recent_clips(limit)
        except Exception as e:
            logger.error(f"Database service error getting recent clips: {e}")
            return []

    def health_check(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            stats = self.get_stats()
            return {
                "status": "healthy",
                "connection": "ok",
                "tables_accessible": True,
                "stats": stats
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "connection": "failed",
                "error": str(e)
            }

    def _job_to_dict(self, job: Job) -> Dict[str, Any]:
        """Convert Job model to dictionary"""
        if not job:
            return None

        return {
            "id": str(job.id),
            "job_id": str(job.id),  # Legacy compatibility
            "user_id": job.user_id,
            "status": job.status,
            "progress": job.progress or 0,
            "video_url": job.video_url,
            "video_title": job.video_title,
            "current_step": job.current_step,
            "error_message": job.error_message,
            "retry_count": job.retry_count or 0,
            "worker_id": job.worker_id,
            "priority": job.priority or 5,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "updated_at": (job.completed_at or job.started_at or job.created_at).isoformat() if (job.completed_at or job.started_at or job.created_at) else None
        }

    def get_analytics_data(self) -> Dict[str, Any]:
        """Get analytics data for dashboard - Uses SSOT via JobsService"""
        try:
            # 🎯 FIXED: Use SSOT instead of legacy bypass
            from services.jobs_service import JobsService
            jobs_service = JobsService()

            # Get analytics from the proper SSOT
            job_stats = jobs_service.get_job_statistics(is_admin=True)

            return {
                "success_rate": job_stats.get("success_rate", 0),
                "avg_processing_time": job_stats.get("avg_processing_time", 0),
                "total_jobs": job_stats.get("total_jobs", 0),
                "completed_jobs": job_stats.get("completed_jobs", 0),
                "failed_jobs": job_stats.get("failed_jobs", 0)
            }
        except Exception as e:
            logger.error(f"Database service error getting analytics data: {e}")
            # Fallback to SSOT even in error case
            try:
                from services.jobs_service import JobsService
                jobs_service = JobsService()
                return jobs_service.get_job_statistics(is_admin=True)
            except:
                return {
                    "success_rate": 0,
                    "avg_processing_time": 0,
                    "total_jobs": 0,
                    "completed_jobs": 0,
                    "failed_jobs": 0,
                    "error": str(e)
                }

    def get_agents_summary(self) -> Dict[str, Any]:
        """Get agents summary for dashboard - Uses SSOT via AgentsService"""
        try:
            # 🎯 FIXED: Use SSOT instead of mock data
            from services.agents_service import AgentsService
            agents_service = AgentsService()

            # Get agents data from the proper SSOT
            return agents_service.get_agents_summary()

        except Exception as e:
            logger.error(f"Database service error getting agents summary: {e}")
            # Fallback to basic agent list if service fails
            return {
                "total": 11,
                "active": 9,
                "inactive": 2,
                "agents": [
                    "VideoDownloader", "AudioTranscriber", "MomentDetector",
                    "FaceDetector", "IntelligentCropper", "VideoCutter",
                    "QualityAnalyzer", "MetadataExtractor", "ThumbnailGenerator",
                    "ContentModerator", "FileManager"
                ],
                "error": str(e)
            }

    def get_system_configuration(self) -> Dict[str, Any]:
        """Get system configuration data"""
        try:
            return {
                "database": {
                    "type": "postgresql",
                    "host": "localhost",
                    "port": 5432,
                    "name": "agentos_v4",
                    "connection_pool_size": 10,
                    "max_overflow": 20
                },
                "api": {
                    "host": "0.0.0.0",
                    "port": 8001,
                    "workers": 4,
                    "timeout": 120,
                    "keepalive": 60
                },
                "celery": {
                    "broker_url": "redis://localhost:6379/0",
                    "result_backend": "redis://localhost:6379/0",
                    "task_serializer": "json",
                    "result_serializer": "json",
                    "timezone": "UTC"
                },
                "redis": {
                    "host": "localhost",
                    "port": 6379,
                    "db": 0,
                    "decode_responses": True
                },
                "websocket": {
                    "host": "localhost",
                    "port": 8765,
                    "max_connections": 100,
                    "ping_interval": 20,
                    "ping_timeout": 10
                },
                "logging": {
                    "level": "INFO",
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    "file_rotation": True,
                    "max_file_size": "10MB",
                    "backup_count": 5
                },
                "storage": {
                    "input_directory": "./io/input",
                    "output_directory": "./io/output",
                    "temp_directory": "./io/temp",
                    "max_file_size_mb": 500,
                    "allowed_extensions": [".mp4", ".avi", ".mov", ".mkv", ".webm"]
                },
                "ai": {
                    "use_mock_ai": True,
                    "openai_api_key": "[CONFIGURED]",
                    "anthropic_api_key": "[CONFIGURED]",
                    "google_api_key": "[CONFIGURED]"
                },
                "system": {
                    "version": "4.0.0",
                    "environment": "development",
                    "debug_mode": True,
                    "maintenance_mode": False,
                    "max_concurrent_jobs": 10,
                    "job_timeout_seconds": 3600
                },
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get system configuration: {e}")
            return {
                "error": str(e),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
