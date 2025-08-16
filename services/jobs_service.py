"""
Jobs Service Layer
Handles all job-related business logic for both admin and user endpoints
Eliminates 12 duplicate method implementations
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, date, timezone
from uuid import UUID, uuid4
from core.database_manager import Job, Clip
from core.database_pool import get_db_session
from sqlalchemy import desc, func
import logging

# V4 Workflow Integration
from events.workflow_orchestrator import get_workflow_orchestrator, WorkflowType

logger = logging.getLogger(__name__)


class JobsService:
    """Central service for all job-related operations"""

    def __init__(self, db_manager = None):
        # ✅ Using shared database pool - no individual connections needed
        pass

    def get_todays_jobs(self, user_id: Optional[str] = None, is_admin: bool = False) -> List[Dict[str, Any]]:
        """Get all jobs created today
        Admin sees all jobs, users see only their own"""
        with get_db_session() as session:
            query = session.query(Job)

            # Filter by date
            today = date.today()
            query = query.filter(func.date(Job.created_at) == today)

            # Apply user filter for non-admin
            if not is_admin and user_id:
                query = query.filter(Job.user_id == user_id)

            jobs = query.order_by(desc(Job.created_at)).all()
            return [self._job_to_dict(job) for job in jobs]

    def get_job_history(self, user_id: Optional[str] = None, is_admin: bool = False,
                       limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Get job history with pagination
        Admin sees all jobs, users see only their own"""
        with get_db_session() as session:
            query = session.query(Job)

            # Apply user filter for non-admin
            if not is_admin and user_id:
                query = query.filter(Job.user_id == user_id)

            # Get total count
            total = query.count()

            # Get paginated results
            jobs = query.order_by(desc(Job.created_at))\
                       .limit(limit)\
                       .offset(offset)\
                       .all()

            return {
                "total": total,
                "jobs": [self._job_to_dict(job) for job in jobs],
                "limit": limit,
                "offset": offset
            }

    def get_job_by_id(self, job_id: UUID | str, user_id: Optional[str] = None, is_admin: bool = False) -> Optional[Dict[str, Any]]:
        """Get single job by ID
        Admin can see any job, users can only see their own"""
        with get_db_session() as session:
            # Ensure job_id is UUID for proper database comparison
            job_uuid = UUID(job_id) if isinstance(job_id, str) else job_id
            query = session.query(Job).filter(Job.id == job_uuid)

            # Apply user filter for non-admin
            if not is_admin and user_id:
                query = query.filter(Job.user_id == user_id)

            job = query.first()
            return self._job_to_dict(job) if job else None

    def get_job_status(self, job_id: UUID | str, user_id: Optional[str] = None, is_admin: bool = False) -> Optional[Dict[str, str]]:
        """Get job status
        Admin can see any job status, users can only see their own"""
        job = self.get_job_by_id(job_id, user_id, is_admin)
        if job:
            return {
                "job_id": job["id"],
                "status": job["status"],
                "progress": job.get("progress", 0),
                "updated_at": job["updated_at"]
            }
        return None

    def update_job_status(self, job_id: UUID | str, status: str, progress: Optional[int] = None,
                         user_id: Optional[str] = None, is_admin: bool = False) -> bool:
        """Update job status
        Only admin or job owner can update"""
        with get_db_session() as session:
            # Ensure job_id is UUID for proper database comparison
            job_uuid = UUID(job_id) if isinstance(job_id, str) else job_id
            query = session.query(Job).filter(Job.id == job_uuid)

            # Apply user filter for non-admin
            if not is_admin and user_id:
                query = query.filter(Job.user_id == user_id)

            job = query.first()
            if job:
                job.status = status
                if progress is not None:
                    job.progress = progress
                job.updated_at = datetime.now(timezone.utc)
                session.commit()
                return True
            return False

    def delete_job(self, job_id: UUID | str, user_id: Optional[str] = None, is_admin: bool = False, **kwargs) -> Dict[str, Any]:
        """Delete a job
        Only admin or job owner can delete"""
        with get_db_session() as session:
            # Ensure job_id is UUID for proper database comparison
            job_uuid = UUID(job_id) if isinstance(job_id, str) else job_id
            query = session.query(Job).filter(Job.id == job_uuid)

            # Apply user filter for non-admin
            if not is_admin and user_id:
                query = query.filter(Job.user_id == user_id)

            job = query.first()
            if job:
                # Also delete associated clips
                session.query(Clip).filter(Clip.job_id == job_id).delete()
                session.delete(job)
                session.commit()
                return {
                    "success": True,
                    "job_id": job_id,
                    "message": "Job and associated clips deleted successfully"
                }
            return {
                "success": False,
                "job_id": job_id,
                "message": "Job not found or unauthorized"
            }

    def get_jobs_by_status(self, status: str, user_id: Optional[str] = None, is_admin: bool = False) -> List[Dict[str, Any]]:
        """Get all jobs with specific status
        Admin sees all, users see only their own"""
        with get_db_session() as session:
            query = session.query(Job).filter(Job.status == status)

            # Apply user filter for non-admin
            if not is_admin and user_id:
                query = query.filter(Job.user_id == user_id)

            jobs = query.order_by(desc(Job.created_at)).all()
            return [self._job_to_dict(job) for job in jobs]

    def get_job_clips(self, job_id: UUID | str, user_id: Optional[str] = None, is_admin: bool = False) -> List[Dict[str, Any]]:
        """Get all clips for a job
        Admin can see any job's clips, users only their own"""
        # First verify job access
        job = self.get_job_by_id(job_id, user_id, is_admin)
        if not job:
            return []

        with get_db_session() as session:
            clips = session.query(Clip)\
                          .filter(Clip.job_id == job_id)\
                          .order_by(Clip.clip_number)\
                          .all()
            return [self._clip_to_dict(clip) for clip in clips]

    def get_jobs_summary(self, user_id: Optional[str] = None, is_admin: bool = False) -> Dict[str, Any]:
        """Get summary statistics for jobs
        Admin sees all stats, users see only their own"""
        with get_db_session() as session:
            query = session.query(Job)

            # Apply user filter for non-admin
            if not is_admin and user_id:
                query = query.filter(Job.user_id == user_id)

            # Get counts by status
            total = query.count()
            completed = query.filter(Job.status == "completed").count()
            processing = query.filter(Job.status == "processing").count()
            failed = query.filter(Job.status == "failed").count()
            queued = query.filter(Job.status == "queued").count()

            return {
                "total": total,
                "completed": completed,
                "processing": processing,
                "failed": failed,
                "queued": queued,
                "success_rate": (completed / total * 100) if total > 0 else 0
            }

    def cancel_job(self, job_id: UUID | str, user_id: Optional[str] = None, is_admin: bool = False, **kwargs) -> Dict[str, Any]:
        """Cancel a job
        Only admin or job owner can cancel"""
        # First check if job exists
        job = self.get_job_by_id(job_id, user_id, is_admin)
        if not job:
            return {
                "success": False,
                "job_id": job_id,
                "new_status": "unknown",
                "message": "Job not found or access denied"
            }

        # Check if job can be cancelled
        if job["status"] in ["completed", "cancelled", "failed"]:
            return {
                "success": False,
                "job_id": job_id,
                "new_status": job["status"],
                "message": f"Cannot cancel job with status '{job['status']}'"
            }

        # Try to cancel the job
        success = self.update_job_status(job_id, "cancelled", user_id=user_id, is_admin=is_admin)
        return {
            "success": success,
            "job_id": job_id,
            "new_status": "cancelled" if success else job["status"],
            "message": "Job cancelled successfully" if success else "Failed to cancel job"
        }

    def retry_job(self, job_id: UUID | str, user_id: Optional[str] = None, is_admin: bool = False, **kwargs) -> Dict[str, Any]:
        """Retry a failed job
        Only admin or job owner can retry"""
        # First check if job exists
        job = self.get_job_by_id(job_id, user_id, is_admin)
        if not job:
            return {
                "success": False,
                "job_id": job_id,
                "new_status": "unknown",
                "message": "Job not found or access denied"
            }

        # Check if job can be retried
        if job["status"] != "failed":
            return {
                "success": False,
                "job_id": job_id,
                "new_status": job["status"],
                "message": f"Cannot retry job with status '{job['status']}' - only failed jobs can be retried"
            }

        # Try to retry the job
        success = self.update_job_status(job_id, "queued", progress=0, user_id=user_id, is_admin=is_admin)
        return {
            "success": success,
            "job_id": job_id,
            "new_status": "queued" if success else job["status"],
            "message": "Job queued for retry" if success else "Failed to retry job"
        }

    def get_recent_jobs(self, limit: int = 10, user_id: Optional[str] = None, is_admin: bool = False) -> List[Dict[str, Any]]:
        """Get most recent jobs
        Admin sees all, users see only their own"""
        with get_db_session() as session:
            query = session.query(Job)

            # Apply user filter for non-admin
            if not is_admin and user_id:
                query = query.filter(Job.user_id == user_id)

            jobs = query.order_by(desc(Job.created_at)).limit(limit).all()
            return [self._job_to_dict(job) for job in jobs]

    def get_job_statistics(self, user_id: Optional[str] = None, is_admin: bool = False) -> Dict[str, Any]:
        """Get job statistics for dashboard and analytics
        Admin sees all jobs, users see only their own"""
        try:
            with get_db_session() as session:
                query = session.query(Job)

                # Apply user filter for non-admin
                if not is_admin and user_id:
                    query = query.filter(Job.user_id == user_id)

                # Get all jobs for statistics
                all_jobs = query.all()

                # Calculate statistics
                total_jobs = len(all_jobs)
                completed_jobs = len([job for job in all_jobs if job.status == "completed"])
                failed_jobs = len([job for job in all_jobs if job.status == "failed"])
                processing_jobs = len([job for job in all_jobs if job.status == "processing"])
                pending_jobs = len([job for job in all_jobs if job.status in ["pending", "queued"]])

                # Calculate success rate
                finished_jobs = completed_jobs + failed_jobs
                success_rate = (completed_jobs / finished_jobs * 100) if finished_jobs > 0 else 0

                # Calculate today's jobs - handle timezone properly
                today = date.today()
                todays_jobs = []
                for job in all_jobs:
                    try:
                        job_date = job.created_at.date() if hasattr(job.created_at, 'date') else job.created_at
                        if isinstance(job_date, datetime):
                            job_date = job_date.date()
                        if job_date == today:
                            todays_jobs.append(job)
                    except (AttributeError, TypeError):
                        # Skip jobs with invalid date formats
                        continue

                # Calculate average processing time (mock for now)
                avg_processing_time = 125.5  # TODO: Calculate from actual completion times

                return {
                    "total_jobs": total_jobs,
                    "completed_jobs": completed_jobs,
                    "failed_jobs": failed_jobs,
                    "processing_jobs": processing_jobs,
                    "pending_jobs": pending_jobs,
                    "success_rate": round(success_rate, 2),
                    "todays_jobs": len(todays_jobs),
                    "avg_processing_time": avg_processing_time,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

        except Exception as e:
            logger.error(f"Failed to get job statistics: {e}")
            return {
                "total_jobs": 0,
                "completed_jobs": 0,
                "failed_jobs": 0,
                "processing_jobs": 0,
                "pending_jobs": 0,
                "success_rate": 0,
                "todays_jobs": 0,
                "avg_processing_time": 0,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def create_job(self, job_data: Dict[str, Any], is_admin: bool = False) -> Dict[str, Any]:
        """Create a new job
        Returns created job data"""
        
        with get_db_session() as session:
            # Create new job instance
            job = Job(
                id=uuid4(),
                user_id=job_data.get("user_id", "user1"),
                video_url=job_data.get("video_url", ""),
                video_title=job_data.get("video_title", ""),
                status="queued",
                progress=0,
                current_step="Queued for processing",
                created_at=datetime.now(timezone.utc),
                retry_count=0,
                worker_id=None
            )

            session.add(job)
            session.commit()
            session.refresh(job)

            # V4: Launch workflow via centralized orchestrator
            try:
                logger.info(f"🚀 V4: Starting workflow via orchestrator for job {job.id}")

                # Convert job object naar dict voor workflow
                job_dict = self._job_to_dict(job)

                # Use centralized WorkflowOrchestrator - automatic event dispatching!
                orchestrator = get_workflow_orchestrator()

                # Execute workflow asynchronously via orchestrator using thread executor
                def run_workflow():
                    """Run workflow in new event loop to avoid sync context issues"""
                    import asyncio
                    job_id_str = str(job.id)  # Store job ID before thread
                    try:
                        # Create new event loop for this thread
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                        # Execute workflow
                        result = loop.run_until_complete(
                            orchestrator.execute_workflow(
                                job_id=job_id_str,
                                workflow_type=WorkflowType.VIDEO_PROCESSING,
                                job_data=job_dict
                            )
                        )

                        logger.info(f"✅ V4: Orchestrated workflow completed for job {job_id_str}")
                        return result

                    except Exception as workflow_error:
                        logger.error(f"❌ V4: Workflow execution failed for job {job_id_str}: {workflow_error}")

                        # Update job status to failed in database
                        try:
                            from core.database_manager import Job
                            with get_db_session() as error_session:
                                # Ensure job_id_str is converted to UUID for proper database comparison
                                job_uuid = UUID(job_id_str)
                                error_job = error_session.query(Job).filter(Job.id == job_uuid).first()
                                if error_job:
                                    error_job.status = "failed"
                                    error_job.error_message = f"Workflow failed: {str(workflow_error)}"
                                    error_session.commit()
                        except Exception as db_error:
                            logger.error(f"❌ Failed to update job status after workflow error: {db_error}")
                    finally:
                        loop.close()

                # Start workflow in separate thread to avoid blocking
                import threading
                workflow_thread = threading.Thread(target=run_workflow, daemon=True)
                workflow_thread.start()

                logger.info(f"✅ V4: Orchestrated workflow thread started for job {job.id}")

                # Mark job as processing (orchestrator handles detailed status)
                job.status = "processing"
                job.worker_id = "orchestrator_v4"  # Shortened to fit 50 char limit
                session.commit()

            except Exception as e:
                logger.error(f"❌ V4: Failed to start orchestrated workflow: {e}")
                # Update job status to failed
                job.status = "failed"
                job.error_message = f"Failed to start workflow: {str(e)}"
                session.commit()

            logger.info(f"Created new job {job.id} for user {job.user_id}")
            return self._job_to_dict(job)

    # Helper methods
    def _job_to_dict(self, job: Job) -> Dict[str, Any]:
        """Convert Job model to dictionary"""
        if not job:
            return None

        return {
            "id": str(job.id),
            "user_id": job.user_id,
            "status": job.status,
            "progress": job.progress,
            "video_url": job.video_url,
            "video_title": job.video_title,
            "current_step": job.current_step,
            "error_message": job.error_message,
            "retry_count": job.retry_count,
            "worker_id": job.worker_id,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "updated_at": job.updated_at.isoformat() if getattr(job, "updated_at", None) else (job.created_at.isoformat() if job.created_at else None)
        }

    def _clip_to_dict(self, clip: Clip) -> Dict[str, Any]:
        """Convert Clip model to dictionary"""
        if not clip:
            return None

        return {
            "id": str(clip.id),
            "job_id": str(clip.job_id),
            "clip_number": clip.clip_number,
            "file_path": clip.file_path,
            "thumbnail_path": clip.thumbnail_path,
            "duration": clip.duration,
            "title": clip.title,
            "description": clip.description,
            "tags": clip.tags,
            "file_size": clip.file_size,
            "created_at": clip.created_at.isoformat() if clip.created_at else None
        }
    
    # ==========================================
    # NEW JOB BREAKDOWN METRICS FOR REDESIGN
    # ==========================================
    
    def get_jobs_breakdown(self) -> Dict[str, int]:
        """
        Get complete job counts breakdown by status
        Returns counts for total, completed, failed, processing, pending
        """
        try:
            with get_db_session() as session:
                # Get total job count
                total = session.query(func.count(Job.id)).scalar() or 0
                
                # Get counts by status
                completed = session.query(func.count(Job.id)).filter(Job.status == "completed").scalar() or 0
                failed = session.query(func.count(Job.id)).filter(Job.status == "failed").scalar() or 0
                processing = session.query(func.count(Job.id)).filter(Job.status == "processing").scalar() or 0
                pending = session.query(func.count(Job.id)).filter(Job.status.in_(["pending", "queued"])).scalar() or 0
                
                breakdown = {
                    "total": total,
                    "completed": completed,
                    "failed": failed,
                    "processing": processing,
                    "pending": pending
                }
                
                logger.debug(f"Jobs breakdown: {breakdown}")
                return breakdown
                
        except Exception as e:
            logger.error(f"Failed to get jobs breakdown: {e}")
            return {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "processing": 0,
                "pending": 0
            }
    
    def get_today_jobs_breakdown(self) -> Dict[str, int]:
        """
        Get today's job counts breakdown by status
        Returns counts for jobs created today only
        """
        try:
            with get_db_session() as session:
                today = date.today()
                
                # Get total jobs created today
                total_today = session.query(func.count(Job.id)).filter(
                    func.date(Job.created_at) == today
                ).scalar() or 0
                
                # Get today's counts by status
                completed_today = session.query(func.count(Job.id)).filter(
                    func.date(Job.created_at) == today,
                    Job.status == "completed"
                ).scalar() or 0
                
                failed_today = session.query(func.count(Job.id)).filter(
                    func.date(Job.created_at) == today,
                    Job.status == "failed"
                ).scalar() or 0
                
                processing_today = session.query(func.count(Job.id)).filter(
                    func.date(Job.created_at) == today,
                    Job.status == "processing"
                ).scalar() or 0
                
                pending_today = session.query(func.count(Job.id)).filter(
                    func.date(Job.created_at) == today,
                    Job.status.in_(["pending", "queued"])
                ).scalar() or 0
                
                breakdown = {
                    "total": total_today,
                    "completed": completed_today,
                    "failed": failed_today,
                    "processing": processing_today,
                    "pending": pending_today
                }
                
                logger.debug(f"Today's jobs breakdown: {breakdown}")
                return breakdown
                
        except Exception as e:
            logger.error(f"Failed to get today's jobs breakdown: {e}")
            return {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "processing": 0,
                "pending": 0
            }
