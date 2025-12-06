"""
File Serving API Routes
=======================

Serve debug files (images, videos) from io/ directory for debug viewer.

Priority 2 (DEBUG_VIEWER_V2.md) - Fix crop comparison image display
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/io/debug/{job_id}/{filename}")
async def serve_debug_file(job_id: str, filename: str):
    """
    Serve debug images/videos from io/debug/{job_id}/ directory

    Examples:
        - GET /api/files/io/debug/{job_id}/crop_comparison.jpg
        - GET /api/files/io/debug/{job_id}/original_temp.jpg
        - GET /api/files/io/debug/{job_id}/cropped_temp.jpg

    Args:
        job_id: Job UUID
        filename: File name to serve

    Returns:
        FileResponse with the requested file

    Raises:
        HTTPException: 404 if file not found
    """
    file_path = Path(f"./io/debug/{job_id}/{filename}")

    if not file_path.exists():
        logger.warning(f"Debug file not found: {file_path}")
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {filename}"
        )

    logger.info(f"Serving debug file: {file_path}")
    return FileResponse(file_path)


@router.get("/io/debug/{job_id}/faces/{filename}")
async def serve_face_screenshot(job_id: str, filename: str):
    """
    Serve face screenshots from io/debug/{job_id}/faces/ directory

    Examples:
        - GET /api/files/io/debug/{job_id}/faces/face_0.jpg
        - GET /api/files/io/debug/{job_id}/faces/face_1.jpg

    Args:
        job_id: Job UUID
        filename: Face screenshot filename (e.g., face_0.jpg)

    Returns:
        FileResponse with the face screenshot

    Raises:
        HTTPException: 404 if file not found
    """
    file_path = Path(f"./io/debug/{job_id}/faces/{filename}")

    if not file_path.exists():
        logger.warning(f"Face screenshot not found: {file_path}")
        raise HTTPException(
            status_code=404,
            detail=f"Face screenshot not found: {filename}"
        )

    logger.info(f"Serving face screenshot: {file_path}")
    return FileResponse(file_path)


@router.get("/io/clips/{job_id}/{filename}")
async def serve_clip_file(job_id: str, filename: str):
    """
    Serve generated clips from io/clips/{job_id}/ directory

    Examples:
        - GET /api/files/io/clips/{job_id}/clip_0.mp4
        - GET /api/files/io/clips/{job_id}/clip_1.mp4

    Args:
        job_id: Job UUID
        filename: Clip filename

    Returns:
        FileResponse with the video clip

    Raises:
        HTTPException: 404 if file not found
    """
    file_path = Path(f"./io/clips/{job_id}/{filename}")

    if not file_path.exists():
        logger.warning(f"Clip file not found: {file_path}")
        raise HTTPException(
            status_code=404,
            detail=f"Clip file not found: {filename}"
        )

    logger.info(f"Serving clip file: {file_path}")
    return FileResponse(file_path)


@router.get("/io/downloads/{job_id}/{filename}")
async def serve_download_file(job_id: str, filename: str):
    """
    Serve downloaded videos from io/downloads/{job_id}/ directory

    Examples:
        - GET /api/files/io/downloads/{job_id}/video.mp4
        - GET /api/files/io/downloads/{job_id}/video_thumb.jpg

    Args:
        job_id: Job UUID
        filename: Downloaded file name

    Returns:
        FileResponse with the file

    Raises:
        HTTPException: 404 if file not found
    """
    file_path = Path(f"./io/downloads/{job_id}/{filename}")

    if not file_path.exists():
        logger.warning(f"Download file not found: {file_path}")
        raise HTTPException(
            status_code=404,
            detail=f"Download file not found: {filename}"
        )

    logger.info(f"Serving download file: {file_path}")
    return FileResponse(file_path)
