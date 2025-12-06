"""
Debug Wrapper - Agent Wrapper voor Debug Output Logging
========================================================

Deze wrapper maakt het mogelijk om bestaande agents debug functionaliteit te geven
ZONDER hun bestaande code te wijzigen. Perfect voor backwards compatibility.

Usage:
    from agents2.shared.utils import debug_wrapper
    from agents2.video_processing.video_downloader import VideoDownloader

    # Wrap the agent
    downloader = VideoDownloader()
    result = debug_wrapper.execute_agent(
        job_id="abc-123",
        step_name="download_video",
        agent_callable=downloader.download_video,
        agent_input={'url': 'https://...', 'output_path': './io/'},
        extract_debug_output=lambda result: {
            'video_path': result.get('video_path'),
            'thumbnail': generate_thumbnail(result.get('video_path')),
            'duration': result.get('duration'),
            'resolution': f"{result.get('width')}x{result.get('height')}"
        }
    )
"""
import logging
from typing import Callable, Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def execute_agent(
    job_id: str,
    step_name: str,
    agent_callable: Callable,
    agent_input: Dict[str, Any],
    extract_debug_output: Optional[Callable[[Dict], Dict]] = None,
    auto_generate_thumbnail: bool = True
):
    """
    Execute an agent with automatic debug output logging

    Args:
        job_id: Job ID for debug logging
        step_name: Step name (e.g., 'download_video', 'transcribe_audio')
        agent_callable: The agent function/method to call
        agent_input: Input data to pass to agent
        extract_debug_output: Optional function to extract debug-relevant data from result
        auto_generate_thumbnail: Automatically generate thumbnail if video_path in result

    Returns:
        Agent result (unchanged)

    Example:
        downloader = VideoDownloader()
        result = execute_agent(
            job_id="abc-123",
            step_name="download_video",
            agent_callable=downloader.download_video,
            agent_input={'url': 'https://youtube.com/...', 'output_path': './io/'},
            extract_debug_output=lambda r: {
                'video_path': r.get('video_path'),
                'duration': r.get('duration')
            }
        )
    """
    from agents2.shared.utils.video_helpers import save_step_output, generate_thumbnail

    try:
        # Log start
        save_step_output(job_id, step_name, 'in_progress')

        # Execute agent
        logger.info(f"🔄 Executing agent: {step_name} for job {job_id}")
        result = agent_callable(agent_input)

        # Check if agent succeeded
        if not result.get('success', False):
            error = result.get('error', 'Unknown error')
            save_step_output(job_id, step_name, 'failed', error=error)
            logger.error(f"❌ Agent {step_name} failed: {error}")
            return result

        # Extract debug output
        debug_output = {}

        if extract_debug_output:
            try:
                debug_output = extract_debug_output(result)
            except Exception as e:
                logger.warning(f"Failed to extract debug output: {e}")
                debug_output = {}

        # Auto-generate thumbnail if video_path exists
        if auto_generate_thumbnail and result.get('video_path'):
            try:
                thumbnail = generate_thumbnail(
                    video_path=result['video_path'],
                    timestamp=1.0,
                    max_width=400
                )
                if thumbnail:
                    debug_output['thumbnail'] = thumbnail
            except Exception as e:
                logger.warning(f"Failed to generate thumbnail: {e}")

        # Include basic result data if no extract function provided
        if not debug_output and result:
            debug_output = {
                k: v for k, v in result.items()
                if k not in ['success', 'error'] and v is not None
            }

        # Log success
        save_step_output(
            job_id=job_id,
            step_name=step_name,
            status='success',
            output=debug_output
        )

        logger.info(f"✅ Agent {step_name} completed successfully")
        return result

    except Exception as e:
        # Log failure
        save_step_output(
            job_id=job_id,
            step_name=step_name,
            status='failed',
            error=str(e)
        )
        logger.error(f"❌ Agent {step_name} crashed: {e}")
        raise


def wrap_download_video(job_id: str, agent_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience wrapper for VideoDownloader agent

    Example:
        from agents2.shared.utils import debug_wrapper
        result = debug_wrapper.wrap_download_video(
            job_id="abc-123",
            agent_input={'url': 'https://...', 'output_path': './io/'}
        )
    """
    from agents2.video_processing.video_downloader import VideoDownloader
    from agents2.shared.utils.video_helpers import get_duration, get_resolution

    downloader = VideoDownloader()

    def extract_output(result):
        output = {
            'video_path': result.get('video_path'),
            'duration': result.get('duration', 0),
            'size': result.get('size', 0),
            'title': result.get('title', 'Unknown')
        }

        # Try to get resolution if not in result
        if result.get('video_path'):
            try:
                resolution = get_resolution(result['video_path'])
                if resolution:
                    output['resolution'] = resolution
            except:
                pass

        return output

    return execute_agent(
        job_id=job_id,
        step_name='download_video',
        agent_callable=downloader.download_video,
        agent_input=agent_input,
        extract_debug_output=extract_output,
        auto_generate_thumbnail=True
    )


def wrap_transcribe_audio(job_id: str, agent_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience wrapper for AudioTranscriber agent

    Example:
        from agents2.shared.utils import debug_wrapper
        result = debug_wrapper.wrap_transcribe_audio(
            job_id="abc-123",
            agent_input={'video_path': './io/video.mp4'}
        )
    """
    from agents2.audio_processing.audio_transcriber import AudioTranscriber

    transcriber = AudioTranscriber()

    def extract_output(result):
        transcript_text = result.get('transcript', '')

        return {
            'transcript': transcript_text[:500] + '...' if len(transcript_text) > 500 else transcript_text,
            'full_text_length': len(transcript_text),
            'segments_count': len(result.get('segments', [])),
            'language': result.get('language', 'unknown')
        }

    return execute_agent(
        job_id=job_id,
        step_name='transcribe_audio',
        agent_callable=transcriber.transcribe,
        agent_input=agent_input,
        extract_debug_output=extract_output,
        auto_generate_thumbnail=False
    )


def wrap_detect_moments(job_id: str, agent_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience wrapper for MomentDetector agent

    Example:
        from agents2.shared.utils import debug_wrapper
        result = debug_wrapper.wrap_detect_moments(
            job_id="abc-123",
            agent_input={'transcript': {...}}
        )
    """
    from agents2.moment_detection.moment_detector import MomentDetector

    detector = MomentDetector()

    def extract_output(result):
        moments = result.get('moments', [])

        return {
            'moments_count': len(moments),
            'top_moments': [
                {
                    'description': m.get('description', ''),
                    'start_time': m.get('start_time', 0),
                    'end_time': m.get('end_time', 0),
                    'viral_score': m.get('viral_score', 0)
                }
                for m in moments[:3]  # Top 3
            ]
        }

    return execute_agent(
        job_id=job_id,
        step_name='detect_moments',
        agent_callable=detector.detect,
        agent_input=agent_input,
        extract_debug_output=extract_output,
        auto_generate_thumbnail=False
    )


def wrap_detect_faces(job_id: str, agent_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience wrapper for FaceDetector agent

    Example:
        from agents2.shared.utils import debug_wrapper
        result = debug_wrapper.wrap_detect_faces(
            job_id="abc-123",
            agent_input={'video_path': './io/video.mp4'}
        )
    """
    from agents2.face_detection.face_detector import FaceDetector
    from agents2.shared.utils.video_helpers import generate_face_screenshots

    detector = FaceDetector()

    def extract_output(result):
        faces = result.get('faces', [])
        video_path = agent_input.get('video_path')

        face_screenshots = []
        if video_path and faces:
            try:
                face_screenshots = generate_face_screenshots(
                    faces=faces,
                    video_path=video_path,
                    job_id=job_id,
                    max_faces=5
                )
            except Exception as e:
                logger.warning(f"Failed to generate face screenshots: {e}")

        return {
            'face_count': len(faces),
            'face_screenshots': face_screenshots,
            'primary_speaker': faces[0] if faces else None
        }

    return execute_agent(
        job_id=job_id,
        step_name='detect_faces',
        agent_callable=detector.detect,
        agent_input=agent_input,
        extract_debug_output=extract_output,
        auto_generate_thumbnail=False
    )


def wrap_intelligent_crop(job_id: str, agent_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience wrapper for IntelligentCropper agent

    Example:
        from agents2.shared.utils import debug_wrapper
        result = debug_wrapper.wrap_intelligent_crop(
            job_id="abc-123",
            agent_input={'video_path': './io/video.mp4', 'faces': [...]}
        )
    """
    from agents2.intelligent_cropping.intelligent_cropper import IntelligentCropper
    from agents2.shared.utils.video_helpers import generate_crop_comparison

    cropper = IntelligentCropper()

    def extract_output(result):
        crop_settings = result.get('crop_settings', {})
        video_path = agent_input.get('video_path')

        comparison_image = None
        if video_path and crop_settings:
            try:
                comparison_image = generate_crop_comparison(
                    video_path=video_path,
                    crop_settings=crop_settings,
                    job_id=job_id,
                    timestamp=5.0
                )
            except Exception as e:
                logger.warning(f"Failed to generate crop comparison: {e}")

        return {
            'crop_settings': crop_settings,
            'comparison_image': comparison_image,
            'target_aspect_ratio': '9:16'
        }

    return execute_agent(
        job_id=job_id,
        step_name='intelligent_crop',
        agent_callable=cropper.calculate_crop,
        agent_input=agent_input,
        extract_debug_output=extract_output,
        auto_generate_thumbnail=False
    )


def wrap_cut_videos(job_id: str, agent_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience wrapper for VideoCutter agent

    Example:
        from agents2.shared.utils import debug_wrapper
        result = debug_wrapper.wrap_cut_videos(
            job_id="abc-123",
            agent_input={'video_path': './io/video.mp4', 'moments': [...], 'crop_settings': {...}}
        )
    """
    from agents2.video_processing.video_cutter_dynamic import VideoCutter

    cutter = VideoCutter()

    def extract_output(result):
        clips = result.get('clips', [])

        return {
            'clips_generated': len(clips),
            'clips': [
                {
                    'path': clip.get('path', ''),
                    'thumbnail': clip.get('thumbnail'),
                    'duration': clip.get('duration', 0),
                    'moment_description': clip.get('description', '')
                }
                for clip in clips
            ]
        }

    return execute_agent(
        job_id=job_id,
        step_name='cut_videos',
        agent_callable=cutter.cut,
        agent_input=agent_input,
        extract_debug_output=extract_output,
        auto_generate_thumbnail=False
    )
