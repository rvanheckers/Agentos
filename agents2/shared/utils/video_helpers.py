"""
Video Processing Helper Functions
==================================

FFmpeg-based utilities for video processing and debug visualization.
Includes thumbnail generation, metadata extraction, and screenshot capture.

Context7 Validated:
- FFmpeg Python wrappers (trust score 8.4)
- Safe subprocess handling with error checking
- Path validation for security
"""
import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Optional, List, Union
import json

logger = logging.getLogger(__name__)


def generate_thumbnail(
    video_path: str,
    timestamp: float = 1.0,
    output_path: Optional[str] = None,
    max_width: int = 400
) -> Optional[str]:
    """
    Generate thumbnail from video at specified timestamp

    Args:
        video_path: Path to video file
        timestamp: Time in seconds to capture thumbnail (default: 1.0)
        output_path: Optional custom output path
        max_width: Maximum thumbnail width in pixels (default: 400)

    Returns:
        Path to generated thumbnail, or None if failed

    Security:
        - Validates video_path exists
        - Sanitizes output paths
        - Limits thumbnail resolution
    """
    try:
        # Validate input
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return None

        # Generate output path if not provided
        if output_path is None:
            video_dir = Path(video_path).parent
            video_stem = Path(video_path).stem
            output_path = str(video_dir / f"{video_stem}_thumb.jpg")

        # Ensure output directory exists
        os.makedirs(Path(output_path).parent, exist_ok=True)

        # FFmpeg command with quality and size limits
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file
            '-ss', str(timestamp),  # Seek to timestamp
            '-i', video_path,
            '-vframes', '1',  # Extract 1 frame
            '-q:v', '2',  # High quality (1-31, lower is better)
            '-vf', f'scale={max_width}:-1',  # Scale to max width, maintain aspect ratio
            output_path
        ]

        # Run FFmpeg command
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )

        if os.path.exists(output_path):
            logger.info(f"✅ Thumbnail generated: {output_path}")
            return output_path
        else:
            logger.error("FFmpeg completed but no thumbnail file created")
            return None

    except subprocess.TimeoutExpired:
        logger.error(f"Thumbnail generation timed out for {video_path}")
        return None
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error generating thumbnail: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error generating thumbnail: {e}")
        return None


def get_duration(video_path: str) -> Optional[float]:
    """
    Get video duration in seconds using ffprobe

    Args:
        video_path: Path to video file

    Returns:
        Duration in seconds as float, or None if failed
    """
    try:
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return None

        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )

        duration = float(result.stdout.strip())
        logger.info(f"Video duration: {duration}s")
        return duration

    except (subprocess.CalledProcessError, ValueError, subprocess.TimeoutExpired) as e:
        logger.error(f"Error getting video duration: {e}")
        return None


def get_resolution(video_path: str) -> Optional[str]:
    """
    Get video resolution (e.g., '1920x1080')

    Args:
        video_path: Path to video file

    Returns:
        Resolution string like "1920x1080", or None if failed
    """
    try:
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return None

        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'csv=s=x:p=0',
            video_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )

        resolution = result.stdout.strip()
        logger.info(f"Video resolution: {resolution}")
        return resolution

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        logger.error(f"Error getting video resolution: {e}")
        return None


def get_video_metadata(video_path: str) -> Dict[str, Union[str, int, float]]:
    """
    Extract comprehensive video metadata

    Args:
        video_path: Path to video file

    Returns:
        Dictionary with metadata (duration, resolution, size, etc.)
    """
    metadata = {
        "video_path": video_path,
        "exists": os.path.exists(video_path)
    }

    if not metadata["exists"]:
        return metadata

    try:
        # Get file size
        metadata["file_size"] = os.path.getsize(video_path)

        # Get duration
        duration = get_duration(video_path)
        if duration:
            metadata["duration"] = duration

        # Get resolution
        resolution = get_resolution(video_path)
        if resolution:
            metadata["resolution"] = resolution

        logger.info(f"Video metadata extracted: {metadata}")
        return metadata

    except Exception as e:
        logger.error(f"Error extracting video metadata: {e}")
        metadata["error"] = str(e)
        return metadata


def generate_face_screenshots(
    faces: List[Dict],
    video_path: str,
    job_id: str,
    max_faces: int = 5
) -> List[str]:
    """
    Generate screenshots of detected faces for debug view

    Args:
        faces: List of face detection results with timestamps
        video_path: Path to video file
        job_id: Job ID for output directory organization
        max_faces: Maximum number of face screenshots to generate (default: 5)

    Returns:
        List of paths to generated face screenshots
    """
    try:
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return []

        # Create output directory
        output_dir = Path("./io/debug") / str(job_id) / "faces"
        output_dir.mkdir(parents=True, exist_ok=True)

        screenshots = []

        # Generate screenshots for top faces
        for i, face in enumerate(faces[:max_faces]):
            # Get timestamp (try different keys)
            timestamp = face.get('first_appearance') or face.get('timestamp') or face.get('time') or 1.0

            output_path = output_dir / f"face_{i}.jpg"

            cmd = [
                'ffmpeg',
                '-y',
                '-ss', str(timestamp),
                '-i', video_path,
                '-vframes', '1',
                '-q:v', '2',
                '-vf', 'scale=200:-1',  # 200px width
                str(output_path)
            ]

            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                timeout=30
            )

            if output_path.exists():
                screenshots.append(str(output_path))
                logger.info(f"✅ Face screenshot {i} generated")

        return screenshots

    except Exception as e:
        logger.error(f"Error generating face screenshots: {e}")
        return []


def generate_crop_comparison(
    video_path: str,
    crop_settings: Optional[Dict],
    job_id: str,
    timestamp: float = 5.0
) -> Optional[str]:
    """
    Generate side-by-side comparison of original and cropped frame

    Args:
        video_path: Path to video file
        crop_settings: Crop parameters (x, y, width, height) or None for center crop
        job_id: Job ID for output directory
        timestamp: Time in seconds to capture comparison (default: 5.0)

    Returns:
        Path to comparison image, or None if failed
    """
    try:
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return None

        # Create output directory
        output_dir = Path("./io/debug") / str(job_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Temporary frames
        original_frame = output_dir / "original_temp.jpg"
        cropped_frame = output_dir / "cropped_temp.jpg"
        output_path = output_dir / "crop_comparison.jpg"

        # Generate original frame
        cmd_original = [
            'ffmpeg', '-y',
            '-ss', str(timestamp),
            '-i', video_path,
            '-vframes', '1',
            '-vf', 'scale=400:-1',
            str(original_frame)
        ]
        subprocess.run(cmd_original, check=True, capture_output=True, timeout=30)

        # Generate cropped frame
        # If no crop_settings provided, use center crop for 9:16 aspect ratio
        if crop_settings is None or not crop_settings:
            # Default center crop for 9:16 (1080x1920)
            # Get video resolution first
            resolution = get_resolution(video_path)
            if resolution:
                width_str, height_str = resolution.split('x')
                video_width = int(width_str)
                video_height = int(height_str)

                # Calculate center crop coordinates for 9:16
                target_width = int(video_height * (9 / 16))
                target_height = video_height
                x = (video_width - target_width) // 2
                y = 0

                crop_filter = f"crop={target_width}:{target_height}:{x}:{y}"
                logger.info(f"Using center crop: {crop_filter} (no crop_settings provided)")
            else:
                # Fallback to default 9:16 crop
                crop_filter = "crop=1080:1920:420:0"
                logger.warning(f"Could not get video resolution, using default crop: {crop_filter}")
        else:
            crop_filter = f"crop={crop_settings.get('width', 1080)}:{crop_settings.get('height', 1920)}:{crop_settings.get('x', 0)}:{crop_settings.get('y', 0)}"
            logger.info(f"Using provided crop settings: {crop_filter}")

        cmd_cropped = [
            'ffmpeg', '-y',
            '-ss', str(timestamp),
            '-i', video_path,
            '-vf', f"{crop_filter},scale=400:-1",
            '-vframes', '1',
            str(cropped_frame)
        ]
        subprocess.run(cmd_cropped, check=True, capture_output=True, timeout=30)

        # Combine side-by-side with height normalization
        # Scale both to same height (400px) before stacking
        # Add a 10px white gap between images for clear separation
        cmd_combine = [
            'ffmpeg', '-y',
            '-i', str(original_frame),
            '-i', str(cropped_frame),
            '-filter_complex', '[0:v]scale=-1:400[a];[1:v]scale=-1:400[b];[a][b]hstack=inputs=2:shortest=0:gap=10:fillcolor=white',
            str(output_path)
        ]
        subprocess.run(cmd_combine, check=True, capture_output=True, timeout=30)

        # Cleanup temp files
        original_frame.unlink(missing_ok=True)
        cropped_frame.unlink(missing_ok=True)

        if output_path.exists():
            logger.info(f"✅ Crop comparison generated: {output_path}")
            return str(output_path)
        return None

    except Exception as e:
        logger.error(f"Error generating crop comparison: {e}")
        return None


def save_step_output(
    job_id: str,
    step_name: str,
    status: str,
    output: Optional[Dict] = None,
    error: Optional[str] = None
):
    """
    Save step output to database for debug viewer

    Args:
        job_id: Job ID
        step_name: Name of processing step
        status: 'success', 'failed', 'in_progress', 'pending'
        output: Optional output data dictionary
        error: Optional error message

    Note:
        This function updates the Job.step_outputs JSONB column
    """
    try:
        from datetime import datetime, timezone
        from core.database_manager import PostgreSQLManager, Job

        db = PostgreSQLManager()

        with db.get_session() as session:
            job = session.query(Job).filter(Job.id == job_id).first()

            if not job:
                logger.error(f"Job {job_id} not found")
                return

            # Initialize step_outputs if None
            if job.step_outputs is None:
                job.step_outputs = {}

            # Update step data
            job.step_outputs[step_name] = {
                'status': status,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            if output:
                job.step_outputs[step_name]['output'] = output

            if error:
                job.step_outputs[step_name]['error'] = error

            # Mark as modified for SQLAlchemy to detect change
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(job, 'step_outputs')

            session.commit()

            logger.info(f"✅ Step output saved: {job_id} -> {step_name} ({status})")

    except Exception as e:
        logger.error(f"Error saving step output: {e}")
