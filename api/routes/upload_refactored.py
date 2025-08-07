"""
Clean Upload routes - Admin duplicates removed 
Only user endpoints remain to eliminate duplicate chaos
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Body
from typing import Dict, Any, Optional
from pydantic import BaseModel
from services.upload_service import UploadService
import logging

logger = logging.getLogger("agentos.api.routes.upload")

# Create service instance
upload_service = UploadService()

# Single router - user endpoints only (admin can use these too)
user_router = APIRouter(prefix="/api/upload", tags=["upload"])

# === MODELS ===

class UploadInitRequest(BaseModel):
    # Support both camelCase (frontend) and snake_case (API)
    filename: Optional[str] = None
    fileName: Optional[str] = None
    file_size: Optional[int] = None
    fileSize: Optional[int] = None
    chunk_size: int = 1024*1024

class UploadChunkRequest(BaseModel):
    upload_id: str
    uploadId: Optional[str] = None  # Frontend compatibility
    chunk_index: int
    chunkIndex: Optional[int] = None  # Frontend compatibility

class UploadFinalizeRequest(BaseModel):
    upload_id: str
    uploadId: Optional[str] = None  # Frontend compatibility
    total_chunks: int
    totalChunks: Optional[int] = None  # Frontend compatibility

# === USER ENDPOINTS (CLEAN) ===

@user_router.post("/init")
async def init_upload(request: UploadInitRequest) -> Dict[str, Any]:
    """Initialize upload session"""
    try:
        # Handle both camelCase and snake_case
        filename = request.filename or request.fileName
        file_size = request.file_size or request.fileSize
        
        return upload_service.init_upload(
            filename=filename,
            file_size=file_size,
            chunk_size=request.chunk_size,
            is_admin=False
        )
    except Exception as e:
        logger.error(f"Failed to init upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@user_router.post("/chunk")
async def upload_chunk(
    file: UploadFile = File(...),
    upload_id: str = Form(...),
    chunk_index: int = Form(...)
) -> Dict[str, Any]:
    """Upload a file chunk"""
    try:
        return await upload_service.upload_chunk(
            upload_id=upload_id,
            chunk_index=chunk_index,
            chunk=await file.read(),
            is_admin=False
        )
    except Exception as e:
        logger.error(f"Failed to upload chunk: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@user_router.post("/finalize")
async def finalize_upload(request: UploadFinalizeRequest) -> Dict[str, Any]:
    """Finalize upload and assemble chunks"""
    try:
        # Handle both camelCase and snake_case
        upload_id = request.upload_id or request.uploadId
        total_chunks = request.total_chunks or request.totalChunks
        
        return upload_service.finalize_upload(
            upload_id=upload_id,
            is_admin=False
        )
    except Exception as e:
        logger.error(f"Failed to finalize upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@user_router.get("/status/{upload_id}")
async def get_upload_status(upload_id: str) -> Dict[str, Any]:
    """Get upload status"""
    try:
        return upload_service.get_upload_status(upload_id, is_admin=False)
    except Exception as e:
        logger.error(f"Failed to get upload status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@user_router.get("")
async def list_uploads() -> Dict[str, Any]:
    """List all uploads"""
    try:
        return upload_service.list_uploads(is_admin=False)
    except Exception as e:
        logger.error(f"Failed to list uploads: {e}")
        raise HTTPException(status_code=500, detail=str(e))