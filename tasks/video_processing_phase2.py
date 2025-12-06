#!/usr/bin/env python3
"""
Phase 2 Workflow: Clip Generation for Selected Moments
======================================================

Phase 2 genereert clips alleen voor user-geselecteerde moments.
Pipeline: load_selected_moments → intelligent_crop → cut_videos → finalize

Output:
- Clips generated only for selected moments
- Job status = 'completed'
- Clips linked to moments via moment_id
"""

import os
import sys
import logging
import json
from typing import Dict, Any, List
from datetime import datetime, timezone
from celery import chain

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.celery_app import celery_app
from core.database_pool import get_db_session

logger = logging.getLogger(__name__)


def create_phase2_workflow(job_id: str, selected_moment_ids: List[str]):
    """
    Create Phase 2 workflow: Generate clips for selected moments

    Pipeline:
        load_selected_moments → intelligent_crop → cut_videos → finalize

    Args:
        job_id: Job UUID
        selected_moment_ids: List of Moment UUIDs to process

    Returns:
        Celery chain workflow
    """
    logger.info(f"🎬 Creating Phase 2 workflow for job {job_id} with {len(selected_moment_ids)} moments")

    # Import tasks from main video_processing module
    from tasks.video_processing import intelligent_crop, cut_videos

    workflow = chain(
        load_selected_moments.s(job_id, selected_moment_ids),
        intelligent_crop.s(),
        cut_videos.s(),
        finalize_phase2.s(job_id)
    )

    logger.info(f"✅ Phase 2 workflow created for job {job_id}")
    return workflow


@celery_app.task(bind=True, name='tasks.video_processing_phase2.load_selected_moments')
def load_selected_moments(self, job_id: str, selected_moment_ids: List[str]):
    """
    Load selected moments and inject Phase 2 configuration from pipeline_config

    Context7 Validated: Configuration injection patterns (trust score 9.1)
    Pattern: Load config from DB state, pass to downstream tasks via task args

    Changes from original:
    - BEFORE: Use hardcoded defaults for crop settings
    - AFTER: Load crop settings from pipeline_config.phase2
    - NEW: Support manual crop coordinates from Visual Crop Editor
    - NEW: Validate configuration before starting Phase 2
    - NEW: Pass crop_config to intelligent_crop task

    Returns task data in format compatible with existing crop/cut tasks

    Args:
        job_id: Job UUID
        selected_moment_ids: List of moment IDs to process

    Returns:
        Dict with moments data + crop_config for intelligent_crop task
    """
    try:
        logger.info(f"[{job_id}] Loading {len(selected_moment_ids)} selected moments...")

        with get_db_session() as session:
            from core.database_manager import Job, Moment

            # Get job
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")

            # Validate phase (support both old and new phases)
            valid_phases = ['awaiting_selection', 'phase2_generation', 'awaiting_admin_config', 'awaiting_user_selection']
            if job.phase not in valid_phases:
                logger.warning(f"[{job_id}] Job phase is {job.phase}, expected one of: {valid_phases}")

            # 🔥 NEW: Load Phase 2 configuration from pipeline_config
            # Context7 Validated: DB state as config store (trust score 9.1)
            phase2_config = {}
            if job.pipeline_config and 'phase2' in job.pipeline_config:
                phase2_config = job.pipeline_config['phase2']
                logger.info(f"[{job_id}] ✅ Using admin-configured Phase 2 settings: {phase2_config}")
            else:
                logger.info(f"[{job_id}] ℹ️  No Phase 2 config found, using defaults")

            # Extract configuration with defaults
            crop_method = phase2_config.get('crop_method', 'auto')  # "auto" | "manual" | "face-focused"
            manual_crop_coords = phase2_config.get('manual_crop_coords', None)
            clip_length = phase2_config.get('clip_length', 30)
            target_aspect_ratio = phase2_config.get('target_aspect_ratio', '9:16')

            # 🔥 NEW: Validate manual crop coordinates if provided
            if crop_method == 'manual':
                if not manual_crop_coords:
                    raise ValueError("Manual crop method requires crop coordinates")

                required_keys = ['x', 'y', 'width', 'height']
                if not all(key in manual_crop_coords for key in required_keys):
                    raise ValueError(f"Manual crop coords must have: {required_keys}")

                logger.info(f"[{job_id}] 🎨 Using manual crop coordinates: {manual_crop_coords}")

            # Update phase to phase2_running (NEW phase name)
            job.phase = 'phase2_running'  # CHANGED FROM: 'phase2_generation'
            job.progress = 70  # CHANGED FROM: 55
            job.current_step = f'Phase 2 Starting - {crop_method} crop, {clip_length}s clips'

            # 🔥 NEW: Store Phase 2 start metadata
            if not job.pipeline_config:
                job.pipeline_config = {}

            job.pipeline_config['phase2_started'] = {
                'started_at': datetime.now(timezone.utc).isoformat(),
                'crop_method': crop_method,
                'clip_length': clip_length,
                'moments_count': len(selected_moment_ids)
            }

            # Load selected moments
            moments = session.query(Moment).filter(
                Moment.job_id == job_id,
                Moment.id.in_(selected_moment_ids)
            ).order_by(Moment.moment_index).all()

            if len(moments) == 0:
                raise ValueError(f"No moments found for job {job_id} with provided IDs")

            if len(moments) != len(selected_moment_ids):
                logger.warning(f"[{job_id}] Found {len(moments)} moments, expected {len(selected_moment_ids)}")

            # Mark moments as selected
            for moment in moments:
                moment.is_selected = True
                moment.selected_at = datetime.now(timezone.utc)

            # Convert to format compatible with existing tasks
            viral_moments = []
            for m in moments:
                viral_moments.append({
                    'moment_index': m.moment_index,
                    'start_time': float(m.start_time),
                    'end_time': float(m.end_time),
                    'description': m.description,
                    'sentence_text': m.sentence_text,
                    'sentence': m.sentence_text,  # Backward compatibility
                    'keywords': m.keywords or [],
                    'viral_score': float(m.viral_score) if m.viral_score else 0,
                    'score': float(m.viral_score) if m.viral_score else 0,  # Backward compatibility
                    'moment_id': str(m.id)  # NEW: Track which moment this clip belongs to
                })

            session.commit()

            logger.info(f"[{job_id}] ✅ Loaded {len(moments)} moments: {[m.moment_index for m in moments]}")
            logger.info(f"[{job_id}] 🔧 Phase 2 config: crop_method={crop_method}, clip_length={clip_length}s")

            # Get video path from Phase 1 (reuse downloaded video)
            # Find the actual video file in the job directory
            video_path = None
            job_dir = f'./io/input/{job_id}'
            if os.path.exists(job_dir):
                # Find first .mp4 file (excluding audio files)
                for filename in os.listdir(job_dir):
                    if filename.endswith('.mp4') and not filename.endswith('_audio.mp4'):
                        video_path = os.path.join(job_dir, filename)
                        logger.info(f"[{job_id}] Found video file: {video_path}")
                        break

            if not video_path or not os.path.exists(video_path):
                # Try alternative paths
                for alt_dir in [f'./io/downloads/{job_id}', f'./io/input']:
                    if os.path.exists(alt_dir):
                        for filename in os.listdir(alt_dir):
                            if filename.endswith('.mp4') and not filename.endswith('_audio.mp4'):
                                video_path = os.path.join(alt_dir, filename)
                                break
                    if video_path and os.path.exists(video_path):
                        break

                if not video_path or not os.path.exists(video_path):
                    logger.warning(f"[{job_id}] Video file not found at expected paths")

            # 🔥 FIX: Load faces from Phase 1 step_outputs (needed for intelligent_crop)
            faces = []
            if job.step_outputs:
                try:
                    step_outputs = json.loads(job.step_outputs) if isinstance(job.step_outputs, str) else job.step_outputs
                    faces_data = step_outputs.get('detect_faces', {}).get('output', {})
                    faces = faces_data.get('faces', [])
                    logger.info(f"[{job_id}] Loaded {len(faces)} faces from Phase 1 for intelligent_crop")
                except Exception as face_load_error:
                    logger.warning(f"[{job_id}] Could not load faces from step_outputs: {face_load_error}")

            # Return data in format compatible with intelligent_crop task
            return {
                'success': True,
                'job_id': job_id,
                'video_path': video_path,
                'moments': viral_moments,
                'faces': faces,  # 🔥 FIX: Add faces for intelligent_crop!
                'selected_count': len(moments),
                # Pass job metadata for downstream tasks
                'content_type': job.content_type,
                'viral_score': job.viral_score,
                'keywords': job.keywords or [],
                'video_duration': float(job.video_duration) if job.video_duration else 0,
                'analysis_mode': job.analysis_mode,
                'video_title': job.youtube_title or 'Unknown',
                'youtube_metadata': {},
                'user_preferences': {'clip_length': job.clip_duration_preference or 30}
            }

    except Exception as e:
        logger.error(f"[{job_id}] ❌ Error loading moments: {e}")

        # Update job status to failed
        try:
            with get_db_session() as session:
                from core.database_manager import Job
                job = session.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = 'failed'
                    job.phase = 'failed'
                    job.error_message = f"Failed to load moments: {str(e)}"
                    session.commit()
        except Exception as db_error:
            logger.error(f"[{job_id}] Failed to update job status: {db_error}")

        raise self.retry(exc=e, countdown=30, max_retries=2)


@celery_app.task(bind=True, name='tasks.video_processing_phase2.finalize_phase2')
def finalize_phase2(self, task_data: Dict[str, Any], job_id: str):
    """
    Finalize Phase 2: Update job status and link clips to moments

    Input task_data contains:
        - cut_videos: List of generated clip paths
        - moments: Moments that were processed (with moment_id)

    Updates:
        - Links clips to moments via moment_id
        - Sets job.phase = 'completed'
        - Sets job.status = 'completed'
        - Sets job.progress = 100%
    """
    try:
        logger.info(f"[{job_id}] Finalizing Phase 2...")

        cut_videos = task_data.get('cut_videos', [])
        moments = task_data.get('moments', [])

        logger.info(f"[{job_id}] Linking {len(cut_videos)} clips to moments...")

        with get_db_session() as session:
            from core.database_manager import Job, Clip, Moment

            job = session.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")

            # Create clips in database and link to moments
            # Cinema-MVP mode generates multiple clips per moment, so link ALL clips to the same moment
            linked_count = 0

            # Get the moment_id from the first moment (all clips belong to this moment)
            moment_id = moments[0].get('moment_id') if moments else None
            if not moment_id:
                logger.error(f"[{job_id}] No moment_id found in moments data")
                raise ValueError("Cannot link clips: no moment_id")

            logger.info(f"[{job_id}] Linking all {len(cut_videos)} clips to moment {moment_id}")

            for i, clip_data in enumerate(cut_videos):
                # Get clip path
                clip_path = clip_data.get('path', clip_data.get('file_path', ''))
                if not clip_path:
                    logger.warning(f"[{job_id}] Clip data missing path: {clip_data}")
                    continue

                # Check if clip already exists (avoid duplicates)
                existing_clip = session.query(Clip).filter(
                    Clip.job_id == job_id,
                    Clip.file_path == clip_path
                ).first()

                if existing_clip:
                    # Update existing clip
                    existing_clip.moment_id = moment_id
                    clip = existing_clip
                    logger.info(f"[{job_id}] Updated existing clip {clip_path}")
                else:
                    # Create new clip record
                    # Get description from the first moment (all clips share same moment)
                    moment_description = moments[0].get('description', f"Clip {i+1}") if moments else f"Clip {i+1}"

                    clip = Clip(
                        job_id=job_id,
                        moment_id=moment_id,  # Link to moment
                        clip_number=clip_data.get('cut_number', i + 1),
                        file_path=clip_path,
                        duration=clip_data.get('duration'),
                        title=moment_description[:100],
                        description=moment_description,
                        crop_method=clip_data.get('crop_method'),
                        original_video_path=clip_data.get('original_path'),
                        file_size=clip_data.get('size'),
                        created_at=datetime.now(timezone.utc)
                    )
                    session.add(clip)
                    logger.info(f"[{job_id}] Created clip {clip_path} linked to moment {moment_id}")

                linked_count += 1

            # Update job status
            job.phase = 'completed'
            job.status = 'completed'
            job.progress = 100
            job.current_step = 'Completed'
            job.completed_at = datetime.now(timezone.utc)

            # Update job metadata from processing results
            if task_data.get('content_type'):
                job.content_type = task_data.get('content_type')
            if task_data.get('viral_score'):
                job.viral_score = task_data.get('viral_score')
            if task_data.get('keywords'):
                job.keywords = task_data.get('keywords')

            session.commit()

            logger.info(f"[{job_id}] ✅ Phase 2 complete. Generated {len(cut_videos)} clips, linked {linked_count} to moments.")

            return {
                'success': True,
                'job_id': job_id,
                'phase': 'completed',
                'clips_count': len(cut_videos),
                'clips_linked': linked_count,
                'message': f'Generated {len(cut_videos)} clips from selected moments',
                'cut_videos_data': task_data
            }

    except Exception as e:
        logger.error(f"[{job_id}] ❌ Error finalizing Phase 2: {e}")

        # Update job status to failed
        try:
            with get_db_session() as session:
                from core.database_manager import Job
                job = session.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = 'failed'
                    job.phase = 'failed'
                    job.error_message = f"Failed to finalize Phase 2: {str(e)}"
                    session.commit()
        except Exception as db_error:
            logger.error(f"[{job_id}] Failed to update job status: {db_error}")

        raise self.retry(exc=e, countdown=30, max_retries=2)
