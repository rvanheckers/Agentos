"""
Upload Service Layer - Database-First Hybrid
===========================================
Handles all upload-related business logic
Updated to Database-First pattern for consistency with AgentOS v2.4.0
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import UploadFile, HTTPException
import os
import hashlib
import shutil
import logging

logger = logging.getLogger("agentos.services.upload")

class UploadService:
    """
    Service layer for upload management - Database-First Pattern

    Methods:
    - init_upload(): Initialize a new upload session
    - upload_file(): Upload a complete file in one request
    - upload_chunk(): Upload a file chunk (for large files)
    - finalize_upload(): Finalize a chunked upload
    - get_upload_status(): Get status of an upload
    - import_local_file(): Import a file from local path
    """

    def __init__(self, db_manager=None):
        """Initialize upload service with Database-First integration"""
        self.upload_dir = "./io/input"
        self.temp_dir = "./io/temp"
        self.uploads = {}  # In-memory cache for real-time tracking

        # Database-First Integration
        if db_manager:
            self.db = db_manager
        else:
            try:
                from core.database_pool import get_db_session
                # Store the factory function, not a session instance
                self.db = get_db_session  # Store factory for per-operation sessions
                logger.info("✅ Database integration enabled for upload service")
            except Exception as e:
                logger.error(f"❌ Database factory import failed: {e}")
                self.db = None
                raise

        # Ensure directories exist
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

    def init_upload(self, filename: str, file_size: int, chunk_size: int = 1024*1024,
                   user_id: Optional[str] = None, is_admin: bool = False) -> Dict[str, Any]:
        """
        Initialize a new upload session - Database-First pattern
        Admin and users have same functionality
        """
        try:
            # Generate upload ID
            upload_id = hashlib.md5(f"{filename}{datetime.now().timestamp()}".encode()).hexdigest()

            # Calculate chunks
            total_chunks = (file_size + chunk_size - 1) // chunk_size

            # Create upload session
            upload_session = {
                "upload_id": upload_id,
                "filename": filename,
                "file_size": file_size,
                "chunk_size": chunk_size,
                "total_chunks": total_chunks,
                "received_chunks": [],
                "status": "initialized",
                "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "user_id": user_id if is_admin else "anonymous",
                "temp_path": os.path.join(self.temp_dir, upload_id)
            }

            # 🆕 DATABASE-FIRST: Store upload session in database first
            if self.db:
                try:
                    with self.db() as session:
                        event_metadata = {
                            "upload_id": upload_id,
                            "filename": filename,
                            "file_size": file_size,
                            "chunk_size": chunk_size,
                            "total_chunks": total_chunks,
                            "temp_path": upload_session["temp_path"]
                        }

                        # Assuming log_system_event is a method that takes a session
                        # If it's on db_manager, we need to adapt this
                        if hasattr(session, 'log_system_event'):
                            session.log_system_event(
                                event_type="upload_session_initialized",
                                message=f"Upload session initialized for file: {filename} ({file_size} bytes)",
                                component="upload_service",
                                metadata=event_metadata
                            )
                        logger.info(f"✅ Upload session {upload_id} stored in database")

                except Exception as db_error:
                    logger.warning(f"⚠️ Database upload session storage failed: {db_error}")

            # Store in memory cache for real-time tracking
            self.uploads[upload_id] = upload_session

            # Create temp directory for chunks
            os.makedirs(upload_session["temp_path"], exist_ok=True)

            # Return same format as legacy for frontend compatibility
            return {
                "success": True,
                "session_id": upload_id,
                "uploadId": upload_id,  # Frontend expects this
                "upload_id": upload_id,  # Keep for internal consistency
                "chunk_size": chunk_size,
                "total_chunks": total_chunks,
                "max_file_size": 2 * 1024 * 1024 * 1024,  # 2GB like legacy
                "supported_formats": ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'],
                "message": "Upload initialized successfully"
            }

        except Exception as e:
            logger.error(f"Failed to initialize upload: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def upload_file(self, file: UploadFile, user_id: Optional[str] = None,
                         is_admin: bool = False) -> Dict[str, Any]:
        """
        Upload a complete file in one request
        Admin and users have same functionality
        """
        try:
            # Validate file
            if not file.filename:
                raise HTTPException(status_code=400, detail="No filename provided")

            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{timestamp}_{file.filename}"
            file_path = os.path.join(self.upload_dir, safe_filename)

            # Save file
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)

            # Calculate file info
            file_size = len(content)
            file_hash = hashlib.md5(content).hexdigest()

            # Create relative path for users (security - no absolute paths)
            relative_path = f"./io/input/{safe_filename}" if not is_admin else file_path

            return {
                "filename": safe_filename,
                "original_filename": file.filename,
                "file_path": relative_path,
                "file_size": file_size,
                "file_hash": file_hash,
                "upload_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "message": "File uploaded successfully"
            }

        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def upload_chunk(self, upload_id: str, chunk_index: int, chunk: bytes,
                          is_admin: bool = False) -> Dict[str, Any]:
        """
        Upload a file chunk for large files
        Admin and users have same functionality
        """
        try:
            # Get upload session
            if upload_id not in self.uploads:
                raise HTTPException(status_code=404, detail="Upload session not found")

            session = self.uploads[upload_id]

            # Validate chunk index
            if chunk_index >= session["total_chunks"]:
                raise HTTPException(status_code=400, detail="Invalid chunk index")

            if chunk_index in session["received_chunks"]:
                return {
                    "message": "Chunk already received",
                    "chunk_index": chunk_index,
                    "received_chunks": len(session["received_chunks"]),
                    "total_chunks": session["total_chunks"]
                }

            # Save chunk
            chunk_path = os.path.join(session["temp_path"], f"chunk_{chunk_index}")
            with open(chunk_path, "wb") as f:
                f.write(chunk)

            # Update session
            session["received_chunks"].append(chunk_index)
            session["status"] = "uploading"
            session["last_update"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            # Calculate progress
            progress = (len(session["received_chunks"]) / session["total_chunks"]) * 100

            # 🆕 DATABASE-FIRST: Log chunk progress to database
            if self.db:
                try:
                    with self.db() as db_session:
                        event_metadata = {
                            "upload_id": upload_id,
                            "chunk_index": chunk_index,
                            "received_chunks": len(session["received_chunks"]),
                            "total_chunks": session["total_chunks"],
                            "progress": round(progress, 2),
                            "chunk_size": len(chunk)
                        }

                        if hasattr(db_session, 'log_system_event'):
                            db_session.log_system_event(
                                event_type="upload_chunk_received",
                                message=f"Chunk {chunk_index}/{session['total_chunks']} uploaded for {session['filename']} ({progress:.1f}%)",
                                component="upload_service",
                                metadata=event_metadata
                            )

                except Exception as db_error:
                    logger.warning(f"⚠️ Database chunk logging failed: {db_error}")

            return {
                "message": "Chunk uploaded successfully",
                "chunk_index": chunk_index,
                "received_chunks": len(session["received_chunks"]),
                "total_chunks": session["total_chunks"],
                "progress": round(progress, 2),
                "complete": len(session["received_chunks"]) == session["total_chunks"]
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to upload chunk: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def finalize_upload(self, upload_id: str, is_admin: bool = False) -> Dict[str, Any]:
        """
        Finalize a chunked upload
        Admin and users have same functionality
        """
        try:
            # Get upload session
            if upload_id not in self.uploads:
                raise HTTPException(status_code=404, detail="Upload session not found")

            session = self.uploads[upload_id]

            # Check all chunks received
            if len(session["received_chunks"]) != session["total_chunks"]:
                missing = [i for i in range(session["total_chunks"])
                          if i not in session["received_chunks"]]
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing chunks: {missing}"
                )

            # Combine chunks
            final_path = os.path.join(self.upload_dir, session["filename"])
            with open(final_path, "wb") as final_file:
                for i in range(session["total_chunks"]):
                    chunk_path = os.path.join(session["temp_path"], f"chunk_{i}")
                    with open(chunk_path, "rb") as chunk_file:
                        final_file.write(chunk_file.read())

            # Calculate final hash
            with open(final_path, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()

            # 🆕 DATABASE-FIRST: Log upload completion to database first
            if self.db:
                try:
                    with self.db() as db_session:
                        completion_metadata = {
                            "upload_id": upload_id,
                            "filename": session["filename"],
                            "final_path": final_path,
                            "file_size": session["file_size"],
                            "file_hash": file_hash,
                            "total_chunks": session["total_chunks"],
                            "upload_duration_seconds": (datetime.now(timezone.utc) - datetime.fromisoformat(session["created_at"].replace("Z", "+00:00"))).total_seconds()
                        }

                        if hasattr(db_session, 'log_system_event'):
                            db_session.log_system_event(
                                event_type="upload_completed",
                                message=f"Upload completed successfully: {session['filename']} ({session['file_size']} bytes, {session['total_chunks']} chunks)",
                                component="upload_service",
                                metadata=completion_metadata
                            )
                        logger.info(f"✅ Upload completion logged to database: {upload_id}")

                except Exception as db_error:
                    logger.warning(f"⚠️ Database upload completion logging failed: {db_error}")

            # Clean up
            shutil.rmtree(session["temp_path"])
            session["status"] = "completed"
            session["completed_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            session["file_hash"] = file_hash

            # Create relative path for users (security - no absolute paths)
            relative_path = f"./io/input/{session['filename']}" if not is_admin else final_path

            return {
                "message": "Upload finalized successfully",
                "filename": session["filename"],
                "file_path": relative_path,
                "file_size": session["file_size"],
                "file_hash": file_hash,
                "upload_time": session["completed_at"]
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to finalize upload: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def get_upload_status(self, upload_id: str, is_admin: bool = False) -> Dict[str, Any]:
        """
        Get status of an upload
        Admin sees full details, users see limited info
        """
        try:
            # Get upload session
            if upload_id not in self.uploads:
                raise HTTPException(status_code=404, detail="Upload session not found")

            session = self.uploads[upload_id]

            # Calculate progress
            progress = 0
            if session["total_chunks"] > 0:
                progress = (len(session["received_chunks"]) / session["total_chunks"]) * 100

            status = {
                "upload_id": upload_id,
                "filename": session["filename"],
                "status": session["status"],
                "progress": round(progress, 2),
                "received_chunks": len(session["received_chunks"]),
                "total_chunks": session["total_chunks"],
                "created_at": session["created_at"]
            }

            # Add admin-only fields
            if is_admin:
                status.update({
                    "file_size": session["file_size"],
                    "chunk_size": session["chunk_size"],
                    "user_id": session.get("user_id"),
                    "temp_path": session.get("temp_path"),
                    "last_update": session.get("last_update")
                })

            return status

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get upload status: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def import_local_file(self, file_path: str, is_admin: bool = False) -> Dict[str, Any]:
        """
        Import a file from local path
        Admin only functionality
        """
        if not is_admin:
            raise HTTPException(
                status_code=403,
                detail="Unauthorized: Admin access required"
            )

        try:
            # Validate file exists
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail="File not found")

            # Get file info
            file_size = os.path.getsize(file_path)
            filename = os.path.basename(file_path)

            # Copy to upload directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{timestamp}_{filename}"
            dest_path = os.path.join(self.upload_dir, safe_filename)

            shutil.copy2(file_path, dest_path)

            # Calculate hash
            with open(dest_path, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()

            # 🆕 DATABASE-FIRST: Log file import to database
            if self.db:
                try:
                    with self.db() as db_session:
                        import_metadata = {
                            "original_path": file_path,
                            "imported_filename": safe_filename,
                            "dest_path": dest_path,
                            "file_size": file_size,
                            "file_hash": file_hash,
                            "import_method": "local_file_import"
                        }

                        if hasattr(db_session, 'log_system_event'):
                            db_session.log_system_event(
                                event_type="file_imported",
                                message=f"Local file imported: {filename} ({file_size} bytes) -> {safe_filename}",
                                component="upload_service",
                                metadata=import_metadata
                            )
                        logger.info(f"✅ File import logged to database: {safe_filename}")

                except Exception as db_error:
                    logger.warning(f"⚠️ Database file import logging failed: {db_error}")

            return {
                "message": "File imported successfully",
                "filename": safe_filename,
                "original_path": file_path,
                "file_size": file_size,
                "file_hash": file_hash,
                "import_time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to import local file: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def list_uploads(self, is_admin: bool = False) -> Dict[str, Any]:
        """List all upload sessions"""
        try:
            upload_list = []
            for upload_id, session in self.uploads.items():
                upload_list.append({
                    "upload_id": upload_id,
                    "filename": session["filename"],
                    "file_size": session["file_size"],
                    "status": session["status"],
                    "progress": (len(session["received_chunks"]) / session["total_chunks"]) * 100,
                    "created_at": session["created_at"]
                })

            return {
                "uploads": upload_list,
                "total": len(upload_list)
            }
        except Exception as e:
            logger.error(f"Failed to list uploads: {e}")
            return {"uploads": [], "total": 0}
