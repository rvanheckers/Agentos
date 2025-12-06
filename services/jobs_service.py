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
import time

# V4 Workflow Integration
# Direct workflow imports - no orchestrator needed
from tasks.video_processing import create_video_processing_workflow

logger = logging.getLogger(__name__)

# simple in-process debounce cache (service-side only; workers updaten zelf via DB)
_last_progress_write: Dict[str, tuple[int, float]] = {}


class JobsService:
    """Central service for all job-related operations"""

    def __init__(self, db_manager = None):
        # ✅ Using shared database pool - no individual connections needed
        pass

    # ----------------------------
    # Progress helpers (optioneel)
    # ----------------------------
    def set_progress_monotonic(self, job_id: UUID | str, pct: int, step: Optional[str] = None,
                               min_delta_pct: int = 1, min_delta_sec: float = 3.0) -> bool:
        """
        Monotone, gedebounce'te progress update. Handig voor routes/admin-actions.
        Workers updaten al direct in de DB; dit is voor API-kant.
        """
        try:
            jid = str(job_id)
            pct = max(0, min(100, int(pct)))
            now = time.time()
            last = _last_progress_write.get(jid)
            if last:
                last_pct, last_ts = last
                if pct < last_pct:
                    pct = last_pct
                if pct == last_pct and (now - last_ts) < min_delta_sec:
                    return False
                if pct - last_pct < min_delta_pct and (now - last_ts) < min_delta_sec:
                    return False

            with get_db_session() as session:
                job_uuid = UUID(jid) if isinstance(job_id, str) else job_id
                job = session.query(Job).filter(Job.id == job_uuid).first()
                if not job:
                    return False
                if job.progress is not None:
                    pct = max(pct, int(job.progress))
                job.progress = pct
                if step:
                    job.current_step = step
                if pct >= 100:
                    job.status = 'completed'
                    job.completed_at = datetime.now(timezone.utc)
                elif pct > 0 and (job.status or '').lower() in ('queued', 'pending', 'created'):
                    job.status = 'processing'
                job.updated_at = datetime.now(timezone.utc)
                session.commit()

            _last_progress_write[jid] = (pct, now)
            return True
        except Exception as e:
            logger.error(f"set_progress_monotonic failed for {job_id}: {e}")
            return False

    # ----------------------------
    # Counts helpers
    # ----------------------------
    def _counts_for_job(self, session, job_uuid: UUID) -> Dict[str, int]:
        """Return both counters: detector vs produced."""
        clips_produced = session.query(func.count(Clip.id)).filter(Clip.job_id == job_uuid).scalar() or 0
        job = session.query(Job).filter(Job.id == job_uuid).first()
        moments_detected = getattr(job, "total_moments", None)
        if moments_detected is None:
            # fallback: if not present, at least surface produced clips
            moments_detected = clips_produced
        return {"moments_detected": int(moments_detected), "clips_produced": int(clips_produced)}

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
            out = []
            for job in jobs:
                enriched = self._job_to_dict(job)
                counts = self._counts_for_job(session, job.id)
                enriched.update(counts)
                out.append(enriched)
            return out

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
                "jobs": [
                    (lambda j: (lambda d, c: (d.update(c) or d))(self._job_to_dict(j), self._counts_for_job(session, j.id)))(job)
                    for job in jobs
                ],
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
            if not job:
                return None
            data = self._job_to_dict(job)
            data.update(self._counts_for_job(session, job.id))
            return data

    def get_job_status(self, job_id: UUID | str, user_id: Optional[str] = None, is_admin: bool = False) -> Optional[Dict[str, str]]:
        """Get job status
        Admin can see any job status, users can only see their own"""
        with get_db_session() as session:
            job_uuid = UUID(job_id) if isinstance(job_id, str) else job_id
            query = session.query(Job).filter(Job.id == job_uuid)
            if not is_admin and user_id:
                query = query.filter(Job.user_id == user_id)
            job = query.first()
            if not job:
                return None
            counts = self._counts_for_job(session, job_uuid)

            # Phase tracking for user selection workflow
            phase = getattr(job, 'phase', 'phase1_analysis')
            moments_available = phase in ['awaiting_selection', 'phase2_generation', 'completed']

            return {
                "job_id": str(job.id),
                "status": job.status,
                "progress": job.progress or 0,
                "updated_at": job.updated_at.isoformat() if getattr(job, "updated_at", None) else (job.created_at.isoformat() if job.created_at else None),
                "moments_detected": counts["moments_detected"],
                "clips_produced": counts["clips_produced"],
                "clips_count": counts["clips_produced"],  # Alias for compatibility
                # NEW: Phase tracking
                "phase": phase,
                "moments_available": moments_available
            }

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
        """Get all clips for a job with processing metadata
        Admin can see any job's clips, users only their own"""
        # First verify job access
        job = self.get_job_by_id(job_id, user_id, is_admin)
        if not job:
            return []

        # Always fetch clips from database first to get metadata
        with get_db_session() as session:
            # Ensure job_id is UUID for proper database comparison
            job_uuid = UUID(job_id) if isinstance(job_id, str) else job_id
            clips = session.query(Clip)\
                          .filter(Clip.job_id == job_uuid)\
                          .order_by(Clip.clip_number)\
                          .all()
            
            if clips:
                # Use database clips with full metadata including processing_metadata
                clip_dicts = []
                for clip in clips:
                    clip_dict = self._clip_to_dict(clip)
                    
                    # Add analysis metadata if processing_metadata exists
                    if clip.processing_metadata:
                        try:
                            import json
                            metadata = json.loads(clip.processing_metadata) if isinstance(clip.processing_metadata, str) else clip.processing_metadata
                            
                            # Structure the analysis data as expected by frontend
                            clip_dict["analysis"] = {
                                "analysis_mode": metadata.get("analysis_mode", "viral_ai"),
                                "keywords": metadata.get("keywords", []),
                                "viral_score": metadata.get("viral_score", 0),
                                "total_moments": metadata.get("total_moments", 0),
                                "video_duration": metadata.get("video_duration", 0),
                                "totalDuration": metadata.get("video_duration", 0),  # Also include for backward compatibility
                                "confidence": metadata.get("confidence", 0.95),
                                "intent": "visual_clips"
                            }
                        except (json.JSONDecodeError, TypeError):
                            # Fallback if metadata is malformed
                            clip_dict["analysis"] = {
                                "analysis_mode": "viral_ai",
                                "keywords": [],
                                "viral_score": 0,
                                "total_moments": 0,
                                "video_duration": 0,
                                "totalDuration": 0,
                                "confidence": 0.95,
                                "intent": "visual_clips"
                            }
                    else:
                        # Default analysis structure if no metadata
                        clip_dict["analysis"] = {
                            "analysis_mode": "viral_ai",
                            "keywords": [],
                            "viral_score": 0,
                            "total_moments": 0,
                            "video_duration": 0,
                            "totalDuration": 0,
                            "confidence": 0.95,
                            "intent": "visual_clips"
                        }
                    
                    clip_dicts.append(clip_dict)
                
                return clip_dicts

        # Fallback: Check if clips exist on disk (legacy approach)
        import os
        import glob
        
        output_dir = f"./io/output/{job_id}"
        if not os.path.exists(output_dir):
            return []
        
        # Read clips from disk (without metadata)
        clip_files = sorted(glob.glob(f"{output_dir}/clip_*.mp4"))
        clips = []
        
        for i, clip_path in enumerate(clip_files):
            # Skip _original files in main listing
            if "_original" in clip_path:
                continue
                
            filename = os.path.basename(clip_path)
            clip_number = filename.replace("clip_", "").replace(".mp4", "")
            
            # Look for corresponding original file
            original_path = clip_path.replace(".mp4", "_original.mp4")
            
            clip_data = {
                "clip_id": i + 1,
                "file_path": clip_path,
                "original_video": original_path if os.path.exists(original_path) else None,
                "cropped_video": clip_path,
                "title": f"Clip {clip_number}",
                "clip_number": int(clip_number) if clip_number.isdigit() else i + 1,
                "duration": 30,  # Default duration
                "job_id": str(job_id),
                "created_at": os.path.getctime(clip_path),
                # Default analysis structure for filesystem-based clips
                "analysis": {
                    "analysis_mode": "viral_ai",
                    "keywords": [],
                    "viral_score": 0,
                    "total_moments": 0,
                    "video_duration": 0,
                    "totalDuration": 0,
                    "confidence": 0.95,
                    "intent": "visual_clips"
                }
            }
            clips.append(clip_data)
        
        return clips

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

            # 🔧 FIX: Move uploaded file to job-specific directory
            # Upload service saves to ./io/input/video_123.mp4
            # But workflow expects ./io/input/{job_id}/video_123.mp4
            import os
            import shutil

            job_id_str = str(job.id)
            video_url = job.video_url

            # Only move if it's a local file (not URL) and not already in job directory
            if video_url and not video_url.startswith(('http://', 'https://')) and job_id_str not in video_url:
                try:
                    video_filename = os.path.basename(video_url)
                    old_path = video_url if os.path.isabs(video_url) else os.path.abspath(video_url)

                    # Create job-specific directory
                    new_dir = os.path.join(os.path.dirname(old_path), job_id_str)
                    os.makedirs(new_dir, exist_ok=True)

                    new_path = os.path.join(new_dir, video_filename)

                    # Move file if it exists
                    if os.path.exists(old_path):
                        shutil.move(old_path, new_path)

                        # Update video_url in database
                        relative_new_path = f"./io/input/{job_id_str}/{video_filename}"
                        job.video_url = relative_new_path
                        session.commit()

                        logger.info(f"✅ Moved uploaded file from {old_path} to {new_path}")
                    else:
                        logger.warning(f"⚠️ Upload file not found at {old_path}, skipping move")

                except Exception as move_error:
                    logger.error(f"❌ Failed to move uploaded file: {move_error}")
                    # Don't fail job creation, workflow will handle missing file

            # Direct workflow execution - no orchestrator needed!
            try:
                logger.info(f"🚀 Starting direct video workflow for job {job.id}")

                # Convert job object naar dict voor workflow
                job_dict = self._job_to_dict(job)
                job_id_str = str(job.id)

                # Create and start video processing workflow directly
                try:
                    logger.error(f"🚨🚨🚨 JOBS_SERVICE: Creating workflow for job {job_id_str}")
                    workflow = create_video_processing_workflow(job_id_str, job_dict)
                    logger.error(f"🚨 JOBS_SERVICE: Workflow created with {len(workflow.tasks)} tasks")
                    logger.error(f"🚨 JOBS_SERVICE: Tasks: {[str(task) for task in workflow.tasks]}")
                    
                    # Start the workflow asynchronously
                    logger.error(f"🚨 JOBS_SERVICE: Calling workflow.apply_async()...")
                    chain_result = workflow.apply_async()
                    logger.error(f"🚨 JOBS_SERVICE: apply_async() returned chain ID: {chain_result.id}")
                    logger.error(f"🚨 JOBS_SERVICE: Chain state: {chain_result.state}")
                    
                    logger.error(f"🚨🚨🚨 Direct video workflow started for job {job_id_str} with chain ID: {chain_result.id}")
                    
                    # Don't wait for completion - workflow runs in background
                    workflow_result = {
                        "success": True,
                        "job_id": job_id_str,
                        "chain_id": chain_result.id,
                        "workflow_type": "video_processing_direct",
                        "message": "Video workflow started successfully"
                    }

                    workflow_result = {"success": True, "chain_id": chain_result.id}

                except Exception as workflow_error:
                    logger.error(f"❌ Direct workflow execution failed for job {job_id_str}: {workflow_error}")
                    
                    # Update job status to failed
                    job.status = "failed"
                    job.error_message = f"Workflow failed: {str(workflow_error)}"
                    session.commit()
                    raise workflow_error

                # Mark job as processing - workflow handles detailed status updates
                job.status = "processing"
                job.worker_id = f"direct_workflow"  
                session.commit()
                
                logger.info(f"✅ Direct workflow started for job {job.id}")

            except Exception as e:
                logger.error(f"❌ Failed to start direct workflow: {e}")
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

        # Determine if moments are available based on phase
        phase = getattr(job, 'phase', 'phase1_analysis')
        moments_available = phase in ['awaiting_selection', 'phase2_generation', 'completed']

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
            "updated_at": job.updated_at.isoformat() if getattr(job, "updated_at", None) else (job.created_at.isoformat() if job.created_at else None),
            # NEW: Phase tracking for user selection workflow
            "phase": phase,
            "moments_available": moments_available
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
            # keep legacy name + modern alias
            "thumbnail_path": clip.thumbnail_path,
            "duration": clip.duration,
            "title": clip.title,
            "description": clip.description,
            "tags": clip.tags,
            "file_size": clip.file_size,
            "created_at": clip.created_at.isoformat() if clip.created_at else None,
            # Face detection and smart cropping data
            "original_video": clip.original_video_path,
            "cropped_video": clip.file_path,  # file_path is the cropped version
            "faces_detected": clip.faces_detected,
            "crop_method": clip.crop_method,
            "processing_metadata": clip.processing_metadata
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

                # Optional: surface global produced/detected aggregates (cheap)
                produced = session.query(func.count(Clip.id)).scalar() or 0
                detected = session.query(func.coalesce(func.sum(Job.total_moments), 0)).scalar() or 0
                # Not returned by default, but handy to log:
                logger.debug(f"Global counts → detected={detected}, produced={produced}")

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
