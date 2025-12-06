#!/usr/bin/env python3
"""
Test script to run the full video processing pipeline on the political interview video
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the agents directly
from agents2.audio_processing.audio_transcriber import FastAudioTranscriber
from agents2.moment_detection.moment_detector import MomentDetector
from agents2.face_detection.face_detector_mediapipe import SimpleFaceDetector
from agents2.intelligent_cropping.intelligent_cropper import IntelligentCropper
from agents2.video_processing.video_cutter import VideoCutter

def run_pipeline():
    """Run the full pipeline for the political interview"""
    job_id = '19499831-4f73-4fc5-baac-71d137097b7d'  # Updated to available job_id

    # Input paths
    video_path = f'./io/input/{job_id}/video_1751933560.mp4'
    audio_path = f'./io/input/{job_id}/video_1751933560_audio.mp3'

    logger.info(f"🎬 Starting pipeline test for job {job_id}")
    logger.info(f"📹 Video: {video_path}")
    logger.info(f"🎵 Audio: {audio_path}")

    # Step 1: Transcribe audio (already exists, so we'll skip or use existing)
    logger.info("\n" + "="*80)
    logger.info("STEP 1: Audio Transcription")
    logger.info("="*80)

    transcriber = FastAudioTranscriber()
    transcription_result = transcriber.transcribe_audio({
        "video_path": video_path,
        "method": "auto"
    })

    logger.info(f"✅ Transcription completed")
    logger.info(f"   Method: {transcription_result.get('method_used')}")
    logger.info(f"   Language: {transcription_result.get('language')}")
    logger.info(f"   Transcript length: {len(transcription_result.get('transcript', ''))} chars")

    # Step 2: Detect moments
    logger.info("\n" + "="*80)
    logger.info("STEP 2: Moment Detection")
    logger.info("="*80)

    detector = MomentDetector()
    moment_input = {
        'video_path': video_path,
        'audio_path': audio_path,
        'transcript': transcription_result['transcript'],
        'language': transcription_result.get('language', 'en'),
        'output_types': ['viral', 'key_highlights', 'summary'],
        'content_type': 'spoken',  # Political interview
        'audio_confidence': 0.9,
        'audio_analysis': {'success': True, 'method': 'metadata_full', 'fallback': False},
        'youtube_metadata': {
            'title': 'Political Interview Test',
            'description': 'Test of political debate content detection'
        },
        'video_title': 'Political Interview Test',
        'user_intent': 'auto',
        'constraints_override': {
            "target_len": 30,
            "min_duration": 12,
            "max_duration": 45,
            "max_moments": 8,  # Should be 8 for political content
            "topk": 30,
            "min_conf": 0.15,  # Lower for political content
            "min_gap": 0.5,
            "cluster_gap_s": 8.0,
            "snap_search_radius_s": 1.5,
            "min_lead_in": 0.35,
            "min_lead_out": 0.6,
            "audio_path": audio_path,
            "video_path": video_path,
        }
    }

    moment_result = detector.detect_moments(moment_input)

    if moment_result['success']:
        moments_count = len(moment_result.get('moments', []))
        logger.info(f"\n🎯 MOMENT DETECTION RESULTS:")
        logger.info(f"   Total moments detected: {moments_count}")
        logger.info(f"   Content type: {moment_result.get('content_type')}")
        logger.info(f"   Analysis mode: {moment_result.get('analysis_mode')}")
        logger.info(f"   Viral score: {moment_result.get('viral_score')}")

        logger.info(f"\n📋 DETECTED MOMENTS:")
        for i, moment in enumerate(moment_result.get('moments', []), 1):
            logger.info(f"   {i}. {moment.get('start_time', 0):.1f}s - {moment.get('end_time', 0):.1f}s")
            logger.info(f"      Description: {moment.get('description', 'N/A')[:100]}...")
            logger.info(f"      Confidence: {moment.get('confidence', 0):.2f}")
    else:
        logger.error(f"❌ Moment detection failed: {moment_result.get('error')}")
        return

    # Step 3: Face detection (optional, can be skipped for speed)
    logger.info("\n" + "="*80)
    logger.info("STEP 3: Face Detection (skipped for speed)")
    logger.info("="*80)

    # Step 4: Video cutting
    logger.info("\n" + "="*80)
    logger.info("STEP 4: Video Cutting")
    logger.info("="*80)

    # Convert moments to cuts
    cuts = []
    for i, moment in enumerate(moment_result.get('moments', [])):
        cuts.append({
            'start_time': moment.get('start_time', i * 20),
            'end_time': moment.get('end_time', (i * 20) + 15),
            'output_name': f'clip_{i+1}',
            'keywords': moment.get('keywords', []),
            'viral_score': moment.get('viral_score'),
            'sentence_text': moment.get('sentence_text', ''),
            'description': moment.get('description', '')
        })

    logger.info(f"   Cutting {len(cuts)} clips from video...")

    cutter = VideoCutter()
    cut_result = cutter.cut_video({
        'video_path': video_path,
        'cuts': cuts,
        'output_path': f'./io/output/{job_id}',
        'target_aspect_ratio': '9:16'
    })

    if cut_result['success']:
        clips_created = len(cut_result.get('cut_videos', []))
        logger.info(f"\n✅ VIDEO CUTTING COMPLETED!")
        logger.info(f"   Clips created: {clips_created}")

        logger.info(f"\n📊 FINAL RESULTS:")
        logger.info(f"   {'='*60}")
        logger.info(f"   Job ID: {job_id}")
        logger.info(f"   Content Type: {moment_result.get('content_type')}")
        logger.info(f"   Moments Detected: {moments_count}")
        logger.info(f"   Clips Created: {clips_created}")
        logger.info(f"   Analysis Mode: {moment_result.get('analysis_mode')}")
        logger.info(f"   {'='*60}")

        logger.info(f"\n🎉 COMPARISON:")
        logger.info(f"   OLD: 1 clip (voor content-aware detection)")
        logger.info(f"   NEW: {clips_created} clips (met content-aware detection)")
        logger.info(f"   IMPROVEMENT: {clips_created}x more clips! ✨")

    else:
        logger.error(f"❌ Video cutting failed: {cut_result.get('error')}")

if __name__ == '__main__':
    try:
        run_pipeline()
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}", exc_info=True)
