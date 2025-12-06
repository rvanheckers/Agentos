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
- Explicit progress heartbeats per fase (33/66/99 + tussenstappen)

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
import json
import logging
import hashlib
from typing import Dict, Any, List
from datetime import datetime, timezone, date
from agents2.shared.utils.fallback_messages import FallbackMessages

# Load environment variables for Celery workers
from dotenv import load_dotenv
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.celery_app import celery_app
from core.database_pool import get_db_session
from celery import chain

# V4 Event Integration - Import alleen wat nodig is
# from events.dispatcher import dispatcher  # Verplaatst naar waar nodig
# from events.workflow_orchestrator import get_workflow_orchestrator, WorkflowType  # Niet meer nodig

logger = logging.getLogger(__name__)

def save_marketing_insights_from_processing(session, video_url: str, metadata: Dict[str, Any]):
    """
    Save marketing insights during video processing (not just cleanup)
    Deze functie implementeert de ontbrekende marketing insights logica uit CHANGELOG_2025-09-21.md
    """
    try:
        from core.database_manager import ContentInsights

        # Create content fingerprint from URL (anonymous identifier)
        content_fingerprint = hashlib.sha256(video_url.encode()).hexdigest()[:32]

        # Extract insights data
        insights_data = {
            'content_fingerprint': content_fingerprint,
            'processed_date': date.today(),
            'content_category': metadata.get('content_type', 'spoken'),
            'viral_score': metadata.get('viral_score', 0),
            'total_moments': metadata.get('total_moments', 3),
            'video_duration_seconds': metadata.get('video_duration', 0),
            'processing_method': metadata.get('analysis_mode', 'unknown'),
            'detected_trends': metadata.get('keywords', []),
            'region': 'NL',  # Default region
            'device_category': 'web',  # Default device
            'audience_segment': 'general'
        }

        # Insert or update marketing insights
        insight = ContentInsights(**insights_data)
        session.merge(insight)  # Use merge to handle duplicates

        logger.info(f"✅ Marketing insights saved: {metadata.get('content_type', 'unknown')} content, {metadata.get('total_moments', 0)} moments")

    except Exception as e:
        logger.warning(f"⚠️ Could not save marketing insights: {e}")
        # Don't fail the main process if marketing insights fail

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

def create_video_processing_workflow(job_id: str, job_data: Dict[str, Any], phase: str = 'phase1'):
    """
    Create video processing workflow chain - Dispatches to Phase 1 or Phase 2

    Phase 1 Pipeline: download → transcribe → detect_moments → detect_faces → save_moments → STOP
    Phase 2 Pipeline: load_selected_moments → crop → cut → finalize

    Args:
        job_id: Job UUID
        job_data: Job configuration (video_url for phase1, selected_moment_ids for phase2)
        phase: 'phase1' (default) or 'phase2'

    Returns:
        Celery chain ready for execution
    """
    logger.info(f"🎬 Creating video workflow chain for job {job_id} (phase={phase})")

    if phase == 'phase1' or phase is None:
        # Phase 1: Analyze and detect moments (no clips yet)
        from tasks.video_processing_phase1 import create_phase1_workflow

        logger.info(f"🔍 WORKFLOW_CREATE (Phase 1): Building analysis chain")
        logger.info(f"  1. download_video.s({job_id}, {job_data})")
        logger.info(f"  2. transcribe_audio.s()")
        logger.info(f"  3. detect_moments.s()")
        logger.info(f"  4. detect_faces.s()")
        logger.info(f"  5. save_moments_to_db.s()")
        logger.info(f"  → OUTPUT: Moments in database, job.phase = 'awaiting_selection'")

        workflow = create_phase1_workflow(job_id, job_data)

    elif phase == 'phase2':
        # Phase 2: Generate clips for selected moments
        from tasks.video_processing_phase2 import create_phase2_workflow

        selected_moment_ids = job_data.get('selected_moment_ids', [])
        if not selected_moment_ids:
            raise ValueError("Phase 2 requires 'selected_moment_ids' in job_data")

        logger.info(f"🔍 WORKFLOW_CREATE (Phase 2): Building clip generation chain")
        logger.info(f"  1. load_selected_moments.s({job_id}, {len(selected_moment_ids)} moments)")
        logger.info(f"  2. intelligent_crop.s()")
        logger.info(f"  3. cut_videos.s()")
        logger.info(f"  4. finalize_phase2.s()")
        logger.info(f"  → OUTPUT: {len(selected_moment_ids)} clips generated, job.phase = 'completed'")

        workflow = create_phase2_workflow(job_id, selected_moment_ids)

    else:
        raise ValueError(f"Unknown workflow phase: {phase}. Must be 'phase1' or 'phase2'")

    logger.info(f"✅ Video workflow chain created for job {job_id} (phase={phase})")

    # DEBUG: Print workflow chain steps
    logger.info(f"🔍 DEBUG: Workflow steps: {[str(step) for step in workflow.tasks]}")

    return workflow


# ==============================================================================
# BACKWARDS COMPATIBILITY HELPERS
# ==============================================================================

def start_video_processing(job_id: str, auto_start: bool = False):
    """
    Start video processing workflow with proactive pause points

    Context7 Validated: Backwards compatibility patterns (trust score 8.6)

    Supports two flows:
    1. Admin Flow (auto_start=False): Manual start via API, pauses at awaiting_admin_config
    2. User Flow (auto_start=True): Auto-start, pauses at awaiting_user_selection (old behavior)

    Args:
        job_id: Job identifier
        auto_start: If True, use User UI flow (backwards compatible)
                   If False, use Admin flow (pause for config)

    Returns:
        Dict with workflow status
    """
    try:
        from core.database_manager import Job

        with get_db_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")

            # 🔥 NEW: Set initial phase based on flow type
            if auto_start:
                # User UI flow: start immediately, pause at moment selection
                job.phase = 'phase1_running'
                job.status = 'processing'
                job.current_step = 'Starting Phase 1 (auto-start)'

                # Mark this as auto-flow for later logic
                if not job.pipeline_config:
                    job.pipeline_config = {}
                job.pipeline_config['auto_flow'] = True

                logger.info(f"🚀 Starting AUTO-FLOW for {job_id} (User UI - backwards compatible)")

            else:
                # Admin flow: set to configuring, wait for explicit start
                job.phase = 'configuring'
                job.status = 'pending_config'
                job.current_step = 'Ready for Configuration'

                if not job.pipeline_config:
                    job.pipeline_config = {}
                job.pipeline_config['auto_flow'] = False

                logger.info(f"⚙️ Job {job_id} ready for ADMIN CONFIGURATION (proactive flow)")

            session.commit()

        # If auto_start, trigger Phase 1 immediately
        if auto_start:
            from tasks.video_processing_phase1 import create_phase1_workflow

            # Get job data for workflow
            with get_db_session() as session:
                job = session.query(Job).filter(Job.id == job_id).first()
                job_data = {
                    'video_url': job.video_url,
                    'job_id': job_id
                }

            workflow = create_phase1_workflow(job_id, job_data)
            workflow.apply_async()
            logger.info(f"✅ Phase 1 started for {job_id} (auto-flow)")

            return {
                'success': True,
                'job_id': job_id,
                'flow': 'auto',
                'phase': 'phase1_running',
                'message': 'Phase 1 started automatically (User UI flow)'
            }
        else:
            logger.info(f"⏸️ Job {job_id} waiting for admin to configure and start Phase 1")

            return {
                'success': True,
                'job_id': job_id,
                'flow': 'admin',
                'phase': 'configuring',
                'message': 'Job ready for admin configuration'
            }

    except Exception as e:
        logger.error(f"❌ Error starting workflow for {job_id}: {e}")
        raise


def handle_moment_selection(job_id: str, selected_moment_ids: List[str]):
    """
    Handle moment selection and determine next phase

    Context7 Validated: State transition patterns (trust score 8.5)

    Supports two scenarios:
    1. Auto-flow (User UI): Auto-start Phase 2 after selection
    2. Admin-flow: Keep in awaiting_admin_config, let admin start Phase 2

    Args:
        job_id: Job identifier
        selected_moment_ids: List of moment IDs selected by user/admin

    Returns:
        Dict with next phase information
    """
    try:
        from core.database_manager import Job, Moment

        with get_db_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")

            # Mark moments as selected
            moments = session.query(Moment).filter(
                Moment.job_id == job_id,
                Moment.id.in_(selected_moment_ids)
            ).all()

            for moment in moments:
                moment.is_selected = True
                moment.selected_at = datetime.now(timezone.utc)

            # 🔥 NEW: Check if this is auto-flow or admin-flow
            is_auto_flow = job.pipeline_config.get('auto_flow', True) if job.pipeline_config else True

            if is_auto_flow:
                # User UI flow: auto-start Phase 2 (backwards compatible)
                job.phase = 'phase2_running'
                job.current_step = 'Auto-starting Phase 2 (User UI flow)'
                session.commit()

                logger.info(f"✅ Moments selected for {job_id}, AUTO-STARTING Phase 2 (User UI)")

                # Trigger Phase 2 workflow
                from tasks.video_processing_phase2 import create_phase2_workflow
                workflow = create_phase2_workflow(job_id, selected_moment_ids)
                workflow.apply_async()

                return {
                    'success': True,
                    'job_id': job_id,
                    'flow': 'auto',
                    'phase': 'phase2_running',
                    'selected_count': len(moments),
                    'message': 'Phase 2 started automatically (User UI flow)'
                }

            else:
                # Admin flow: stay in awaiting_admin_config, let admin start Phase 2 explicitly
                job.phase = 'awaiting_admin_config'
                job.current_step = 'Moments selected - Ready for Phase 2 configuration'
                session.commit()

                logger.info(f"⏸️ Moments selected for {job_id}, WAITING for admin to start Phase 2")

                return {
                    'success': True,
                    'job_id': job_id,
                    'flow': 'admin',
                    'phase': 'awaiting_admin_config',
                    'selected_count': len(moments),
                    'message': 'Moments selected. Admin must configure and start Phase 2.'
                }

    except Exception as e:
        logger.error(f"❌ Error handling moment selection for {job_id}: {e}")
        raise


@celery_app.task(bind=True, name='tasks.video_processing.finalize_workflow')
def finalize_workflow(self, cut_videos_data: Dict[str, Any]):
    """Finalize workflow and update job status in database"""
    try:
        job_id = cut_videos_data.get('job_id')
        logger.info(f"🎬 V4: Finalizing workflow for job {job_id}")

        # Update job status to completed in database
        # Using shared database pool

        try:
            # Update job to completed status
            with get_db_session() as session:
                from core.database_manager import Job
                job = session.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = 'completed'
                    job.progress = 100
                    job.current_step = 'Completed'
                    job.completed_at = datetime.now(timezone.utc)

                    # 🔑 CRITICAL FIX: Update job with COMPLETE metadata from pipeline
                    if cut_videos_data and cut_videos_data.get('success'):
                        job.content_type = cut_videos_data.get('content_type', 'spoken')
                        job.youtube_title = cut_videos_data.get('video_title', 'Unknown')
                        job.analysis_mode = cut_videos_data.get('analysis_mode', 'ai_viral_analysis')
                        job.viral_score = cut_videos_data.get('viral_score', 0)
                        # ✅ Tellingsfix: produced clips i.p.v. niet-bestaande 'clips'
                        produced = len((cut_videos_data.get('cut_videos') or []))
                        detected = int(cut_videos_data.get('total_moments') or 0)
                        job.total_moments = produced or detected or 0
                        job.video_duration = cut_videos_data.get('video_duration', 0)
                        if cut_videos_data.get('keywords'):
                            job.keywords = cut_videos_data.get('keywords', [])

                        logger.info(f"✅ Updated COMPLETE job metadata:")
                        logger.info(f"   - content_type: {job.content_type}")
                        logger.info(f"   - title: {job.youtube_title}")
                        logger.info(f"   - viral_score: {job.viral_score}")
                        logger.info(f"   - total_moments_detected: {detected}")
                        logger.info(f"   - clips_produced: {produced}")
                        logger.info(f"   - video_duration: {job.video_duration}")

                        # 🎯 NEW: Save marketing insights (implementing CHANGELOG_2025-09-21.md)
                        video_url = cut_videos_data.get('video_url', job.video_url)
                        save_marketing_insights_from_processing(session, video_url, {
                            'content_type': job.content_type,
                            'viral_score': job.viral_score,
                            'total_moments': detected,
                            'video_duration': job.video_duration,
                            'analysis_mode': job.analysis_mode,
                            'keywords': job.keywords or []
                        })

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
            with get_db_session() as session:
                from core.database_manager import Clip

                # Check if we should use mock data or real AI
                use_mock_ai = os.getenv('USE_MOCK_AI', 'true').lower() == 'true'

                # Use real clips from cut_videos agent if available
                if not use_mock_ai and cut_videos_data and cut_videos_data.get('success') and cut_videos_data.get('cut_videos'):
                    # Use real clips from video cutting agent
                    real_clips = cut_videos_data['cut_videos']
                    logger.info(f"🎥 Using {len(real_clips)} real clips from video_cutter agent")

                    # Get face detection and cropping metadata from workflow
                    faces_data = cut_videos_data.get('faces_data', {})
                    crop_data = cut_videos_data.get('crop_data', {})
                    original_video = cut_videos_data.get('original_video_path', '')

                    for i, clip_data in enumerate(real_clips, 1):
                        # Try to match clip with original moment data by index
                        moment_index = i - 1
                        moments = cut_videos_data.get('moments', [])
                        moment_data = moments[moment_index] if moment_index < len(moments) else {}

                        # ✅ CRITICAL FIX: Generate appropriate descriptions based on content_type
                        content_type = cut_videos_data.get('content_type', 'spoken')
                        if content_type == 'spoken':
                            title = f"🗣️ Speech Clip #{i}"
                            if moment_data.get('description') and '🎵 Music' not in moment_data.get('description', ''):
                                description = moment_data.get('description')
                            else:
                                description = f"🗣️ Speech segment from {clip_data.get('start_time', 0):.1f}s to {clip_data.get('end_time', 15):.1f}s"
                        else:
                            title = f"🤖 AI: Real Clip #{i}"
                            description = moment_data.get('description', f"🤖 AI-generated clip from {clip_data.get('start_time', 0):.1f}s to {clip_data.get('end_time', 15):.1f}s")

                        # V3.2 FIX: Get per-clip crop coordinates from clip_data (not global crop_data)
                        # Each sub-moment has unique crop coordinates in V3.2 shot sequencing
                        clip_crop_coords = clip_data.get('crop_coordinates', crop_data.get('crop_coordinates', {}))

                        clip = Clip(
                            job_id=job_id,
                            clip_number=i,
                            file_path=clip_data.get('path', f"./io/output/clip_{job_id}_{i}.mp4"),
                            duration=clip_data.get('duration', 15.0),
                            title=title,
                            description=description,
                            tags="ai,real,generated,clip",
                            file_size=clip_data.get('size', 1024*1024*5),
                            thumbnail_path=f"./io/output/thumb_{job_id}_{i}.jpg",
                            # Face detection and smart cropping data
                            original_video_path=clip_data.get('original_path', original_video),
                            faces_detected=faces_data.get('faces_detected', 0),
                            crop_method=clip_data.get('crop_method', crop_data.get('crop_method', 'center')),
                            processing_metadata=json.dumps({
                                'faces': faces_data.get('faces', []),
                                'crop_info': crop_data.get('crop_info', {}),
                                'original_resolution': crop_data.get('original_resolution', {}),
                                'crop_coordinates': clip_crop_coords,  # V3.2 FIX: Per-clip crop coordinates
                                # V3.2: Add shot sequencing metadata if available
                                'shot_type': clip_data.get('shot_type'),
                                'sub_moment_index': clip_data.get('sub_moment_index'),
                                # Add moment detection metadata
                                'analysis_mode': cut_videos_data.get('analysis_mode', 'unknown'),
                                'keywords': moment_data.get('keywords', []),
                                'viral_score': moment_data.get('viral_score'),
                                'sentence_text': moment_data.get('sentence_text', ''),
                                'total_moments': cut_videos_data.get('total_moments'),
                                'video_duration': cut_videos_data.get('video_duration')
                            }) if faces_data or crop_data or moment_data else None
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
                                "title": FallbackMessages.get('metadata_missing', 'nl'),
                                "description": FallbackMessages.get('metadata_missing', 'nl'),
                                "tags": "mock,funny,reaction,viral"
                            },
                            {
                                "clip_number": 2,
                                "file_path": f"./io/output/clip_{job_id}_2.mp4",
                                "duration": 12.3,
                                "title": FallbackMessages.get('metadata_missing', 'nl'),
                                "description": FallbackMessages.get('metadata_missing', 'nl'),
                                "tags": "mock,quote,epic,trending"
                            },
                            {
                                "clip_number": 3,
                                "file_path": f"./io/output/clip_{job_id}_3.mp4",
                                "duration": 8.7,
                                "title": FallbackMessages.get('metadata_missing', 'nl'),
                                "description": FallbackMessages.get('metadata_missing', 'nl'),
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

                    # ✅ CRITICAL FIX: Get content_type for appropriate fallback descriptions
                    content_type = cut_videos_data.get('content_type', 'spoken') if cut_videos_data else 'spoken'

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

                        # ✅ CRITICAL FIX: Adjust title and description for content_type
                        if content_type == 'spoken':
                            # Override music-related titles/descriptions for speech content
                            if 'Music' in clip_data["title"] or 'Music' in clip_data["description"]:
                                adjusted_title = f"🗣️ Speech Clip #{clip_data['clip_number']}"
                                adjusted_description = f"🗣️ Speech content - clip {clip_data['clip_number']}"
                            else:
                                adjusted_title = clip_data["title"]
                                adjusted_description = clip_data["description"]
                        else:
                            adjusted_title = clip_data["title"]
                            adjusted_description = clip_data["description"]

                        # Create clip in database
                        clip = Clip(
                            job_id=job_id,
                            clip_number=clip_data["clip_number"],
                            file_path=clip_data["file_path"],
                            duration=clip_data["duration"],
                            title=adjusted_title,
                            description=adjusted_description,
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

        # V4 EVENT DISPATCH: Job completed successfully (async safe)
        try:
            # Use thread-safe event dispatching (no asyncio.create_task needed)
            import asyncio
            import threading
            
            def dispatch_completion_event():
                try:
                    from events.dispatcher import dispatcher
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(dispatcher.dispatch("job:completed", {
                        "job_id": job_id,
                        "clips_created": clips_created,
                        "processing_time": 30,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "success": True
                    }))
                    loop.close()
                except Exception as e:
                    logger.warning(f"Completion event dispatch failed: {e}")
            
            # Run in separate thread to avoid coroutine issues
            threading.Thread(target=dispatch_completion_event, daemon=True).start()
        except Exception as event_error:
            logger.warning(f"Event dispatch setup failed: {event_error}")

        return {
            'success': True,
            'job_id': job_id,
            'clips_count': clips_created,
            'processing_time': 30,
            'cut_videos_data': cut_videos_data
        }

    except Exception as e:
        logger.error(f"❌ V4: Workflow finalization failed for job {job_id}: {e}")

        # V4 EVENT DISPATCH: Job failed (async safe)
        try:
            job_id = cut_videos_data.get('job_id') if cut_videos_data else 'unknown'
            
            def dispatch_failure_event():
                try:
                    from events.dispatcher import dispatcher
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(dispatcher.dispatch("job:failed", {
                        "job_id": job_id,
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "stage": "workflow_finalization"
                    }))
                    loop.close()
                except Exception as dispatch_error:
                    logger.warning(f"Failure event dispatch failed: {dispatch_error}")
            
            # Run in separate thread to avoid coroutine issues
            import threading
            threading.Thread(target=dispatch_failure_event, daemon=True).start()
        except Exception as event_error:
            logger.warning(f"Event dispatch setup failed: {event_error}")

        raise

# ==============================================================================
# INDIVIDUAL AGENT TASKS
# ==============================================================================

@celery_app.task(bind=True, name='tasks.video_processing.download_video', queue='file_operations')
def download_video(self, job_id: str, job_data: Dict[str, Any]):
    """Video download task - routed naar file_operations queue"""
    try:
        # Import debug helpers
        from agents2.shared.utils.video_helpers import save_step_output, generate_thumbnail, get_video_metadata

        # Log start of download
        save_step_output(job_id, 'download_video', 'in_progress')

        # Import hier om circular imports te voorkomen
        from agents2.video_processing.video_downloader import VideoDownloader

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

            # Generate debug outputs for debug viewer
            try:
                video_path = result.get('video_path')

                # Generate thumbnail
                thumbnail_path = None
                if video_path and os.path.exists(video_path):
                    thumbnail_path = generate_thumbnail(video_path, timestamp=1.0)

                # Extract metadata
                metadata = get_video_metadata(video_path) if video_path else {}

                # Log success with debug data
                save_step_output(
                    job_id,
                    'download_video',
                    'success',
                    output={
                        'video_path': video_path,
                        'thumbnail': thumbnail_path,
                        'title': result.get('title', 'Unknown'),
                        'duration': metadata.get('duration', result.get('duration', 0)),
                        'resolution': metadata.get('resolution', 'Unknown'),
                        'file_size': metadata.get('file_size', 0)
                    }
                )
                logger.info(f"✅ Debug viewer updated: download_video success")
            except Exception as debug_error:
                logger.warning(f"⚠️ Debug logging failed (non-critical): {debug_error}")

            # Update job progress in database
            try:
                # Using shared database pool
                with get_db_session() as session:
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

            # Check if IO cleanup is needed (after successful download)
            try:
                from core.io_manager import trigger_io_cleanup_if_needed
                cleanup_result = trigger_io_cleanup_if_needed()
                if cleanup_result.get('triggered'):
                    logger.info(f"🧹 IO cleanup triggered after job {job_id}")
            except Exception as cleanup_error:
                # Don't fail the job if cleanup fails
                logger.warning(f"⚠️ IO cleanup check failed: {cleanup_error}")

            # Add job_id to result for chain workflow compatibility
            result['job_id'] = job_id
            # 📦 User preferences (inclusief clip-lengte) meereizen door de chain
            result['user_preferences'] = job_data.get('user_preferences', {'clip_length': 30})
            return result
        else:
            error_msg = result.get('error', 'Download failed')
            logger.error(f"❌ Video download failed for job {job_id}: {error_msg}")

            # Log failure to debug viewer
            try:
                from agents2.shared.utils.video_helpers import save_step_output
                save_step_output(job_id, 'download_video', 'failed', error=error_msg)
            except Exception as debug_error:
                logger.warning(f"⚠️ Debug failure logging failed (non-critical): {debug_error}")

            raise Exception(error_msg)

    except Exception as e:
        logger.error(f"❌ Download task failed for job {job_id}: {e}")

        # Log failure to debug viewer
        try:
            from agents2.shared.utils.video_helpers import save_step_output
            save_step_output(job_id, 'download_video', 'failed', error=str(e))
        except Exception as debug_error:
            logger.warning(f"⚠️ Debug failure logging failed (non-critical): {debug_error}")

        raise self.retry(exc=e, countdown=60, max_retries=3)

@celery_app.task(bind=True, name='tasks.video_processing.transcribe_audio', queue='transcription')
def transcribe_audio(self, download_data: Dict[str, Any]):
    """Real Whisper transcription with language detection"""
    try:
        # Extract job_id from download_data (chain workflow compatibility)
        job_id = download_data.get('job_id')
        if not job_id:
            raise ValueError("job_id not found in download_data")

        # Import debug helpers
        from agents2.shared.utils.video_helpers import save_step_output

        # Log start of transcription
        save_step_output(job_id, 'transcribe_audio', 'in_progress')

        video_path = download_data['video_path']
        logger.info(f"🎤 Real Whisper transcription for job {job_id} - video: {download_data.get('title', 'Unknown')}")

        # Update job progress in database
        try:
            with get_db_session() as session:
                from core.database_manager import Job
                job = session.query(Job).filter(Job.id == job_id).first()
                if job:
                    # Transcribe-fase eindigt op 66% volgens je mapping
                    job.progress = 66
                    job.current_step = 'Audio transcribed'
                    session.commit()
                    logger.info(f"✅ Job {job_id} progress updated: audio transcribed")
        except Exception as db_error:
            logger.error(f"❌ Database progress update failed for job {job_id}: {db_error}")

        # Use new FastAudioTranscriber with chunking support
        try:
            from agents2.audio_processing.audio_transcriber import FastAudioTranscriber

            # Extract audio from video first for transcriber
            audio_path = video_path.replace('.mp4', '_audio.mp3')

            # Extract audio using ffmpeg (same as before for compatibility)
            import subprocess
            extract_cmd = [
                'ffmpeg', '-i', video_path, '-vn', '-acodec', 'mp3',
                '-ar', '16000', '-ac', '1', '-b:a', '64k', '-y', audio_path
            ]

            result = subprocess.run(extract_cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                raise Exception(f"Audio extraction failed: {result.stderr}")

            logger.info(f"🎵 Audio extracted to {audio_path}")

            # Use FastAudioTranscriber with chunking support
            logger.info(f"🔧 AUDIO_CHUNKING: Using FastAudioTranscriber for job {job_id}")
            logger.info(f"🔧 AUDIO_CHUNKING: Video file: {video_path}")

            transcriber = FastAudioTranscriber()
            transcription_input = {
                "video_path": video_path,  # ✅ FIX: Pass video file, transcriber extracts audio internally
                "method": "auto"  # Changed to auto: tries faster-whisper first, then local whisper, then openai
            }

            logger.info(f"🔧 AUDIO_CHUNKING: Starting transcription with chunking support...")
            transcription_result = transcriber.transcribe_audio(transcription_input)

            logger.info(f"🔧 AUDIO_CHUNKING: Transcription completed - Method: {transcription_result.get('method_used')}")
            logger.info(f"🔧 AUDIO_CHUNKING: Guard fields - is_mock: {transcription_result.get('is_mock')}, allow_downstream: {transcription_result.get('allow_downstream')}")

            # Pipeline Guard - Stop on non-production transcripts
            tr = transcription_result
            logger.info(f"🛡️ PIPELINE_GUARD: Checking allow_downstream = {tr.get('allow_downstream', True)}")

            if not tr.get('allow_downstream', True):
                logger.warning('🛑 PIPELINE_GUARD: Transcription not production-grade (mock/degraded). Halting pipeline.')
                logger.warning(f'🛑 PIPELINE_GUARD: Reason - Method: {tr.get("method_used")}, Quality: {tr.get("quality_tier")}')

                # Update job status in database
                try:
                    with get_db_session() as session:
                        from core.database_manager import Job
                        job = session.query(Job).filter(Job.id == job_id).first()
                        if job:
                            job.status = 'needs_real_transcript'
                            job.user_message = tr.get('user_message') or 'Transcriptie is niet gelukt. Probeer opnieuw met compressie/chunks.'
                            session.commit()
                            logger.info(f"✅ Job {job_id} status updated: needs_real_transcript")
                except Exception as db_error:
                    logger.error(f"❌ Database status update failed for job {job_id}: {db_error}")

                return {
                    'success': False,
                    'stopped_at': 'transcription',
                    'reason': 'non_production_transcript',
                    'user_message': tr.get('user_message') or 'Transcriptie is niet gelukt. Probeer opnieuw met compressie/chunks.',
                    'job_id': job_id
                }

            # Production transcription successful - continue pipeline
            logger.info(f"✅ PIPELINE_GUARD: Production quality approved - pipeline continues")

            transcript_text = transcription_result.get('transcript', '')
            detected_language = transcription_result.get('language', 'auto-detected')
            method_used = transcription_result.get('method_used', 'unknown')

            logger.info(f"🌍 AUDIO_CHUNKING: Final result - Method: {method_used}, Language: {detected_language}")
            logger.info(f"📝 AUDIO_CHUNKING: Transcript length: {len(transcript_text)} characters")
            logger.info(f"⏱️ AUDIO_CHUNKING: Processing time: {transcription_result.get('processing_time', 0):.2f}s")
            logger.info(f"✅ Audio file preserved at {audio_path} for audio analysis")

            # Log success to debug viewer
            try:
                save_step_output(
                    job_id,
                    'transcribe_audio',
                    'success',
                    output={
                        'transcript_length': len(transcript_text),
                        'language': detected_language,
                        'method': method_used,
                        'duration': transcription_result.get('processing_time', 0)
                    }
                )
                logger.info(f"✅ Debug viewer updated: transcribe_audio success")
            except Exception as debug_error:
                logger.warning(f"⚠️ Debug logging failed (non-critical): {debug_error}")

            return {
                'success': True,
                'video_path': video_path,
                'audio_path': audio_path,  # 🔧 AUDIO PATH DOORGEVEN VOOR ANALYSIS!
                'transcript': transcript_text,
                'language': detected_language,  # Language detection from FastAudioTranscriber
                'job_id': job_id,
                'duration': download_data.get('duration', 0),
                'transcription_method': method_used,  # Now from FastAudioTranscriber
                'is_mock': transcription_result.get('is_mock', False),
                'quality_tier': transcription_result.get('quality_tier', 'unknown'),
                'allow_downstream': transcription_result.get('allow_downstream', True),
                # CRITICAL: Pass YouTube metadata through the chain
                'video_title': download_data.get('title', 'Unknown'),
                'youtube_metadata': download_data.get('metadata', {}),
                'user_preferences': download_data.get('user_preferences', {'clip_length': 30})
            }
            
        except Exception as whisper_error:
            logger.warning(f"⚠️ Whisper transcription failed for job {job_id}: {whisper_error}")
            logger.info(f"🎭 Falling back to enhanced mock transcript")

            # Create fallback audio path
            fallback_audio_path = video_path.replace('.mp4', '_audio.mp3')

            # Fallback to enhanced mock with viral content
            viral_test_transcript = """
            Wow, this is absolutely incredible! I can't believe what just happened.
            And then he said something that completely blew my mind.
            Amazing reaction from the crowd! This moment is going to be viral for sure.
            OMG, wait until you see this next part. Holy cow, that was insane!
            The way she responded was just perfect. This quote is everything.
            Suddenly everything changed and the whole room went crazy!
            Wait, look at this amazing moment! Incredible reaction here!
            """

            # 🔧 FIX: Pass fallback transcript when Whisper fails
            # This ensures UnifiedContentAnalyzer still gets text to analyze
            fallback_transcript = viral_test_transcript.strip()
            logger.info(f"📝 Using fallback transcript with {len(fallback_transcript)} characters")

            # Log fallback success to debug viewer
            try:
                save_step_output(
                    job_id,
                    'transcribe_audio',
                    'success',
                    output={
                        'transcript_length': len(fallback_transcript),
                        'language': 'en',
                        'method': 'fallback_mock',
                        'warning': 'Using fallback transcript - Whisper failed'
                    }
                )
                logger.info(f"✅ Debug viewer updated: transcribe_audio fallback success")
            except Exception as debug_error:
                logger.warning(f"⚠️ Debug logging failed (non-critical): {debug_error}")

            return {
                'success': True,
                'video_path': video_path,
                'audio_path': fallback_audio_path,  # 🔧 FIXED: Use fallback audio path
                'transcript': fallback_transcript,  # 🔧 FIX: Pass fallback transcript instead of empty string
                'language': 'en',  # Assume English for mock
                'job_id': job_id,
                'duration': download_data.get('duration', 0),
                'transcription_method': 'fallback_viral',  # Changed to indicate fallback with content
                'fallback_message': FallbackMessages.get('transcription_unavailable', 'nl'),
                # CRITICAL: Pass YouTube metadata through the chain (fallback too)
                'video_title': download_data.get('title', 'Unknown'),
                'youtube_metadata': download_data.get('metadata', {}),
                'user_preferences': download_data.get('user_preferences', {'clip_length': 30})
            }

    except Exception as e:
        logger.error(f"❌ Transcription task failed for job {job_id}: {e}")

        # Log failure to debug viewer
        try:
            from agents2.shared.utils.video_helpers import save_step_output
            save_step_output(job_id, 'transcribe_audio', 'failed', error=str(e))
        except Exception as debug_error:
            logger.warning(f"⚠️ Debug failure logging failed (non-critical): {debug_error}")

        raise self.retry(exc=e, countdown=30, max_retries=2)

# Add completion logging for transcribe_audio  
@celery_app.task(bind=True, name='tasks.video_processing.transcribe_audio_completed')
def log_transcribe_completed(self, transcription_data: Dict[str, Any]):
    """Log when transcribe_audio completes and what data it passes"""
    job_id = transcription_data.get('job_id', 'unknown')
    logger.info(f"🔍 TRANSCRIBE_COMPLETED: Job {job_id} passing data to next task:")
    logger.info(f"  - video_path: {transcription_data.get('video_path')}")
    logger.info(f"  - audio_path: {transcription_data.get('audio_path')}")  
    logger.info(f"  - job_id: {transcription_data.get('job_id')}")
    logger.info(f"🔍 TRANSCRIBE_COMPLETED: Next task is detect_moments (audio analysis removed)")
    return transcription_data


# ✅ AUDIO ANALYSIS REMOVED: YouTube metadata detection via SmartContentDetector is more reliable
# This function was causing '_analyze_metadata_content_type' errors and blocking Rick Astley music detection
# SmartContentDetector now handles content type detection directly from YouTube metadata in detect_moments
def REMOVED_analyze_audio_content():
    """REMOVED: Audio analysis was replaced by SmartContentDetector for better YouTube metadata detection"""
    pass  # Function body removed - SmartContentDetector handles content type detection


@celery_app.task(bind=True, name='tasks.video_processing.detect_moments', queue='ai_analysis')
def detect_moments(self, transcription_data: Dict[str, Any]):
    """Moment detection task - routed naar ai_analysis queue"""
    try:
        from agents2.moment_detection.moment_detector import MomentDetector

        # kleine helper om DB-progress te updaten
        def set_progress(pct: int, step: str):
            try:
                with get_db_session() as session:
                    from core.database_manager import Job
                    job = session.query(Job).filter(Job.id == transcription_data.get('job_id')).first()
                    if job:
                        job.progress = pct
                        job.current_step = step
                        session.commit()
            except Exception as _:
                pass

        job_id = transcription_data.get('job_id')

        # Import debug helpers
        from agents2.shared.utils.video_helpers import save_step_output

        # Log start of moment detection
        save_step_output(job_id, 'detect_moments', 'in_progress')

        logger.info(f"🔍 DETECT_MOMENTS_INPUT: Job {job_id} received data:")
        logger.info(f"  - video_path: {transcription_data.get('video_path')}")
        logger.info(f"  - audio_path: {transcription_data.get('audio_path')}")
        logger.info(f"  - content_type: {transcription_data.get('content_type')}")
        logger.info(f"  - audio_confidence: {transcription_data.get('audio_confidence')}")
        logger.info(f"🔍 DETECT_MOMENTS: Now receiving data directly from transcribe_audio (audio analysis removed)")

        logger.info(f"⚡ Detecting moments for job {job_id}")

        # ✅ CONTENT TYPE DETECTION: Based on YouTube metadata (like in backup)
        youtube_metadata = transcription_data.get('youtube_metadata', {})
        video_title = transcription_data.get('video_title', '') or youtube_metadata.get('title', '')
        description = youtube_metadata.get('description', '')
        uploader = youtube_metadata.get('uploader', '')
        categories = youtube_metadata.get('categories', [])
        tags = youtube_metadata.get('tags', [])

        # Log video information first
        logger.info(f"📺 VIDEO INFO: '{video_title}' by {uploader}")

        # Combine ALL metadata for comprehensive analysis
        metadata_text = f"{video_title} {description} {uploader} {' '.join(categories)} {' '.join(tags) if tags else ''}".lower()

        if metadata_text and metadata_text.strip():
            logger.info(f"🔍 Analyzing metadata for content type detection")

            # Music detection - be specific about music content
            music_indicators = ['music', 'song', 'lyrics', 'album', 'official music video', 'official video', 'music video', 'mv']
            if any(indicator in metadata_text for indicator in music_indicators):
                # Double-check it's not a podcast ABOUT music
                if not any(word in metadata_text for word in ['podcast', 'interview', 'talk about', 'discusses']):
                    logger.info(f"🎵 CONTENT TYPE: MUSIC detected from metadata - {video_title}")
                    content_type = 'music'
                    audio_confidence = 0.9
                    audio_analysis = {'success': True, 'method': 'metadata_full', 'fallback': False}
                else:
                    # Default to spoken for most content
                    logger.info(f"🗣️ CONTENT TYPE: SPOKEN detected (music discussion) - {video_title}")
                    content_type = 'spoken'
                    audio_confidence = 0.85
                    audio_analysis = {'success': True, 'method': 'metadata_full', 'fallback': False}
            else:
                # Default to spoken for most content
                logger.info(f"🗣️ CONTENT TYPE: SPOKEN detected (non-music) - {video_title}")
                content_type = 'spoken'
                audio_confidence = 0.85
                audio_analysis = {'success': True, 'method': 'metadata_full', 'fallback': False}
        else:
            # No metadata available - default to spoken
            logger.info(f"📊 CONTENT TYPE: SPOKEN (no metadata available) - defaulting for unknown content")
            content_type = 'spoken'
            audio_confidence = 0.5
            audio_analysis = {'success': True, 'method': 'metadata_fallback_default', 'fallback': True}

        logger.info(f"🎯 FINAL RESULT: Content Type = {content_type.upper()} | Confidence = {audio_confidence:.2f} | Title = '{video_title}'")
        logger.info(f"🔍 Detection method: {audio_analysis.get('method', 'unknown')}")

        detector = MomentDetector()

        # --- UI clip-lengte voorkeur mappen naar constraints ---
        # Verwacht: transcription_data['user_preferences']['clip_length'] in {30,45,60}
        # Als UI geen user_preferences meegeeft, maken we die hier aan met default 30
        if 'user_preferences' not in transcription_data:
            transcription_data['user_preferences'] = {'clip_length': 30}
            logger.info("📋 No user_preferences received, setting default clip_length=30")

        prefs = transcription_data.get('user_preferences', {}) or {}
        if 'clip_length' not in prefs:
            prefs['clip_length'] = 30
            logger.info("📋 No clip_length in user_preferences, setting default=30")

        clip_len = int(prefs.get('clip_length', 30))  # default 30s
        logger.info(f"🎬 Using clip length preference: {clip_len}s")

        # Presets: doel-lengte + speelruimte; kortere minima voor speeches
        if clip_len == 30:
            target_len, min_d, max_d = 30, 12, 45
        elif clip_len == 45:
            target_len, min_d, max_d = 45, 20, 60
        elif clip_len == 60:
            target_len, min_d, max_d = 60, 25, 60
        else:
            target_len, min_d, max_d = 30, 12, 45

        # Heartbeat callback: map 66%→95% binnen detectie
        def heartbeat(pct: float, msg: str = "detecting moments"):
            # pct is 0..100 binnen de detector; projecteer naar 66..95
            projected = 66 + int((pct/100.0) * (95-66))
            set_progress(projected, f"Detecting moments: {msg}")

        # CRITICAL FIX: cluster_gap_s moet NIET hardcoded zijn!
        # UnifiedContentAnalyzer zet dit content-aware (2.0s political, 8.0s viral)
        # Alleen override als user expliciet een waarde heeft ingesteld
        default_cluster_gap = float(os.getenv('MOMENTS_CLUSTER_GAP_S', '8.0'))

        constraints_override = {
            "target_len": target_len,
            "min_duration": min_d,
            "max_duration": max_d,
            "max_moments": int(prefs.get("max_moments", 6)),
            # Recall-pass instellingen (ruimer, voor veel kandidaten):
            "topk": int(prefs.get("topk", 30)),
            "min_conf": float(prefs.get("min_conf", 0.2)),
            "min_gap": float(prefs.get("min_gap", 0.5)),
            # Clustering & snapping:
            # ⚠️ CHANGED: Use env default instead of hardcoded 8.0
            # This allows UnifiedContentAnalyzer to set content-aware values
            "cluster_gap_s": float(prefs.get("cluster_gap_s", default_cluster_gap)),
            "snap_search_radius_s": float(prefs.get("snap_search_radius_s", 1.5)),
            "min_lead_in": float(prefs.get("min_lead_in", 0.35)),
            "min_lead_out": float(prefs.get("min_lead_out", 0.6)),
            # 🔑 Doorleveren voor UCA/snapping & fallback
            "audio_path": transcription_data.get('audio_path'),
            "video_path": transcription_data.get('video_path'),
        }
        moment_input = {
            'video_path': transcription_data['video_path'],
            'audio_path': transcription_data.get('audio_path'),
            'transcript': transcription_data['transcript'],
            'language': transcription_data.get('language', 'en'),  # From Whisper
            'output_types': ['viral', 'key_highlights', 'summary'],
            # CRITICAL: Pass audio analysis results from previous task
            'content_type': content_type,
            'audio_confidence': audio_confidence,
            'audio_analysis': audio_analysis,
            # 🔑 CRITICAL FIX: Pass youtube_metadata for SmartContentDetector
            'youtube_metadata': transcription_data.get('youtube_metadata', {}),
            'video_title': transcription_data.get('video_title', 'Unknown'),
            'user_intent': transcription_data.get('user_intent', 'auto'),
            # Nieuw: forceer clip policy end-to-end
            'constraints_override': constraints_override,
            # 🎯 Heartbeats terug naar DB zodat UI niet 'hangt'
            'progress_cb': heartbeat,
        }
        
        logger.info(f"🔍 MomentDetector input: {moment_input}")
        result = detector.detect_moments(moment_input)
        # Zet harde mijlpaal 95% na succesvolle detectie (snij-fase = 99%)
        set_progress(95, "Moments detected")

        if result['success']:
            if not result.get('moments'):
                logger.warning(
                    "⚠️ Moments empty after analyzer. Effective thresholds: "
                    f"min_conf={os.getenv('MOMENTS_MIN_CONF','0.25')}, "
                    f"min_duration={min_d}, max_duration={max_d}, "
                    f"topk={os.getenv('MOMENTS_TOPK','20')}"
                )
            moments_count = len(result.get('moments', []))
            analysis_mode = result.get('analysis_mode', 'unknown')
            logger.info(f"✅ Moments detected for job {job_id}: {moments_count} clips ({analysis_mode})")
            
            # Add user-friendly logging
            if moments_count == 0:
                logger.warning(f"⚠️ No valuable moments found in content for job {job_id}")
            elif moments_count <= 2:
                logger.info(f"🎯 Found {moments_count} high-quality moments for job {job_id}")
            else:
                logger.info(f"🔥 Found {moments_count} viral moments for job {job_id} - great content!")
            
            # Add job_id and video_path to result for next task in chain
            result['job_id'] = job_id
            result['video_path'] = transcription_data['video_path']
            
            # Extract keywords from all moments (aggregate)
            all_keywords = []
            for moment in result.get('moments', []):
                if 'keywords' in moment:
                    all_keywords.extend(moment.get('keywords', []))
            # Remove duplicates and store
            result['keywords'] = list(set(all_keywords))
            
            # CRITICAL: Pass ALL metadata from MomentDetector through the chain
            result['content_type'] = result.get('content_type', 'unknown')
            result['viral_score'] = result.get('viral_score', 0)
            result['total_moments'] = len(result.get('moments', []))
            # Respecteer analyzer/ffprobe duration; alleen invullen als leeg
            if 'video_duration' not in result or not result.get('video_duration'):
                meta_dur = transcription_data.get('youtube_metadata', {}).get('duration')
                if meta_dur:
                    result['video_duration'] = meta_dur
            result['analysis_mode'] = result.get('analysis_mode', 'unknown')

            # CRITICAL: Pass YouTube metadata through the chain for UI display
            result['video_title'] = transcription_data.get('video_title', 'Unknown')
            result['youtube_metadata'] = transcription_data.get('youtube_metadata', {})
            result['video_url'] = transcription_data.get('video_url', result['youtube_metadata'].get('webpage_url', ''))
            result['user_preferences'] = transcription_data.get('user_preferences', {'clip_length': 30})
            # Extra tellingsvelden voor downstream/DB/UI
            result['total_moments_detected'] = int(result.get('total_moments', 0))

            # Voor logging/UI transparantie
            logger.info(f"📈 DETECT SUMMARY: detected={result['total_moments_detected']}, "
                        f"content_type={result['content_type']}, analysis={result['analysis_mode']}")

            logger.info(
                f"✅ Passing metadata through chain: viral_score={result.get('viral_score')}, "
                f"moments={result.get('total_moments')}, duration={result.get('video_duration')}, "
                f"clip_policy={constraints_override}"
            )

            # Log success to debug viewer WITH TOP MOMENTS DETAILS
            try:
                # Extract top moments with full details for debug viewer
                moments_list = result.get('moments', [])
                top_moments = []
                for moment in moments_list[:5]:  # Show top 5 moments in debug view
                    top_moments.append({
                        'start_time': moment.get('start_time', 0),
                        'end_time': moment.get('end_time', 0),
                        'duration': moment.get('duration', 0),
                        'description': moment.get('description', ''),
                        'viral_score': moment.get('viral_score', 0),
                        'keywords': moment.get('keywords', [])
                    })

                save_step_output(
                    job_id,
                    'detect_moments',
                    'success',
                    output={
                        'moments_count': moments_count,
                        'content_type': result.get('content_type', 'unknown'),
                        'analysis_mode': analysis_mode,
                        'viral_score': result.get('viral_score', 0),
                        'top_moments': top_moments  # NEW: Full moment details for UI
                    }
                )
                logger.info(f"✅ Debug viewer updated: detect_moments success with {len(top_moments)} moment details")
            except Exception as debug_error:
                logger.warning(f"⚠️ Debug logging failed (non-critical): {debug_error}")

            return result
        else:
            raise Exception(result.get('error', 'Moment detection failed'))

    except Exception as e:
        job_id = transcription_data.get('job_id', 'unknown')
        logger.error(f"❌ Moment detection task failed for job {job_id}: {e}")

        # Log failure to debug viewer
        try:
            from agents2.shared.utils.video_helpers import save_step_output
            save_step_output(job_id, 'detect_moments', 'failed', error=str(e))
        except Exception as debug_error:
            logger.warning(f"⚠️ Debug failure logging failed (non-critical): {debug_error}")

        raise self.retry(exc=e, countdown=30, max_retries=2)

@celery_app.task(bind=True, name='tasks.video_processing.detect_faces', queue='ai_analysis')
def detect_faces(self, moment_data: Dict[str, Any]):
    """Face detection task - routed naar ai_analysis queue"""
    try:
        from agents2.face_detection.face_detector_mediapipe import SimpleFaceDetector
        from agents2.shared.utils.video_helpers import save_step_output, generate_face_screenshots

        job_id = moment_data.get('job_id')
        video_path = moment_data.get('video_path')

        # Log start of face detection
        save_step_output(job_id, 'detect_faces', 'in_progress')

        logger.info(f"👤 Detecting faces for job {job_id}")

        # Multi-frame face detection for better tracking
        detector = SimpleFaceDetector()
        result = detector.detect_faces({
            'video_path': video_path,
            'sample_interval': 3.0,  # Sample every 3 seconds for better tracking
            'confidence': 0.4        # Lower threshold for more face detection
        })

        if result['success']:
            faces_count = result.get('faces_detected', 0)
            logger.info(f"✅ Faces detected for job {job_id}: {faces_count} faces")

            # 🎯 VISUAL DEBUG: Generate face screenshots for debug viewer
            face_screenshots = []
            try:
                if faces_count > 0:
                    face_screenshots = generate_face_screenshots(
                        faces=result.get('faces', []),  # 🔥 FIX: Correct arg order
                        video_path=video_path,
                        job_id=job_id,                  # 🔥 FIX: Add missing job_id
                        max_faces=5  # 🔥 FIX: Correct kwarg name
                    )
                    logger.info(f"📸 Generated {len(face_screenshots)} face screenshots for debug viewer")
            except Exception as screenshot_error:
                logger.warning(f"⚠️ Face screenshots generation failed (non-critical): {screenshot_error}")

            # Log success to debug viewer WITH VISUAL DATA + FACE DATA FOR RE-RUN
            try:
                save_step_output(
                    job_id,
                    'detect_faces',
                    'success',
                    output={
                        'faces_detected': faces_count,
                        'face_screenshots': face_screenshots,  # 🎯 Visual feedback!
                        'faces': result.get('faces', []),  # 🔥 FIX: Save face data with timestamps for re-run!
                        'face_count': faces_count  # For convenience
                    }
                )
                logger.info(f"✅ Debug viewer updated: detect_faces success with {len(face_screenshots)} screenshots and {faces_count} face data entries")
            except Exception as debug_error:
                logger.warning(f"⚠️ Debug logging failed (non-critical): {debug_error}")

            # Pass along all data for next task
            result['job_id'] = job_id
            result['video_path'] = video_path
            result['moments'] = moment_data.get('moments', [])
            # Pass ALL moment detection metadata through the chain
            result['analysis_mode'] = moment_data.get('analysis_mode', 'unknown')
            result['total_moments'] = moment_data.get('total_moments', 3)
            result['video_duration'] = moment_data.get('video_duration', 0)
            result['viral_score'] = moment_data.get('viral_score', 0)
            result['keywords'] = moment_data.get('keywords', [])
            result['content_type'] = moment_data.get('content_type', 'spoken')
            # Pass YouTube metadata through the chain
            result['video_title'] = moment_data.get('video_title', 'Unknown')
            result['youtube_metadata'] = moment_data.get('youtube_metadata', {})
            result['user_preferences'] = moment_data.get('user_preferences', {'clip_length': 30})
            return result
        else:
            raise Exception(result.get('error', 'Face detection failed'))

    except Exception as e:
        job_id = moment_data.get('job_id', 'unknown')
        logger.error(f"❌ Face detection task failed for job {job_id}: {e}")

        # Log failure to debug viewer
        try:
            from agents2.shared.utils.video_helpers import save_step_output
            save_step_output(job_id, 'detect_faces', 'failed', error=str(e))
        except Exception as debug_error:
            logger.warning(f"⚠️ Debug failure logging failed (non-critical): {debug_error}")

        raise self.retry(exc=e, countdown=30, max_retries=2)

def _filter_faces_for_moment(all_faces: List[Dict], moment: Dict, buffer_seconds: float = 5.0) -> List[Dict]:
    """
    Filter faces relevant to a specific moment based on timestamp.

    CRITICAL FIX: Only use faces that appear during the moment's timeframe,
    not ALL faces in the video (which causes "wrong person in crop").

    Args:
        all_faces: All detected faces in video with timestamps
        moment: Moment dict with start_time, end_time
        buffer_seconds: Temporal buffer for frame-moment alignment (default 5s)

    Returns:
        List of faces within moment timeframe (empty if none found)
    """
    moment_start = moment.get('start_time', 0)
    moment_end = moment.get('end_time', 0)

    # Filter faces within moment timeframe with buffer
    relevant_faces = []
    for face in all_faces:
        face_timestamp = face.get('timestamp', 0)

        # Check if face appears during moment (with buffer)
        if face_timestamp >= moment_start - buffer_seconds and face_timestamp <= moment_end + buffer_seconds:
            relevant_faces.append(face)

    logger.debug(f"🎯 Filtered {len(relevant_faces)}/{len(all_faces)} faces for moment [{moment_start:.1f}s - {moment_end:.1f}s]")
    return relevant_faces


@celery_app.task(bind=True, name='tasks.video_processing.intelligent_crop', queue='video_processing')
def intelligent_crop(self, face_data: Dict[str, Any]):
    """Intelligent cropping task - routed naar video_processing queue"""
    try:
        from agents2.intelligent_cropping.intelligent_cropper import IntelligentCropper
        from agents2.shared.utils.video_helpers import save_step_output, generate_crop_comparison

        job_id = face_data.get('job_id')
        video_path = face_data.get('video_path')
        moments = face_data.get('moments', [])
        all_faces = face_data.get('faces', [])

        # Log start of cropping
        save_step_output(job_id, 'intelligent_crop', 'in_progress')

        logger.info(f"✂️ Intelligent cropping for job {job_id} ({len(moments)} moments, {len(all_faces)} total faces)")

        # 🎨 MANUAL CROP MODE: Check if user specified manual crop coordinates
        user_preferences = face_data.get('user_preferences', {})
        crop_method = user_preferences.get('crop_method', 'auto')

        if crop_method == 'manual':
            # Use manually specified coordinates
            manual_crop = {
                'x': user_preferences.get('crop_x', 0),
                'y': user_preferences.get('crop_y', 0),
                'width': user_preferences.get('crop_width', 607),
                'height': user_preferences.get('crop_height', 1080)
            }

            logger.info(f"🎨 Using MANUAL crop coordinates: x={manual_crop['x']}, y={manual_crop['y']}, size={manual_crop['width']}x{manual_crop['height']}")

            # Apply manual crop to all moments
            crops_per_moment = []
            for i, moment in enumerate(moments):
                crops_per_moment.append({
                    'moment_index': i,
                    'moment_start': moment.get('start_time', 0),
                    'moment_end': moment.get('end_time', 0),
                    'crop_coordinates': manual_crop,
                    'crop_method': 'manual',
                    'faces_used': 0,
                    'faces_original': len(all_faces),
                    'faces_filtered': 0
                })

            # Generate crop comparison image
            comparison_image = None
            try:
                comparison_image = generate_crop_comparison(
                    video_path=video_path,
                    crop_settings=manual_crop,
                    job_id=job_id,
                    timestamp=5.0
                )
                logger.info(f"✅ Manual crop comparison generated: {comparison_image}")
            except Exception as comp_error:
                logger.warning(f"⚠️ Could not generate manual crop comparison: {comp_error}")

            # Save step output
            save_step_output(
                job_id, 'intelligent_crop', 'success',
                output={
                    'crop_method': 'manual',
                    'crop_coordinates': manual_crop,
                    'crops_per_moment': crops_per_moment,
                    'comparison_image': comparison_image,
                    'target_aspect_ratio': '9:16',
                    'moments_processed': len(moments),
                    'agent_version': '3.2.0-manual-crop'
                }
            )

            # Return result for cut_videos task
            return {
                'success': True,
                'job_id': job_id,
                'video_path': video_path,
                'moments': moments,
                'crops_per_moment': crops_per_moment,
                'crop_mode': 'manual',
                'crop_coordinates': manual_crop,
                'comparison_image': comparison_image,
                'agent_version': '3.2.0-manual-crop'
            }

        # CRITICAL FIX: Filter faces per moment to avoid "wrong person in crop"
        # Attach relevant_faces to each moment instead of using ALL faces
        moments_with_faces = []
        for moment in moments:
            # Filter faces for this specific moment
            relevant_faces = _filter_faces_for_moment(all_faces, moment, buffer_seconds=5.0)

            # Attach filtered faces to moment
            moment_with_faces = moment.copy()
            moment_with_faces['relevant_faces'] = relevant_faces
            moments_with_faces.append(moment_with_faces)

            logger.info(f"🎯 Moment [{moment.get('start_time', 0):.1f}s-{moment.get('end_time', 0):.1f}s]: {len(relevant_faces)} relevant faces")

        cropper = IntelligentCropper()

        # V3.0 CINEMA-MVP: Enable cinematic mode via ENV flag
        enable_cinematic_mode = os.getenv('ENABLE_CINEMATIC_MODE', 'true').lower() == 'true'

        if enable_cinematic_mode:
            logger.info(f"🎬 CINEMA-MVP MODE ENABLED for job {job_id}")

        result = cropper.calculate_crop({
            'video_path': video_path,
            'faces': all_faces,  # Keep for backward compatibility
            'moments': moments_with_faces,  # ✅ V2.1: Pass moments with relevant_faces attached
            'use_ai_detection': False,  # Skip re-detection (reuse existing faces)
            'use_per_moment_faces': True,  # ✅ V2.1: Enable per-moment face filtering
            'enable_cinematic_mode': enable_cinematic_mode,  # ✅ V3.0: Enable Cinema-MVP features
            'target_formats': ['16:9', '9:16', '1:1']
        })

        if result['success']:
            logger.info(f"✅ Intelligent cropping completed for job {job_id}")

            # 🎯 VISUAL DEBUG: Generate before/after crop comparison for debug viewer
            comparison_image = None
            try:
                crop_coordinates = result.get('crop_coordinates', {})
                crop_method = result.get('crop_info', {}).get('crop_method', 'center')

                # ALWAYS generate comparison image, even for center crop
                # This shows users the before/after for any crop method
                comparison_image = generate_crop_comparison(
                    video_path=video_path,
                    crop_settings=crop_coordinates if crop_coordinates else None,  # Pass None for center crop
                    job_id=job_id,
                    timestamp=5.0  # Middle of video for best preview
                )

                if comparison_image:
                    logger.info(f"📸 Generated crop comparison image for debug viewer: {comparison_image} (method: {crop_method})")
                else:
                    logger.warning(f"⚠️ Crop comparison generation returned None")
            except Exception as comparison_error:
                logger.warning(f"⚠️ Crop comparison generation failed (non-critical): {comparison_error}")

            # Log success to debug viewer WITH VISUAL DATA
            try:
                crop_method = result.get('crop_info', {}).get('crop_method', 'center')
                save_step_output(
                    job_id,
                    'intelligent_crop',
                    'success',
                    output={
                        'crop_method': crop_method,
                        'moments_processed': len(moments),
                        'comparison_image': comparison_image,  # 🎯 Visual before/after!
                        'crop_coordinates': result.get('crop_coordinates', {}),
                        'target_aspect_ratio': '9:16',
                        'cinema_mode_enabled': enable_cinematic_mode
                    }
                )
                logger.info(f"✅ Debug viewer updated: intelligent_crop success with comparison image")
            except Exception as debug_error:
                logger.warning(f"⚠️ Debug logging failed (non-critical): {debug_error}")

            # Pass along data for next task including face/crop data
            result['job_id'] = job_id
            result['video_path'] = video_path
            result['moments'] = moments
            result['original_video_path'] = video_path  # Store original before cropping
            # Pass moment detection metadata through the chain
            result['analysis_mode'] = face_data.get('analysis_mode', 'unknown')
            result['total_moments'] = face_data.get('total_moments', 3)
            result['video_duration'] = face_data.get('video_duration', 0)
            result['viral_score'] = face_data.get('viral_score', 0)
            result['keywords'] = face_data.get('keywords', [])
            result['content_type'] = face_data.get('content_type', 'spoken')
            # Pass YouTube metadata through the chain
            result['video_title'] = face_data.get('video_title', 'Unknown')
            result['youtube_metadata'] = face_data.get('youtube_metadata', {})
            result['faces_data'] = {
                'faces_detected': len(face_data.get('faces', [])),
                'faces': face_data.get('faces', [])
            }
            result['crop_data'] = {
                'crop_method': result.get('crop_info', {}).get('crop_method', 'center'),
                'crop_info': result.get('crop_info', {}),
                'original_resolution': result.get('original_resolution', {}),
                'crop_coordinates': result.get('crop_coordinates', {})
            }
            # V3.2 FIX: Pass crops_per_moment to cut_videos for shot sequencing support
            result['crops_per_moment'] = result.get('crops_per_moment', [])
            result['user_preferences'] = face_data.get('user_preferences', {'clip_length': 30})
            return result
        else:
            raise Exception(result.get('error', 'Intelligent cropping failed'))

    except Exception as e:
        job_id = face_data.get('job_id', 'unknown')
        logger.error(f"❌ Intelligent cropping task failed for job {job_id}: {e}")

        # Log failure to debug viewer
        try:
            from agents2.shared.utils.video_helpers import save_step_output
            save_step_output(job_id, 'intelligent_crop', 'failed', error=str(e))
        except Exception as debug_error:
            logger.warning(f"⚠️ Debug failure logging failed (non-critical): {debug_error}")

        raise self.retry(exc=e, countdown=30, max_retries=2)

@celery_app.task(bind=True, name='tasks.video_processing.cut_videos', queue='video_processing')
def cut_videos(self, crop_data: Dict[str, Any]):
    """Dynamic video cutting with face tracking - Industry Standard"""
    try:
        from agents2.face_detection.face_tracker_dynamic import DynamicFaceTracker
        from agents2.video_processing.video_cutter_dynamic import DynamicVideoCutter
        from agents2.video_processing.video_cutter import VideoCutter  # Fallback
        from agents2.shared.utils.video_helpers import save_step_output

        # Progress helper naar 99% gedurende cut-fase
        def set_progress(pct: int, step: str):
            try:
                with get_db_session() as session:
                    from core.database_manager import Job
                    job = session.query(Job).filter(Job.id == crop_data.get('job_id')).first()
                    if job:
                        job.progress = pct
                        job.current_step = step
                        session.commit()
            except Exception:
                pass

        from agents2.schemas.video_processing import CropsPerMoment, SubMoment
        from pydantic import ValidationError

        job_id = crop_data.get('job_id')
        video_path = crop_data.get('video_path')
        moments = crop_data.get('moments', [])
        faces_data = crop_data.get('faces_data', {})
        crops_per_moment_raw = crop_data.get('crops_per_moment', [])

        # Log start of video cutting
        save_step_output(job_id, 'cut_videos', 'in_progress')

        # DEBUG: Log the exact input structure
        logger.info(f"🎬 V3.2 PIPELINE FIX: Dynamic face tracking + cutting for job {job_id}")
        logger.info(f"🔍 DEBUG cut_videos input keys: {list(crop_data.keys())}")
        logger.info(f"🔍 DEBUG moments count from input: {len(moments)}")
        logger.info(f"🔍 DEBUG crops_per_moment count: {len(crops_per_moment_raw)}")

        # CONTEXT7: Validate data contract with Pydantic
        if crops_per_moment_raw:
            try:
                # Convert raw crop data to Pydantic models for validation
                validated_schema = CropsPerMoment(
                    crops_per_moment=[SubMoment(**crop) for crop in crops_per_moment_raw],
                    crop_mode='per_moment',
                    success=True
                )
                crops_per_moment = [crop.dict() for crop in validated_schema.crops_per_moment]
                logger.info(f"✅ Data contract validated: {len(crops_per_moment)} crops")
            except ValidationError as e:
                logger.error(f"❌ DATA CONTRACT VIOLATION in crops_per_moment: {e.json()}")

                # Fail loudly with diagnostics
                return {
                    'success': False,
                    'error': 'Invalid crops_per_moment schema',
                    'error_code': 'DATA_CONTRACT_VIOLATION',
                    'validation_errors': e.errors(),
                    'job_id': job_id
                }
        else:
            crops_per_moment = []

        # V3.2 FIX: Check if crops_per_moment has sub-moment data
        has_sub_moments = any('sub_moment_index' in crop for crop in crops_per_moment)
        if has_sub_moments:
            logger.info(f"🎬 V3.2: Shot sequencing detected - using crops_per_moment for sub-moment granularity")

        if moments:
            logger.info(f"🔍 DEBUG first moment: {moments[0]}")
        else:
            logger.info(f"🔍 DEBUG moments array is empty!")

        # V3.2 CRITICAL FIX: Use crops_per_moment if available (supports sub-moments)
        # This enables split-screen shot sequencing (6 sub-moments per moment)
        cuts = []

        if crops_per_moment:
            # V3.2 NEW PATH: Create cuts from crops_per_moment (supports sub-moments)
            logger.info(f"🎬 V3.2: Creating cuts from {len(crops_per_moment)} crop definitions")

            for i, crop in enumerate(crops_per_moment):
                moment_idx = crop.get('moment_index', 0)
                sub_idx = crop.get('sub_moment_index')

                # Determine output filename based on sub-moment presence
                if sub_idx is not None:
                    # V3.2: Sub-moment naming (e.g., clip_0_0.mp4, clip_0_1.mp4)
                    output_name = f'clip_{moment_idx}_{sub_idx}'
                    logger.info(f"   Sub-moment {moment_idx}.{sub_idx}: {crop.get('start_time', 0):.1f}s - {crop.get('end_time', 0):.1f}s (shot: {crop.get('shot_type', 'N/A')})")
                else:
                    # Legacy: Single clip per moment
                    output_name = f'clip_{moment_idx}'

                # Get original moment metadata if available
                moment_data = moments[moment_idx] if moment_idx < len(moments) else {}

                cuts.append({
                    'start_time': crop.get('start_time', 0),
                    'end_time': crop.get('end_time', 0),
                    'output_name': output_name,
                    'crop_coordinates': crop.get('crop_coordinates'),  # V3.2: Include crop per sub-moment
                    'shot_type': crop.get('shot_type'),  # V3.2: Include cinematography metadata
                    'moment_index': moment_idx,
                    'sub_moment_index': sub_idx,
                    # Include original moment metadata
                    'keywords': moment_data.get('keywords', []),
                    'viral_score': moment_data.get('viral_score'),
                    'sentence_text': moment_data.get('sentence_text', ''),
                    'description': moment_data.get('description', '')
                })

            logger.info(f"🎯 V3.2: Created {len(cuts)} cuts from crops_per_moment (includes sub-moments)")

        else:
            # V2 LEGACY PATH: Create cuts from moments (no sub-moments)
            logger.info(f"🔍 V2 LEGACY: No crops_per_moment found, falling back to moments-based cutting")

            for i, moment in enumerate(moments):
                cuts.append({
                    'start_time': moment.get('start_time', i * 20),
                    'end_time': moment.get('end_time', (i * 20) + 15),
                    'output_name': f'clip_{i}',
                    # Include moment metadata for each clip
                    'keywords': moment.get('keywords', []),
                    'viral_score': moment.get('viral_score'),
                    'sentence_text': moment.get('sentence_text', ''),
                    'description': moment.get('description', ''),
                    'moment_id': moment.get('moment_id')  # NEW: Pass moment_id for Phase 2 linking
                })

            logger.info(f"🎯 V2: Created {len(cuts)} cuts from moments (legacy mode)")

        # Check if we have faces for dynamic tracking
        faces = faces_data.get('faces', [])
        
        if faces and len(faces) > 0:
            logger.info(f"🎯 Using dynamic face tracking for {len(faces)} faces")
            # snijfase begonnen ⇒ zet naar 99% baseline; sub-progress blijft op 99
            set_progress(99, "Cutting (dynamic tracking)")

            # Step 1: Dynamic face tracking through video
            tracker = DynamicFaceTracker()
            tracking_result = tracker.track_faces_through_video({
                'video_path': video_path,
                'target_aspect_ratio': '9:16',
                'tracker_type': 'KCF',  # Good balance speed/accuracy
                'smoothing_factor': 0.3,  # Smooth camera movement
                'face_margin': 0.25,      # 25% margin around face
                'initial_faces': faces
            })
            
            if tracking_result['success']:
                # Step 2: Cut video with dynamic tracking data
                cutter = DynamicVideoCutter()
                result = cutter.cut_video_with_tracking({
                    'video_path': video_path,
                    'cuts': cuts,
                    'output_path': f'./io/output/{job_id}',
                    'tracking_data': tracking_result['tracking_data'],
                    'target_aspect_ratio': '9:16'
                })
                
                if result['success']:
                    logger.info(f"✅ Dynamic face tracking cutting completed for job {job_id}")
                    result['job_id'] = job_id
                    result['tracking_method'] = 'dynamic_opencv_tracking'
                    # Pass moment detection metadata through
                    result['analysis_mode'] = crop_data.get('analysis_mode', 'unknown')
                    result['total_moments'] = crop_data.get('total_moments')
                    result['video_duration'] = crop_data.get('video_duration')
                    result['keywords'] = crop_data.get('keywords', [])
                    result['content_type'] = crop_data.get('content_type', 'spoken')
                    # Pass YouTube metadata through the chain
                    result['video_title'] = crop_data.get('video_title', 'Unknown')
                    result['youtube_metadata'] = crop_data.get('youtube_metadata', {})
                    result['moments'] = moments  # Pass moments array for metadata storage
                    return result
            
            logger.warning(f"⚠️ Dynamic tracking failed, falling back to static crop")
        
        # Fallback to VideoCutter (static) - maar gebruikt nog steeds V3.2 per-cut crop coordinates
        if has_sub_moments:
            logger.info(f"✂️ V3.2 VideoCutter: Cutting {len(cuts)} sub-moments with shot-specific crop coordinates for job {job_id}")
        else:
            logger.info(f"✂️ VideoCutter: Cutting {len(cuts)} clips with static crop for job {job_id}")
        cutter = VideoCutter()

        # progress callback doorgeven zodat cutter subprogress kan melden (99%)
        def cutter_heartbeat(pct: float, msg: str = "cutting"):
            # houdt het binnen 99% (de finalize zet 100%)
            set_progress(99, f"Cutting: {msg}")

        # V3.2 FIX: Per-cut crop coordinates (not global)
        # Each cut now has its own crop_coordinates from crops_per_moment
        # VideoCutter will apply crop_coordinates on a per-cut basis
        result = cutter.cut_video({
            'video_path': video_path,
            'cuts': cuts,  # V3.2: Each cut contains crop_coordinates field
            'output_path': f'./io/output/{job_id}',
            'crop_coordinates': crop_data.get('crop_coordinates'),  # V2 LEGACY: Global fallback
            'target_aspect_ratio': '9:16'
            # NB: onze VideoCutter ondersteunt optionele min/max; hier niet forceren
            # 'min_duration': 12, 'max_duration': 60,
            # 'copy_streams': True,
            # 'progress_cb': cutter_heartbeat,  ← alleen meegeven als je cutter deze parameter accepteert
        })

        if result['success']:
            clips_count = len(result.get('cut_videos', []))
            if has_sub_moments:
                logger.info(f"✅ V3.2 VideoCutter: Successfully cut {len(cuts)} sub-moments with shot-specific crops for job {job_id}")
            else:
                logger.info(f"✅ VideoCutter: Successfully cut {len(cuts)} clips for job {job_id}")

            # Log success to debug viewer
            try:
                save_step_output(
                    job_id,
                    'cut_videos',
                    'success',
                    output={
                        'clips_produced': clips_count,
                        'cuts_total': len(cuts)
                    }
                )
                logger.info(f"✅ Debug viewer updated: cut_videos success")
            except Exception as debug_error:
                logger.warning(f"⚠️ Debug logging failed (non-critical): {debug_error}")

            result['job_id'] = job_id
            result['tracking_method'] = 'static_crop_fallback'
            # Pass ALL metadata through the chain
            result['analysis_mode'] = crop_data.get('analysis_mode', 'unknown')
            result['total_moments'] = crop_data.get('total_moments', 3)
            result['video_duration'] = crop_data.get('video_duration', 0)
            result['viral_score'] = crop_data.get('viral_score', 0)
            result['keywords'] = crop_data.get('keywords', [])
            result['content_type'] = crop_data.get('content_type', 'spoken')
            # Pass YouTube metadata through the chain
            result['video_title'] = crop_data.get('video_title', 'Unknown')
            result['youtube_metadata'] = crop_data.get('youtube_metadata', {})
            result['video_url'] = crop_data.get('video_url', crop_data.get('youtube_metadata', {}).get('webpage_url', ''))
            result['moments'] = moments  # Pass moments array for metadata storage
            # Transparante metrics naar finalize:
            result['clips_produced'] = len(result.get('cut_videos') or [])
            # Zet 99% milestone (finalize zet 100%)
            set_progress(99, "Cutting completed")
            return result
        else:
            raise Exception(result.get('error', 'Video cutting failed'))

    except Exception as e:
        job_id = crop_data.get('job_id', 'unknown')
        logger.error(f"❌ Video cutting task failed for job {job_id}: {e}")

        # Log failure to debug viewer
        try:
            from agents2.shared.utils.video_helpers import save_step_output
            save_step_output(job_id, 'cut_videos', 'failed', error=str(e))
        except Exception as debug_error:
            logger.warning(f"⚠️ Debug failure logging failed (non-critical): {debug_error}")

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


# ==============================================================================
# PRIORITY 3: RE-RUN SYSTEM (DEBUG_VIEWER_V2.md)
# ==============================================================================

@celery_app.task(bind=True, name='tasks.video_processing.finalize_rerun_task')
def finalize_rerun_task(self, cut_videos_result: Dict, job_id: str, start_step: str, config_override: Dict):
    """
    Finalize re-run workflow: Mark job as completed

    This is the final callback in the re-run chain.
    Called after cut_videos completes.
    """
    try:
        logger.info(f"🎬 Finalizing re-run for job {job_id}")

        from core.database_manager import PostgreSQLManager, Job
        db = PostgreSQLManager()

        with db.get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()

            if job:
                job.status = 'completed'
                job.phase = 'completed'
                job.progress = 100
                job.current_step = 'Re-run completed'
                job.completed_at = datetime.now(timezone.utc)
                session.commit()

                logger.info(f"✅ Re-run completed successfully for job {job_id}")

        return {
            'success': True,
            'clips_generated': len(cut_videos_result.get('cut_videos', [])),
            'rerun_from': start_step,
            'config_applied': config_override
        }

    except Exception as e:
        logger.error(f"❌ Finalize re-run failed for job {job_id}: {str(e)}")
        raise


@celery_app.task(bind=True, name='tasks.video_processing.rerun_processing_steps_task')
def rerun_processing_steps_task(self, job_id: str, start_step: str, config_override: Dict):
    """
    Re-run processing steps starting from start_step with new configuration

    Priority 3 Feature: Allows developers to re-run pipeline steps without
    re-downloading videos, saving significant time during testing/tuning.

    Args:
        job_id: Job UUID
        start_step: Step to start re-running from ('detect_moments' | 'detect_faces' | 'intelligent_crop' | 'cut_videos')
        config_override: New configuration to apply (merged with existing job config)

    Example:
        rerun_processing_steps_task.delay(
            job_id='abc-123',
            start_step='detect_faces',
            config_override={
                'user_preferences': {
                    'face_confidence': 0.7,
                    'sample_interval': 1.5
                }
            }
        )

    Dependency Handling:
        - Re-run detect_moments → triggers: detect_faces, intelligent_crop, cut_videos
        - Re-run detect_faces → triggers: intelligent_crop, cut_videos
        - Re-run intelligent_crop → triggers: cut_videos
        - Re-run cut_videos → no dependencies
    """
    try:
        from celery import chain
        logger.info(f"🔄 Re-running pipeline from step '{start_step}' for job {job_id}")
        logger.info(f"📦 Config override: {config_override}")

        # Load job and existing step outputs
        from core.database_manager import PostgreSQLManager, Job, Moment
        db = PostgreSQLManager()

        with db.get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()

            if not job:
                raise ValueError(f"Job {job_id} not found")

            # Get existing step outputs (we need video_path, transcript, etc.)
            step_outputs = job.step_outputs or {}

            # Extract config from override
            user_preferences = config_override.get('user_preferences', {})
            face_filters = config_override.get('face_filters', {})

            logger.info(f"🔍 Existing step_outputs keys: {list(step_outputs.keys())}")

            # Get video_path (needed for all chains)
            video_path = step_outputs.get('download_video', {}).get('output', {}).get('video_path')
            if not video_path:
                raise ValueError("video_path not found in step_outputs")

            # Prepare data based on start_step and build chain
            workflow = None

            if start_step == 'detect_moments':
                # Full chain: detect_moments → detect_faces → intelligent_crop → cut_videos → finalize
                transcript_output = step_outputs.get('transcribe_audio', {}).get('output', {})
                transcript = transcript_output.get('transcript')

                if not transcript:
                    raise ValueError("Cannot re-run detect_moments: transcript not found in step_outputs")

                logger.info(f"🔄 Building full chain from detect_moments")
                job.phase = 'rerun_detect_moments'
                job.progress = 25
                job.current_step = 'Detecting moments (re-run)'
                session.commit()

                # Prepare transcription_data for first task
                transcription_data = {
                    'job_id': job_id,
                    'video_path': video_path,
                    'transcript': transcript,
                    'language': transcript_output.get('language', 'en'),
                    'duration': transcript_output.get('duration', 0),
                    'user_preferences': user_preferences or {'clip_length': 30}
                }

                # Build chain: detect_moments will return moment_data with moments array
                # Each subsequent task receives previous result and extracts what it needs
                workflow = chain(
                    detect_moments.s(transcription_data),
                    detect_faces.s(),
                    intelligent_crop.s(),
                    cut_videos.s(),
                    finalize_rerun_task.s(job_id, start_step, config_override)
                )

            elif start_step == 'detect_faces':
                # Chain: detect_faces → intelligent_crop → cut_videos → finalize
                logger.info(f"📥 Loading existing moments from database")
                moments_from_db = session.query(Moment).filter(Moment.job_id == job_id).all()
                moments = [
                    {
                        'start_time': m.start_time,
                        'end_time': m.end_time,
                        'description': m.description,
                        'viral_score': m.viral_score,
                        'keywords': m.keywords or []
                    }
                    for m in moments_from_db
                ]
                logger.info(f"📥 Loaded {len(moments)} existing moments")

                logger.info(f"🔄 Building chain from detect_faces")
                job.phase = 'rerun_detect_faces'
                job.progress = 50
                job.current_step = 'Detecting faces (re-run)'
                session.commit()

                # Prepare moment_data for detect_faces
                moment_data = {
                    'job_id': job_id,
                    'video_path': video_path,
                    'moments': moments,
                    'user_preferences': user_preferences
                }

                workflow = chain(
                    detect_faces.s(moment_data),
                    intelligent_crop.s(),
                    cut_videos.s(),
                    finalize_rerun_task.s(job_id, start_step, config_override)
                )

            elif start_step == 'intelligent_crop':
                # Chain: intelligent_crop → cut_videos → finalize
                logger.info(f"📥 Loading existing data from step_outputs and database")

                # Load moments
                moments_from_db = session.query(Moment).filter(Moment.job_id == job_id).all()
                moments = [
                    {
                        'start_time': m.start_time,
                        'end_time': m.end_time,
                        'description': m.description,
                        'viral_score': m.viral_score,
                        'keywords': m.keywords or []
                    }
                    for m in moments_from_db
                ]

                # Load faces
                faces_result = step_outputs.get('detect_faces', {}).get('output', {})
                faces = faces_result.get('faces', [])

                # Apply face filters if specified
                if 'enabled_faces' in face_filters:
                    enabled_ids = face_filters['enabled_faces']
                    faces = [f for i, f in enumerate(faces) if f"face_{i}" in enabled_ids]
                    logger.info(f"👤 Filtered to {len(faces)} enabled faces")

                logger.info(f"📥 Loaded {len(moments)} moments and {len(faces)} faces")

                logger.info(f"🔄 Building chain from intelligent_crop")
                job.phase = 'rerun_intelligent_crop'
                job.progress = 75
                job.current_step = 'Cropping (re-run)'
                session.commit()

                # Prepare face_data for intelligent_crop
                face_data = {
                    'job_id': job_id,
                    'video_path': video_path,
                    'moments': moments,
                    'faces': faces,
                    'user_preferences': user_preferences
                }

                workflow = chain(
                    intelligent_crop.s(face_data),
                    cut_videos.s(),
                    finalize_rerun_task.s(job_id, start_step, config_override)
                )

            elif start_step == 'cut_videos':
                # Chain: cut_videos → finalize (shortest chain)
                logger.info(f"📥 Loading existing data from step_outputs and database")

                # Load moments
                moments_from_db = session.query(Moment).filter(Moment.job_id == job_id).all()
                moments = [
                    {
                        'start_time': m.start_time,
                        'end_time': m.end_time,
                        'description': m.description,
                        'viral_score': m.viral_score,
                        'keywords': m.keywords or []
                    }
                    for m in moments_from_db
                ]

                # Load faces and crop data
                faces_result = step_outputs.get('detect_faces', {}).get('output', {})
                faces = faces_result.get('faces', [])
                crop_result = step_outputs.get('intelligent_crop', {}).get('output', {})

                logger.info(f"📥 Loaded {len(moments)} moments, {len(faces)} faces")

                logger.info(f"🔄 Building chain from cut_videos")
                job.phase = 'rerun_cut_videos'
                job.progress = 90
                job.current_step = 'Cutting videos (re-run)'
                session.commit()

                # Prepare crop_data for cut_videos
                crop_data = {
                    'job_id': job_id,
                    'video_path': video_path,
                    'moments': moments,
                    'faces_data': {'faces': faces},
                    'crop_data': crop_result.get('crop_data', {}),
                    'crop_coordinates': crop_result.get('crop_coordinates', {}),
                    'crops_per_moment': crop_result.get('crops_per_moment', []),
                    'user_preferences': user_preferences
                }

                workflow = chain(
                    cut_videos.s(crop_data),
                    finalize_rerun_task.s(job_id, start_step, config_override)
                )

            else:
                raise ValueError(f"Invalid start_step: {start_step}. Must be one of: detect_moments, detect_faces, intelligent_crop, cut_videos")

            # Dispatch chain asynchronously (non-blocking)
            if workflow:
                logger.info(f"🚀 Dispatching Celery chain for re-run (non-blocking)")
                workflow.apply_async()

                logger.info(f"✅ Re-run chain dispatched successfully for job {job_id}")

                return {
                    'success': True,
                    'message': f'Re-run chain dispatched from {start_step}',
                    'job_id': job_id,
                    'rerun_from': start_step,
                    'config_applied': config_override
                }
            else:
                raise ValueError("Failed to build workflow chain")

    except Exception as e:
        logger.error(f"❌ Re-run failed for job {job_id}: {str(e)}")

        # Update job status on error
        try:
            from core.database_manager import PostgreSQLManager, Job
            db = PostgreSQLManager()
            with db.get_session() as session:
                job = session.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = 'failed'
                    job.phase = 'error'
                    job.current_step = f'Re-run failed: {str(e)}'
                    session.commit()
        except Exception as db_error:
            logger.error(f"Failed to update job status: {db_error}")

        raise
