#!/usr/bin/env python3
"""
Celery Video Processing Tasks
============================

Industry-standard distributed video processing tasks.
Elke agent wordt een Celery task voor parallel execution.

FEATURES:
- Auto-retry met exponential backoff
- Task chaining (workflow execution)
- Progress tracking
- Error handling en recovery
- Resource management

QUEUE ROUTING:
- video_downloader → file_operations queue
- audio_transcriber → transcription queue
- moment_detector → ai_analysis queue
- face_detector → ai_analysis queue
- intelligent_cropper → video_processing queue
- video_cutter → video_processing queue
"""

import os
import sys
import logging
from typing import Dict, Any
from datetime import datetime, timezone

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.celery_app import celery_app
from core.database_manager import PostgreSQLManager
from celery import chain

# V4 Event Integration - Now using centralized orchestrator
from events.dispatcher import dispatcher
from events.workflow_orchestrator import get_workflow_orchestrator, WorkflowType

logger = logging.getLogger(__name__)

# ==============================================================================
# TEST TASKS
# ==============================================================================

@celery_app.task(name='tasks.video_processing.add_numbers')
def add_numbers(x: int, y: int) -> int:
    """Simple test task for Celery functionality"""
    return x + y

# ==============================================================================
# VIDEO PROCESSING WORKFLOW ORCHESTRATION
# ==============================================================================

@celery_app.task(bind=True, name='tasks.video_processing.process_video_workflow_v4')
async def process_video_workflow_v4(self, job_id: str, job_data: Dict[str, Any]):
    """
    V4 Workflow: Uses centralized WorkflowOrchestrator for automatic event dispatching

    VOORDELEN:
    - Automatische event dispatching (geen handmatige code)
    - Consistent error handling
    - Real-time progress tracking
    - Centralized workflow management

    Args:
        job_id: Job UUID
        job_data: Job configuration en metadata

    Returns:
        Workflow execution result via orchestrator
    """
    try:
        logger.info(f"🎬 V4: Starting centralized workflow for job {job_id}")

        # Use centralized orchestrator - automatic event dispatching!
        orchestrator = get_workflow_orchestrator()
        result = await orchestrator.execute_workflow(
            job_id=job_id,
            workflow_type=WorkflowType.VIDEO_PROCESSING,
            job_data=job_data
        )

        logger.info(f"✅ V4: Centralized workflow completed for job {job_id}")
        return result

    except Exception as e:
        logger.error(f"❌ V4: Centralized workflow failed for job {job_id}: {e}")
        raise

@celery_app.task(bind=True, name='tasks.video_processing.process_video_workflow')
def process_video_workflow(self, job_id: str, job_data: Dict[str, Any]):
    """
    Master workflow orchestrator - Industry standard Celery chain approach

    Creates a Celery chain for sequential processing:
    download_video | group(transcribe_audio, detect_faces) | detect_moments | intelligent_crop | cut_videos

    Args:
        job_id: Job UUID
        job_data: Job configuration en metadata

    Returns:
        Chain signature for execution
    """
    try:
        logger.info(f"🎬 V4: Creating video workflow chain for job {job_id}")

        # V4 EVENT DISPATCH: Job processing started
        import asyncio
        try:
            asyncio.create_task(dispatcher.dispatch("job:processing", {
                "job_id": job_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "workflow": "video_processing"
            }))
        except Exception as event_error:
            logger.warning(f"Event dispatch failed: {event_error}")

        # Create workflow chain - FULL AGENT PIPELINE
        workflow = chain(
            # Step 1: Download video
            download_video.s(job_id, job_data),

            # Step 2: Transcribe audio (receives download result)
            transcribe_audio.s(job_id),

            # Step 3: Detect viral moments (receives transcription result)
            detect_moments.s(),

            # Step 4: Detect faces (receives moment result)
            detect_faces.s(),

            # Step 5: Intelligent cropping (receives face result)
            intelligent_crop.s(),

            # Step 6: Cut videos (receives crop result)
            cut_videos.s(),

            # Step 7: Finalize and store clips
            finalize_workflow.s()
        )

        # Execute the chain
        return workflow()

    except Exception as e:
        logger.error(f"❌ Video workflow setup failed for job {job_id}: {e}")
        raise

@celery_app.task(bind=True, name='tasks.video_processing.finalize_workflow')
def finalize_workflow(self, cut_videos_data: Dict[str, Any]):
    """Finalize workflow and update job status in database"""
    try:
        job_id = cut_videos_data.get('job_id')
        logger.info(f"🎬 V4: Finalizing workflow for job {job_id}")

        # Update job status to completed in database
        db = PostgreSQLManager()

        try:
            # Update job to completed status
            with db.get_session() as session:
                from core.database_manager import Job
                job = session.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = 'completed'
                    job.progress = 100
                    job.current_step = 'Completed'
                    job.completed_at = datetime.now(timezone.utc)
                    session.commit()
                    logger.info(f"✅ Job {job_id} marked as completed in database")
                else:
                    logger.warning(f"⚠️ Job {job_id} not found in database")

        except Exception as db_error:
            logger.error(f"❌ Database update failed for job {job_id}: {db_error}")

        # Create clips from cut_videos agent output or fallback to test clips
        try:
            import os
            os.makedirs("./io/output", exist_ok=True)

            clips_created = 0
            with db.get_session() as session:
                from core.database_manager import Clip

                # Check if we should use mock data or real AI
                use_mock_ai = os.getenv('USE_MOCK_AI', 'true').lower() == 'true'

                # Use real clips from cut_videos agent if available
                if not use_mock_ai and cut_videos_data and cut_videos_data.get('success') and cut_videos_data.get('cut_videos'):
                    # Use real clips from video cutting agent
                    real_clips = cut_videos_data['cut_videos']
                    logger.info(f"🎥 Using {len(real_clips)} real clips from video_cutter agent")

                    for i, clip_data in enumerate(real_clips, 1):
                        clip = Clip(
                            job_id=job_id,
                            clip_number=i,
                            file_path=clip_data.get('path', f"./io/output/clip_{job_id}_{i}.mp4"),
                            duration=clip_data.get('duration', 15.0),
                            title=f"🤖 AI: Real Clip #{i}",
                            description=f"🤖 AI-generated clip from {clip_data.get('start_time', 0):.1f}s to {clip_data.get('end_time', 15):.1f}s",
                            tags="ai,real,generated,clip",
                            file_size=clip_data.get('size', 1024*1024*5),
                            thumbnail_path=f"./io/output/thumb_{job_id}_{i}.jpg"
                        )
                        session.add(clip)
                        clips_created += 1

                    # Commit real clips to database
                    session.commit()
                    logger.info(f"✅ Saved {clips_created} real AI clips to database for job {job_id}")

                else:
                    # Either mock mode or AI mode fallback
                    if use_mock_ai:
                        clips_data = [
                            {
                                "clip_number": 1,
                                "file_path": f"./io/output/clip_{job_id}_1.mp4",
                                "duration": 15.5,
                                "title": "🎭 MOCK: Viral Moment #1",
                                "description": "🎭 Mock data - Amazing reaction at 2:30",
                                "tags": "mock,funny,reaction,viral"
                            },
                            {
                                "clip_number": 2,
                                "file_path": f"./io/output/clip_{job_id}_2.mp4",
                                "duration": 12.3,
                                "title": "🎭 MOCK: Best Quote Ever",
                                "description": "🎭 Mock data - Epic quote that went viral",
                                "tags": "mock,quote,epic,trending"
                            },
                            {
                                "clip_number": 3,
                                "file_path": f"./io/output/clip_{job_id}_3.mp4",
                                "duration": 8.7,
                                "title": "🎭 MOCK: Perfect Loop",
                                "description": "🎭 Mock data - Seamless loop for TikTok",
                                "tags": "mock,loop,tiktok,perfect"
                            }
                        ]
                    else:
                        # Fallback to dummy clips when video_cutter fails in AI mode
                        logger.warning(f"⚠️ Video cutting failed or unavailable, using fallback clips for job {job_id}")
                        clips_data = [
                            {
                                "clip_number": 1,
                                "file_path": f"./io/output/clip_{job_id}_1.mp4",
                                "duration": 15.5,
                                "title": "⚠️ AI: Fallback Clip #1",
                                "description": "⚠️ AI-generated fallback - Video cutting failed",
                                "tags": "ai,fallback,error,clip"
                            },
                            {
                                "clip_number": 2,
                                "file_path": f"./io/output/clip_{job_id}_2.mp4",
                                "duration": 12.3,
                                "title": "⚠️ AI: Fallback Clip #2",
                                "description": "⚠️ AI-generated fallback - Video cutting failed",
                                "tags": "ai,fallback,error,clip"
                            },
                            {
                                "clip_number": 3,
                                "file_path": f"./io/output/clip_{job_id}_3.mp4",
                                "duration": 8.7,
                                "title": "⚠️ AI: Fallback Clip #3",
                                "description": "⚠️ AI-generated fallback - Video cutting failed",
                                "tags": "ai,fallback,error,clip"
                            }
                        ]

                    # Process fallback clips (either mock or AI error fallback)
                    logger.info(f"🔍 Environment USE_MOCK_AI: {os.getenv('USE_MOCK_AI')}, use_mock_ai: {use_mock_ai}")

                    for clip_data in clips_data:
                        # Create dummy file for fallback clips (mock or AI error fallback)
                        with open(clip_data["file_path"], "w") as f:
                            if use_mock_ai:
                                f.write(f"🎭 MOCK MODE - Dummy video clip {clip_data['clip_number']} for job {job_id}")
                                logger.info(f"🎭 MOCK: Created dummy clip {clip_data['clip_number']} for job {job_id}")
                            else:
                                f.write(f"⚠️ FALLBACK - Dummy video clip {clip_data['clip_number']} for job {job_id} (video cutting failed)")
                                logger.warning(f"⚠️ FALLBACK: Created dummy clip {clip_data['clip_number']} for job {job_id}")
                        file_size = 1024*1024*5  # 5MB dummy size

                        # Create clip in database
                        clip = Clip(
                            job_id=job_id,
                            clip_number=clip_data["clip_number"],
                            file_path=clip_data["file_path"],
                            duration=clip_data["duration"],
                            title=clip_data["title"],
                            description=clip_data["description"],
                            tags=clip_data["tags"],
                            file_size=file_size,
                            thumbnail_path=f"./io/output/thumb_{job_id}_{clip_data['clip_number']}.jpg"
                        )
                        session.add(clip)
                        clips_created += 1

                    # Commit fallback clips to database
                    session.commit()
                    logger.info(f"✅ Created {clips_created} fallback clips for job {job_id}")

        except Exception as clip_error:
            logger.error(f"❌ Failed to create clips for job {job_id}: {clip_error}")
            clips_created = 0

        # V4 EVENT DISPATCH: Job completed successfully
        import asyncio
        try:
            asyncio.create_task(dispatcher.dispatch("job:completed", {
                "job_id": job_id,
                "clips_created": clips_created,
                "processing_time": 30,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "success": True
            }))
        except Exception as event_error:
            logger.warning(f"Completion event dispatch failed: {event_error}")

        return {
            'success': True,
            'job_id': job_id,
            'clips_count': clips_created,
            'processing_time': 30,
            'cut_videos_data': cut_videos_data
        }

    except Exception as e:
        logger.error(f"❌ V4: Workflow finalization failed for job {job_id}: {e}")

        # V4 EVENT DISPATCH: Job failed
        import asyncio
        try:
            job_id = cut_videos_data.get('job_id') if cut_videos_data else 'unknown'
            asyncio.create_task(dispatcher.dispatch("job:failed", {
                "job_id": job_id,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "stage": "workflow_finalization"
            }))
        except Exception as event_error:
            logger.warning(f"Failure event dispatch failed: {event_error}")

        raise

# ==============================================================================
# INDIVIDUAL AGENT TASKS
# ==============================================================================

@celery_app.task(bind=True, name='tasks.video_processing.download_video', queue='file_operations')
def download_video(self, job_id: str, job_data: Dict[str, Any]):
    """Video download task - routed naar file_operations queue"""
    try:
        # Import hier om circular imports te voorkomen
        from agents2.video_downloader import VideoDownloader

        logger.info(f"🔽 Downloading video for job {job_id}")

        downloader = VideoDownloader()
        result = downloader.download_video({
            'url': job_data['video_url'],
            'output_path': f'./io/input/{job_id}',
            'quality': 'best',
            'format': 'mp4'
        })

        if result['success']:
            logger.info(f"✅ Video downloaded for job {job_id}")

            # Update job progress in database
            try:
                db = PostgreSQLManager()
                with db.get_session() as session:
                    from core.database_manager import Job
                    job = session.query(Job).filter(Job.id == job_id).first()
                    if job:
                        job.status = 'processing'
                        job.progress = 33
                        job.current_step = 'Video downloaded'
                        job.started_at = datetime.now(timezone.utc)
                        session.commit()
                        logger.info(f"✅ Job {job_id} progress updated: video downloaded")
            except Exception as db_error:
                logger.error(f"❌ Database progress update failed for job {job_id}: {db_error}")

            return result
        else:
            logger.error(f"❌ Video download failed for job {job_id}: {result.get('error')}")
            raise Exception(result.get('error', 'Download failed'))

    except Exception as e:
        logger.error(f"❌ Download task failed for job {job_id}: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=3)

@celery_app.task(bind=True, name='tasks.video_processing.transcribe_audio', queue='transcription')
def transcribe_audio(self, download_data: Dict[str, Any], job_id: str):
    """Audio transcription task - routed naar transcription queue"""
    try:
        logger.info(f"🎤 Mock transcription for job {job_id} - video: {download_data.get('title', 'Unknown')}")

        # Update job progress in database
        try:
            db = PostgreSQLManager()
            with db.get_session() as session:
                from core.database_manager import Job
                job = session.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.progress = 66
                    job.current_step = 'Audio transcribed'
                    session.commit()
                    logger.info(f"✅ Job {job_id} progress updated: audio transcribed")
        except Exception as db_error:
            logger.error(f"❌ Database progress update failed for job {job_id}: {db_error}")

        # Mock transcription for testing
        return {
            'success': True,
            'video_path': download_data['video_path'],
            'transcript': f"Mock transcript for {download_data.get('title', 'video')}. This is test transcription data.",
            'job_id': job_id,
            'duration': download_data.get('duration', 0)
        }

    except Exception as e:
        logger.error(f"❌ Transcription task failed for job {job_id}: {e}")
        raise self.retry(exc=e, countdown=30, max_retries=2)

@celery_app.task(bind=True, name='tasks.video_processing.detect_faces', queue='ai_analysis')
def detect_faces(self, moment_data: Dict[str, Any]):
    """Face detection task - routed naar ai_analysis queue"""
    try:

        job_id = moment_data.get('job_id')
        video_path = moment_data.get('video_path')
        logger.info(f"👤 Detecting faces for job {job_id}")

        # Face detection is currently for images only
        # Return mock face data for video pipeline
        result = {
            'success': True,
            'faces_detected': 1,
            'faces': [{
                'confidence': 0.9,
                'center_x': 0.5,
                'center_y': 0.5,
                'tracking': 'Mock face tracking data for video'
            }],
            'method_used': 'mock_video'
        }

        if result['success']:
            logger.info(f"✅ Faces detected for job {job_id}")
            # Pass along data for next task
            result['job_id'] = job_id
            result['video_path'] = video_path or moment_data.get('video_path')
            result['moments'] = moment_data.get('moments', [])
            return result
        else:
            raise Exception(result.get('error', 'Face detection failed'))

    except Exception as e:
        job_id = moment_data.get('job_id', 'unknown')
        logger.error(f"❌ Face detection task failed for job {job_id}: {e}")
        raise self.retry(exc=e, countdown=30, max_retries=2)

@celery_app.task(bind=True, name='tasks.video_processing.detect_moments', queue='ai_analysis')
def detect_moments(self, transcription_data: Dict[str, Any]):
    """Moment detection task - routed naar ai_analysis queue"""
    try:
        from agents2.moment_detector import MomentDetector

        job_id = transcription_data.get('job_id')
        logger.info(f"⚡ Detecting moments for job {job_id}")

        detector = MomentDetector()
        result = detector.detect_moments({
            'video_path': transcription_data['video_path'],
            'transcript': transcription_data['transcript'],
            'output_types': ['viral', 'key_highlights', 'summary']
        })

        if result['success']:
            logger.info(f"✅ Moments detected for job {job_id}")
            # Add job_id and video_path to result for next task in chain
            result['job_id'] = job_id
            result['video_path'] = transcription_data['video_path']
            return result
        else:
            raise Exception(result.get('error', 'Moment detection failed'))

    except Exception as e:
        job_id = transcription_data.get('job_id', 'unknown')
        logger.error(f"❌ Moment detection task failed for job {job_id}: {e}")
        raise self.retry(exc=e, countdown=30, max_retries=2)

@celery_app.task(bind=True, name='tasks.video_processing.intelligent_crop', queue='video_processing')
def intelligent_crop(self, face_data: Dict[str, Any]):
    """Intelligent cropping task - routed naar video_processing queue"""
    try:
        from agents2.intelligent_cropper import IntelligentCropper

        job_id = face_data.get('job_id')
        video_path = face_data.get('video_path')
        moments = face_data.get('moments', [])
        logger.info(f"✂️ Intelligent cropping for job {job_id}")

        cropper = IntelligentCropper()
        result = cropper.calculate_crop({
            'video_path': video_path,
            'face_coordinates': face_data.get('faces', []),
            'moments': moments,
            'target_formats': ['16:9', '9:16', '1:1']
        })

        if result['success']:
            logger.info(f"✅ Intelligent cropping completed for job {job_id}")
            # Pass along data for next task
            result['job_id'] = job_id
            result['video_path'] = video_path
            result['moments'] = moments
            return result
        else:
            raise Exception(result.get('error', 'Intelligent cropping failed'))

    except Exception as e:
        job_id = face_data.get('job_id', 'unknown')
        logger.error(f"❌ Intelligent cropping task failed for job {job_id}: {e}")
        raise self.retry(exc=e, countdown=30, max_retries=2)

@celery_app.task(bind=True, name='tasks.video_processing.cut_videos', queue='video_processing')
def cut_videos(self, crop_data: Dict[str, Any]):
    """Video cutting task - routed naar video_processing queue"""
    try:
        from agents2.video_cutter import VideoCutter

        job_id = crop_data.get('job_id')
        video_path = crop_data.get('video_path')
        moments = crop_data.get('moments', [])
        logger.info(f"🎬 Cutting videos for job {job_id}")

        # Convert moments to cuts for video cutter
        cuts = []
        for i, moment in enumerate(moments[:3]):  # Max 3 clips
            cuts.append({
                'start_time': moment.get('start_time', i * 20),
                'end_time': moment.get('end_time', (i * 20) + 15),
                'output_name': f'clip_{i+1}'
            })

        cutter = VideoCutter()
        result = cutter.cut_video({
            'video_path': video_path,
            'cuts': cuts,
            'output_path': f'./io/output/{job_id}'
        })

        if result['success']:
            logger.info(f"✅ Video cutting completed for job {job_id}")
            # Pass along data for finalize task
            result['job_id'] = job_id
            return result
        else:
            raise Exception(result.get('error', 'Video cutting failed'))

    except Exception as e:
        job_id = crop_data.get('job_id', 'unknown')
        logger.error(f"❌ Video cutting task failed for job {job_id}: {e}")
        raise self.retry(exc=e, countdown=60, max_retries=2)

# ==============================================================================
# UTILITY TASKS
# ==============================================================================

@celery_app.task(name='tasks.video_processing.cleanup_temp_files')
def cleanup_temp_files(job_id: str):
    """Cleanup temporary files voor een job"""
    try:
        import shutil
        temp_dir = f"/tmp/agentos_{job_id}"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"🧹 Cleaned up temp files for job {job_id}")
    except Exception as e:
        logger.error(f"❌ Cleanup failed for job {job_id}: {e}")
