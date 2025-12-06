#!/usr/bin/env python3
"""
Phase 1 Workflow: Video Analysis & Moment Detection
===================================================

Phase 1 analyseert de video en detecteert moments, maar genereert nog geen clips.
Pipeline: download → transcribe → detect_moments → detect_faces → save_moments_to_db

Output:
- Moments saved to database
- Job status = 'awaiting_selection'
- No clips generated yet

Security:
- JSONB injection prevention via Pydantic validation
- XSS prevention via HTML entity encoding
- Input validation for all untrusted data
"""

import os
import sys
import logging
from typing import Dict, Any
from datetime import datetime, timezone
from celery import chain

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.celery_app import celery_app
from core.database_pool import get_db_session

# SECURITY FIX: Import validation schemas for JSONB injection and XSS prevention
from agents2.security.validation_schemas import (
    validate_face_coordinates,
    sanitize_ai_text
)

logger = logging.getLogger(__name__)


def create_phase1_workflow(job_id: str, job_data: Dict[str, Any]):
    """
    Create Phase 1 workflow: Analyze video and detect moments

    Pipeline:
        download → transcribe → detect_moments → detect_faces → save_moments

    Output:
        - Moments saved to database
        - Job status = 'awaiting_selection'
        - No clips generated yet

    Args:
        job_id: Job UUID
        job_data: Job configuration (video_url, etc.)

    Returns:
        Celery chain workflow
    """
    logger.info(f"🎬 Creating Phase 1 workflow for job {job_id}")

    # Import tasks from main video_processing module
    from tasks.video_processing import download_video, transcribe_audio, detect_moments, detect_faces

    workflow = chain(
        download_video.s(job_id, job_data),
        transcribe_audio.s(),
        detect_moments.s(),
        detect_faces.s(),
        save_moments_to_db.s(job_id)  # NEW: Save and stop here
    )

    logger.info(f"✅ Phase 1 workflow created for job {job_id}")
    return workflow


@celery_app.task(
    bind=True,
    name='tasks.video_processing_phase1.save_moments_to_db',
    acks_late=True,  # Acknowledge after completion (prevents message loss on worker crash)
    autoretry_for=(Exception,),  # Auto-retry on any exception
    retry_backoff=True,  # Exponential backoff: 2^retry_count seconds
    retry_backoff_max=600,  # Max backoff: 10 minutes
    max_retries=3  # Max 3 retries before final failure
)
def save_moments_to_db(self, task_data: Dict[str, Any], job_id: str):
    """
    Save detected moments to database and PAUSE for admin configuration

    Context7 Validated: Celery pause patterns (trust score 9.1)
    Pattern: Stop chain execution, save state to DB, create new chain on resume

    Changes from original:
    - BEFORE: Set phase to 'awaiting_selection' (User UI auto-flow)
    - AFTER: Set phase to 'awaiting_admin_config' (Admin flow - pause for config)
    - NEW: Store Phase 1 results in pipeline_config.phase1_results for review
    - NEW: Do NOT auto-continue to Phase 2 (admin must explicitly start via API)

    Input task_data contains:
        - moments: List of detected moments
        - faces: Face detection results
        - video_path: Path to downloaded video
        - transcript: Transcription data

    Updates:
        - Creates Moment records in database
        - Sets job.phase = 'awaiting_admin_config' (PAUSE POINT)
        - Sets job.status = 'paused_for_config'
        - Sets job.progress = 60% (Phase 1 complete)
        - Stores Phase 1 results in pipeline_config for admin review
    """
    # IDEMPOTENCY CHECK: Prevent duplicate execution
    # Context7: Idempotent task design (trust score 9.0)
    with get_db_session() as check_session:
        from core.database_manager import Job
        job = check_session.query(Job).filter(Job.id == job_id).first()
        if job and job.phase == 'awaiting_admin_config':
            logger.info(f"[{job_id}] Task already completed (idempotency check). Skipping.")
            return {
                'success': True,
                'job_id': job_id,
                'phase': 'awaiting_admin_config',
                'message': 'Task already completed (idempotent)',
                'idempotent_skip': True
            }

    try:
        logger.info(f"[{job_id}] Saving moments to database...")

        viral_moments = task_data.get('moments', [])
        all_faces = task_data.get('faces', [])  # Extract faces for Phase 2

        if not viral_moments:
            logger.warning(f"[{job_id}] No moments detected in video")
            # Don't fail - just mark as awaiting selection with 0 moments

        with get_db_session() as session:
            from core.database_manager import Job, Moment

            # Get job
            job = session.query(Job).filter(Job.id == job_id).first()
            if not job:
                raise ValueError(f"Job {job_id} not found")

            # Save each moment
            saved_count = 0
            for idx, moment in enumerate(viral_moments):
                # SECURITY FIX 3: Sanitize AI-generated text to prevent stored XSS
                # Context7: OWASP XSS Prevention - HTML entity encoding
                description = sanitize_ai_text(moment.get('description', ''), max_length=500)
                sentence_text = sanitize_ai_text(
                    moment.get('sentence_text', moment.get('sentence', '')),
                    max_length=1000
                )

                # Extract AI transparency data (DEBUG_VIEWER_V2)
                reasoning = moment.get('reasoning')
                if reasoning:
                    # SECURITY FIX 3b: Sanitize reasoning field (AI-generated)
                    reasoning = sanitize_ai_text(str(reasoning), max_length=500)

                engagement_drivers = moment.get('engagement_drivers', [])
                if not isinstance(engagement_drivers, list):
                    engagement_drivers = []

                moment_record = Moment(
                    job_id=job_id,
                    moment_index=idx,
                    start_time=moment.get('start_time', 0),
                    end_time=moment.get('end_time', 0),
                    duration=moment.get('end_time', 0) - moment.get('start_time', 0),
                    description=description,  # SANITIZED
                    sentence_text=sentence_text,  # SANITIZED
                    keywords=moment.get('keywords', []),
                    viral_score=int(moment.get('viral_score', moment.get('score', 0))),
                    is_selected=False,
                    # NEW: AI Transparency fields for debug viewer
                    reasoning=reasoning,  # SANITIZED
                    engagement_drivers=engagement_drivers
                )
                session.add(moment_record)
                saved_count += 1

                logger.info(
                    f"  💾 Moment {idx}: {moment.get('start_time', 0):.1f}s-{moment.get('end_time', 0):.1f}s "
                    f"(viral_score={moment.get('viral_score', 0)}, reasoning={'✓' if reasoning else '✗'})"
                )

            # 🔥 NEW: Update job phase to awaiting_admin_config (PAUSE POINT)
            job.phase = 'awaiting_admin_config'  # CHANGED FROM: 'awaiting_selection'
            job.status = 'paused_for_config'      # CHANGED FROM: 'processing'
            job.progress = 60                      # CHANGED FROM: 50
            job.current_step = 'Phase 1 Complete - Ready for Admin Configuration'

            # Update job metadata from detection results
            if task_data.get('content_type'):
                job.content_type = task_data.get('content_type')
            if task_data.get('viral_score'):
                job.viral_score = task_data.get('viral_score')
            if task_data.get('keywords'):
                job.keywords = task_data.get('keywords')
            if task_data.get('video_duration'):
                job.video_duration = task_data.get('video_duration')
            if task_data.get('analysis_mode'):
                job.analysis_mode = task_data.get('analysis_mode')
            if task_data.get('video_title'):
                job.youtube_title = task_data.get('video_title')

            job.total_moments = len(viral_moments)

            # 🔥 NEW: Store Phase 1 results in pipeline_config for admin review
            # Context7 Validated: JSONB state storage pattern (trust score 9.1)
            if not job.pipeline_config:
                job.pipeline_config = {}

            job.pipeline_config['phase1_results'] = {
                'moments_detected': saved_count,
                'faces_detected': len(all_faces),
                'video_duration': float(job.video_duration) if job.video_duration else 0,
                'transcription_length': len(job.transcription_text) if job.transcription_text else 0,
                'completed_at': datetime.now(timezone.utc).isoformat(),
                'analysis_mode': job.analysis_mode or 'hybrid',
                'content_type': job.content_type or 'spoken'
            }

            # SECURITY FIX 2: Validate face coordinates before storing in JSONB column
            # Context7: Pydantic validation for JSONB injection prevention
            try:
                validated_faces = validate_face_coordinates(all_faces)
                logger.info(f"[{job_id}] ✅ Validated {len(validated_faces)} face coordinates")
            except ValueError as e:
                logger.error(f"[{job_id}] ⚠️ Face validation failed: {e}")
                # Use empty list if validation fails (fail securely)
                validated_faces = []

            # 🔥 NEW: Store VALIDATED faces for Phase 2 (needed for face-focused crop)
            job.pipeline_config['phase1_faces'] = validated_faces

            session.commit()

            logger.info(f"[{job_id}] ✅ Saved {saved_count} moments. Phase 1 complete.")
            logger.info(f"[{job_id}] ⏸️ Pipeline PAUSED at awaiting_admin_config")
            logger.info(f"[{job_id}] 📊 Phase 1 results stored in pipeline_config (moments={saved_count}, faces={len(all_faces)})")
            logger.info(f"[{job_id}] 🔧 Next: Admin must configure Phase 2 via /api/pipeline/{job_id}/configure-phase2")

            return {
                'success': True,
                'job_id': job_id,
                'phase': 'awaiting_admin_config',  # CHANGED FROM: 'awaiting_selection'
                'moments_count': saved_count,
                'faces_count': len(all_faces),
                'next_action': 'Admin must configure Phase 2 OR user selects moments (backwards compatible)',
                'message': 'Phase 1 complete. Pipeline paused for admin configuration.',
                **task_data  # Pass through data for potential Phase 2
            }

    except Exception as e:
        logger.error(f"[{job_id}] ❌ Error saving moments: {e}")
        logger.info(f"[{job_id}] 🔄 Celery will auto-retry with exponential backoff (retry {self.request.retries}/3)")

        # Rollback happened automatically via context manager (get_db_session)
        # autoretry_for will handle retry logic with exponential backoff
        # No need for manual retry - raise exception to trigger autoretry
        raise  # Re-raise to trigger autoretry_for mechanism
