#!/usr/bin/env python3
"""
Reprocess Job Script
====================

Herverwerkt een specifieke job met de nieuwste versie van alle agents.
Gebruikt voor het testen van fixes zoals V3.2.1 split-screen detection.

Usage:
    python reprocess_job.py <job_id>

Example:
    python reprocess_job.py 7df4efda-9fb4-4571-95ee-ee4bafcaef09
"""

import sys
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.celery_app import celery_app
from core.database_pool import get_db_session
from tasks.video_processing import (
    transcribe_audio,
    detect_moments,
    detect_faces,
    intelligent_crop,
    cut_videos,
    finalize_workflow
)
from celery import chain
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def reprocess_job(job_id: str, skip_download: bool = True):
    """
    Herverwerkt een job met de nieuwste agent versies.

    Args:
        job_id: Job UUID om te reprocessen
        skip_download: Skip video download (gebruik bestaande video)
    """

    # Check if video exists
    video_dir = f"./io/input/{job_id}"
    if not os.path.exists(video_dir):
        logger.error(f"❌ Video directory not found: {video_dir}")
        return False

    video_files = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
    if not video_files:
        logger.error(f"❌ No video file found in {video_dir}")
        return False

    video_path = os.path.join(video_dir, video_files[0])
    logger.info(f"✅ Found video: {video_path}")

    # Get job metadata from database
    try:
        with get_db_session() as session:
            from core.database_manager import Job
            job = session.query(Job).filter(Job.id == job_id).first()

            if not job:
                logger.error(f"❌ Job {job_id} not found in database")
                return False

            # Extract data WITHIN session scope (before detachment)
            video_url = job.video_url
            youtube_title = job.youtube_title or 'Unknown'
            video_duration = job.video_duration or 0

            logger.info(f"📺 Job: {youtube_title}")
            logger.info(f"🔗 URL: {video_url}")

            # Reset job status
            job.status = 'processing'
            job.progress = 33
            job.current_step = 'Reprocessing with V3.2.1'
            session.commit()
            logger.info(f"✅ Job reset to processing state")

    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return False

    # Create reprocessing workflow (skip download)
    logger.info(f"\n🔄 Creating reprocessing workflow for job {job_id}")
    logger.info(f"   Using LayoutDetector V3.2.1 with visual edge detection\n")

    # Prepare download_data (as if download just completed)
    download_data = {
        'success': True,
        'job_id': job_id,
        'video_path': video_path,
        'title': youtube_title,
        'duration': video_duration,
        'metadata': {},
        'user_preferences': {'clip_length': 30}
    }

    # Create workflow starting from transcription
    workflow = chain(
        transcribe_audio.s(download_data),
        detect_moments.s(),
        detect_faces.s(),
        intelligent_crop.s(),
        cut_videos.s(),
        finalize_workflow.s()
    )

    logger.info(f"🚀 Launching workflow...")

    # Execute workflow
    try:
        result = workflow.apply_async()
        logger.info(f"✅ Workflow launched!")
        logger.info(f"   Task ID: {result.id}")
        logger.info(f"   Status: {result.status}")
        logger.info(f"\n📊 Monitor progress:")
        logger.info(f"   - Check UI: http://localhost:3000")
        logger.info(f"   - Check logs: tail -f logs/agentos.log")
        logger.info(f"   - Check Celery: celery -A core.celery_app inspect active")
        return True

    except Exception as e:
        logger.error(f"❌ Workflow launch failed: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python reprocess_job.py <job_id>")
        print("\nExample:")
        print("  python reprocess_job.py 7df4efda-9fb4-4571-95ee-ee4bafcaef09")
        sys.exit(1)

    job_id = sys.argv[1]

    print("=" * 70)
    print("🔄 AgentOS Job Reprocessing Script")
    print("=" * 70)
    print(f"\nJob ID: {job_id}")
    print(f"Version: V3.2.1 (Cinema MVP with visual edge detection)")
    print()

    success = reprocess_job(job_id, skip_download=True)

    if success:
        print("\n" + "=" * 70)
        print("✅ SUCCESS: Job reprocessing started!")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("❌ FAILED: Job reprocessing failed")
        print("=" * 70)
        sys.exit(1)


if __name__ == "__main__":
    main()
