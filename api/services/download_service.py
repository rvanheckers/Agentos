"""
Download Service - File download functionaliteit voor AgentOS

Centrale service voor alle download operaties (clips, jobs, zip bestanden).
Ondersteunt zowel admin als user endpoints met is_admin parameter.
Gebruikt MediaSource voor flexibele file handling (local/cloud storage).
Elimineert code duplicatie tussen verschillende download endpoints.
"""
from typing import Dict, Any, Optional, List
import os
import zipfile
import io
from datetime import datetime
from fastapi.responses import FileResponse, StreamingResponse
from fastapi import HTTPException
from api.services.media_source import MediaSourceFactory, LocalMediaSource
import logging

logger = logging.getLogger(__name__)


class DownloadService:
    """Central service for all download-related operations"""
    
    def __init__(self):
        self.base_output_path = "./io/output"
    
    def download_clip(self, job_id: str, clip_id: str, is_admin: bool = False) -> FileResponse:
        """Download a specific clip file
        Admin can download any clip, users can download their own clips"""
        try:
            logger.info(f"Downloading clip {clip_id} from job {job_id} (admin: {is_admin})")
            
            # Use MediaSourceFactory for proper path resolution
            output_dir_source = MediaSourceFactory.create(f"./io/output/{job_id}")
            output_dir = output_dir_source.get_local_path()
            
            # Validate the output directory exists
            is_valid, error_msg = output_dir_source.validate()
            if not is_valid and not os.path.exists(output_dir):
                if is_admin:
                    # Admin can create mock data for testing
                    os.makedirs(output_dir, exist_ok=True)
                    mock_clip_path = os.path.join(output_dir, f"clip_{clip_id}.mp4")
                    with open(mock_clip_path, "wb") as f:
                        f.write(b"Mock video file content for testing")
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Job output directory not found: {job_id}"
                    )
            
            # Try different possible clip filenames
            possible_filenames = [
                f"clip_{clip_id}.mp4",
                f"clip{clip_id}.mp4", 
                f"video_{clip_id}.mp4",
                f"{clip_id}.mp4"
            ]
            
            clip_file_path = None
            for filename in possible_filenames:
                potential_clip_path = f"./io/output/{job_id}/{filename}"
                try:
                    clip_source = MediaSourceFactory.create(potential_clip_path)
                    is_valid, _ = clip_source.validate()
                    if is_valid:
                        clip_file_path = clip_source.get_local_path()
                        break
                except Exception:
                    continue
            
            if not clip_file_path:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Clip file not found: {clip_id} in job {job_id}"
                )
            
            # Additional admin privileges
            if is_admin:
                # Admin gets additional metadata in headers
                headers = {
                    "Content-Disposition": f"attachment; filename={job_id}_{clip_id}.mp4",
                    "X-Job-ID": job_id,
                    "X-Clip-ID": clip_id,
                    "X-Download-Time": datetime.now().isoformat(),
                    "X-Admin-Download": "true"
                }
            else:
                headers = {
                    "Content-Disposition": f"attachment; filename={job_id}_{clip_id}.mp4"
                }
            
            return FileResponse(
                path=clip_file_path,
                media_type="video/mp4",
                filename=f"{job_id}_{clip_id}.mp4",
                headers=headers
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to download clip {clip_id} from job {job_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to download clip: {str(e)}")
    
    def download_job_files(self, job_id: str, is_admin: bool = False) -> StreamingResponse:
        """Download all clips from a job as a zip file
        Admin can download any job files, users can download their own job files"""
        try:
            logger.info(f"Downloading all files for job {job_id} (admin: {is_admin})")
            
            # Use MediaSourceFactory for proper path resolution
            output_dir_source = MediaSourceFactory.create(f"./io/output/{job_id}")
            output_dir = output_dir_source.get_local_path()
            
            # Validate the output directory exists
            is_valid, error_msg = output_dir_source.validate()
            if not is_valid and not os.path.exists(output_dir):
                if is_admin:
                    # Admin can create mock data for testing
                    os.makedirs(output_dir, exist_ok=True)
                    mock_clips = ["clip_1.mp4", "clip_2.mp4", "clip_3.mp4"]
                    for clip_name in mock_clips:
                        mock_clip_path = os.path.join(output_dir, clip_name)
                        with open(mock_clip_path, "wb") as f:
                            f.write(f"Mock video content for {clip_name}".encode())
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Job output directory not found: {job_id}"
                    )
            
            # Create zip file in memory
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add all video files in the directory
                for filename in os.listdir(output_dir):
                    if filename.endswith(('.mp4', '.avi', '.mov', '.mkv')):
                        file_path = os.path.join(output_dir, filename)
                        zip_file.write(file_path, filename)
                
                # Admin gets additional metadata file
                if is_admin:
                    metadata = f"""Job: {job_id}
Downloaded: {datetime.now().isoformat()}  
Admin Download: Yes
Files included: {len([f for f in os.listdir(output_dir) if f.endswith(('.mp4', '.avi', '.mov', '.mkv'))])}
"""
                    zip_file.writestr("download_metadata.txt", metadata)
            
            zip_buffer.seek(0)
            
            # Prepare headers
            if is_admin:
                headers = {
                    "Content-Disposition": f"attachment; filename={job_id}_clips_admin.zip",
                    "X-Job-ID": job_id,
                    "X-Download-Time": datetime.now().isoformat(),
                    "X-Admin-Download": "true"
                }
            else:
                headers = {
                    "Content-Disposition": f"attachment; filename={job_id}_clips.zip"
                }
            
            return StreamingResponse(
                io.BytesIO(zip_buffer.read()),
                media_type="application/zip",
                headers=headers
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to download job files for {job_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to download job files: {str(e)}")
    
    def get_download_stats(self, job_id: Optional[str] = None, is_admin: bool = False) -> Dict[str, Any]:
        """Get download statistics
        Admin sees all stats, users see limited stats"""
        try:
            if job_id:
                # Stats for specific job
                output_dir = f"./io/output/{job_id}"
                if os.path.exists(output_dir):
                    files = [f for f in os.listdir(output_dir) if f.endswith(('.mp4', '.avi', '.mov', '.mkv'))]
                    total_size = sum(os.path.getsize(os.path.join(output_dir, f)) for f in files)
                    
                    stats = {
                        "job_id": job_id,
                        "files_available": len(files),
                        "total_size_bytes": total_size,
                        "total_size_mb": round(total_size / (1024 * 1024), 2),
                        "files": files if is_admin else len(files)  # Admin sees file names
                    }
                else:
                    stats = {
                        "job_id": job_id,
                        "files_available": 0,
                        "total_size_bytes": 0,
                        "total_size_mb": 0,
                        "files": [] if is_admin else 0
                    }
            else:
                # General download stats
                output_base_dir = "./io/output"
                if os.path.exists(output_base_dir):
                    job_dirs = [d for d in os.listdir(output_base_dir) if os.path.isdir(os.path.join(output_base_dir, d))]
                    total_jobs = len(job_dirs)
                    total_files = 0
                    total_size = 0
                    
                    for job_dir in job_dirs:
                        job_path = os.path.join(output_base_dir, job_dir)
                        files = [f for f in os.listdir(job_path) if f.endswith(('.mp4', '.avi', '.mov', '.mkv'))]
                        total_files += len(files)
                        total_size += sum(os.path.getsize(os.path.join(job_path, f)) for f in files)
                    
                    stats = {
                        "total_jobs": total_jobs,
                        "total_files": total_files,
                        "total_size_bytes": total_size,
                        "total_size_mb": round(total_size / (1024 * 1024), 2),
                        "avg_files_per_job": round(total_files / max(total_jobs, 1), 1)
                    }
                    
                    # Admin gets additional details
                    if is_admin:
                        stats["job_directories"] = job_dirs
                else:
                    stats = {
                        "total_jobs": 0,
                        "total_files": 0,
                        "total_size_bytes": 0,
                        "total_size_mb": 0,
                        "avg_files_per_job": 0
                    }
            
            if is_admin:
                stats["admin_access"] = True
                stats["generated_at"] = datetime.now().isoformat()
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get download stats: {e}")
            return {
                "error": str(e),
                "job_id": job_id,
                "admin_access": is_admin
            }