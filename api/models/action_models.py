"""
Enterprise Action Models
Type-safe payloads for admin actions with comprehensive validation
"""

from typing import Union, Optional, List, Literal
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, validator
from enum import Enum

# ============ ACTION TYPES ENUM ============

class ActionType(str, Enum):
    # Job Actions
    JOB_RETRY = "job.retry"
    JOB_CANCEL = "job.cancel"
    JOB_DELETE = "job.delete"
    JOB_PRIORITY = "job.priority"
    
    # Queue Actions
    QUEUE_CLEAR = "queue.clear"
    QUEUE_PAUSE = "queue.pause"
    QUEUE_RESUME = "queue.resume"
    QUEUE_DRAIN = "queue.drain"
    
    # Worker Actions
    WORKER_RESTART = "worker.restart"
    WORKER_SCALE = "worker.scale"
    WORKER_PAUSE = "worker.pause"
    WORKER_RESUME = "worker.resume"
    
    # System Actions
    SYSTEM_BACKUP = "system.backup"
    SYSTEM_MAINTENANCE = "system.maintenance"
    CACHE_CLEAR = "cache.clear"
    CACHE_WARM = "cache.warm"

# ============ PAYLOAD MODELS ============

class JobRetryPayload(BaseModel):
    """Payload for retrying a failed job"""
    job_id: UUID = Field(..., description="ID of the job to retry")
    reason: Optional[str] = Field(None, description="Reason for retry", max_length=500)
    priority: Optional[int] = Field(None, ge=0, le=10, description="New priority (0-10)")
    max_retries: Optional[int] = Field(None, ge=1, le=5, description="Maximum retry attempts")
    
    @validator('reason')
    def validate_reason(cls, v):
        if v and len(v.strip()) == 0:
            raise ValueError('Reason cannot be empty string')
        return v

class JobCancelPayload(BaseModel):
    """Payload for cancelling a running job"""
    job_id: UUID = Field(..., description="ID of the job to cancel")
    cascade: bool = Field(False, description="Cancel dependent jobs too")
    force: bool = Field(False, description="Force cancel even if job is completing")
    reason: Optional[str] = Field(None, description="Cancellation reason", max_length=500)

class JobDeletePayload(BaseModel):
    """Payload for deleting a job"""
    job_id: UUID = Field(..., description="ID of the job to delete")
    delete_outputs: bool = Field(False, description="Delete job output files")
    cascade: bool = Field(False, description="Delete dependent jobs too")

class JobPriorityPayload(BaseModel):
    """Payload for changing job priority"""
    job_id: UUID = Field(..., description="ID of the job")
    priority: int = Field(..., ge=0, le=10, description="New priority (0=low, 10=critical)")

class QueueClearPayload(BaseModel):
    """Payload for clearing queue"""
    status_filter: List[str] = Field(
        ["pending", "queued"], 
        description="Job statuses to clear",
        min_items=1
    )
    older_than_hours: Optional[int] = Field(None, ge=1, description="Only clear jobs older than X hours")
    dry_run: bool = Field(False, description="Preview what would be deleted without actually deleting")
    user_filter: Optional[str] = Field(None, description="Only clear jobs from specific user")
    
    @validator('status_filter')
    def validate_status_filter(cls, v):
        valid_statuses = {'pending', 'queued', 'failed', 'cancelled'}
        for status in v:
            if status not in valid_statuses:
                raise ValueError(f'Invalid status: {status}. Must be one of {valid_statuses}')
        return v

class QueuePausePayload(BaseModel):
    """Payload for pausing queue processing"""
    reason: Optional[str] = Field(None, description="Reason for pausing", max_length=500)
    duration_minutes: Optional[int] = Field(None, ge=1, le=1440, description="Auto-resume after X minutes")

class QueueResumePayload(BaseModel):
    """Payload for resuming queue processing"""
    reason: Optional[str] = Field(None, description="Reason for resuming", max_length=500)

class QueueDrainPayload(BaseModel):
    """Payload for draining queue (finish current jobs, accept no new ones)"""
    timeout_minutes: Optional[int] = Field(30, ge=1, le=120, description="Timeout for drain operation")

class WorkerRestartPayload(BaseModel):
    """Payload for restarting worker"""
    worker_id: Optional[str] = Field(None, description="Specific worker ID, or all if not provided")
    force: bool = Field(False, description="Force restart even if worker is busy")
    wait_for_completion: bool = Field(True, description="Wait for current jobs to complete")

class WorkerScalePayload(BaseModel):
    """Payload for scaling workers"""
    count: int = Field(..., ge=1, le=100, description="Target number of workers")
    worker_type: Optional[str] = Field("default", description="Type of workers to scale")
    timeout_seconds: Optional[int] = Field(300, ge=60, le=600, description="Timeout for scaling operation")

class WorkerPausePayload(BaseModel):
    """Payload for pausing workers"""
    worker_id: Optional[str] = Field(None, description="Specific worker ID, or all if not provided")
    finish_current: bool = Field(True, description="Finish current jobs before pausing")

class WorkerResumePayload(BaseModel):
    """Payload for resuming workers"""
    worker_id: Optional[str] = Field(None, description="Specific worker ID, or all if not provided")

class SystemBackupPayload(BaseModel):
    """Payload for system backup"""
    include_logs: bool = Field(True, description="Include system logs in backup")
    include_job_data: bool = Field(True, description="Include job data in backup")
    include_user_data: bool = Field(False, description="Include user data in backup")
    compression: bool = Field(True, description="Compress backup file")
    backup_name: Optional[str] = Field(None, description="Custom backup name", max_length=100)

class SystemMaintenancePayload(BaseModel):
    """Payload for maintenance mode"""
    enable: bool = Field(..., description="Enable or disable maintenance mode")
    message: Optional[str] = Field(None, description="Maintenance message for users", max_length=1000)
    duration_minutes: Optional[int] = Field(None, ge=1, le=1440, description="Expected maintenance duration")

class CacheClearPayload(BaseModel):
    """Payload for clearing cache"""
    cache_types: List[str] = Field(
        ["redis", "application"], 
        description="Types of cache to clear",
        min_items=1
    )
    pattern: Optional[str] = Field(None, description="Cache key pattern to clear (supports wildcards)")
    
    @validator('cache_types')
    def validate_cache_types(cls, v):
        valid_types = {'redis', 'application', 'database', 'cdn'}
        for cache_type in v:
            if cache_type not in valid_types:
                raise ValueError(f'Invalid cache type: {cache_type}. Must be one of {valid_types}')
        return v

class CacheWarmPayload(BaseModel):
    """Payload for warming cache"""
    cache_types: List[str] = Field(
        ["dashboard", "queue"], 
        description="Types of cache to warm",
        min_items=1
    )
    force: bool = Field(False, description="Force warm even if cache is fresh")

# ============ DISCRIMINATED UNION ACTIONS ============

class JobRetryAction(BaseModel):
    action: Literal[ActionType.JOB_RETRY] = ActionType.JOB_RETRY
    payload: JobRetryPayload

class JobCancelAction(BaseModel):
    action: Literal[ActionType.JOB_CANCEL] = ActionType.JOB_CANCEL
    payload: JobCancelPayload

class JobDeleteAction(BaseModel):
    action: Literal[ActionType.JOB_DELETE] = ActionType.JOB_DELETE
    payload: JobDeletePayload

class JobPriorityAction(BaseModel):
    action: Literal[ActionType.JOB_PRIORITY] = ActionType.JOB_PRIORITY
    payload: JobPriorityPayload

class QueueClearAction(BaseModel):
    action: Literal[ActionType.QUEUE_CLEAR] = ActionType.QUEUE_CLEAR
    payload: QueueClearPayload

class QueuePauseAction(BaseModel):
    action: Literal[ActionType.QUEUE_PAUSE] = ActionType.QUEUE_PAUSE
    payload: QueuePausePayload

class QueueResumeAction(BaseModel):
    action: Literal[ActionType.QUEUE_RESUME] = ActionType.QUEUE_RESUME
    payload: QueueResumePayload

class QueueDrainAction(BaseModel):
    action: Literal[ActionType.QUEUE_DRAIN] = ActionType.QUEUE_DRAIN
    payload: QueueDrainPayload

class WorkerRestartAction(BaseModel):
    action: Literal[ActionType.WORKER_RESTART] = ActionType.WORKER_RESTART
    payload: WorkerRestartPayload

class WorkerScaleAction(BaseModel):
    action: Literal[ActionType.WORKER_SCALE] = ActionType.WORKER_SCALE
    payload: WorkerScalePayload

class WorkerPauseAction(BaseModel):
    action: Literal[ActionType.WORKER_PAUSE] = ActionType.WORKER_PAUSE
    payload: WorkerPausePayload

class WorkerResumeAction(BaseModel):
    action: Literal[ActionType.WORKER_RESUME] = ActionType.WORKER_RESUME
    payload: WorkerResumePayload

class SystemBackupAction(BaseModel):
    action: Literal[ActionType.SYSTEM_BACKUP] = ActionType.SYSTEM_BACKUP
    payload: SystemBackupPayload

class SystemMaintenanceAction(BaseModel):
    action: Literal[ActionType.SYSTEM_MAINTENANCE] = ActionType.SYSTEM_MAINTENANCE
    payload: SystemMaintenancePayload

class CacheClearAction(BaseModel):
    action: Literal[ActionType.CACHE_CLEAR] = ActionType.CACHE_CLEAR
    payload: CacheClearPayload

class CacheWarmAction(BaseModel):
    action: Literal[ActionType.CACHE_WARM] = ActionType.CACHE_WARM
    payload: CacheWarmPayload

# ============ MAIN UNION TYPE ============

ActionRequest = Union[
    # Job Actions
    JobRetryAction,
    JobCancelAction,
    JobDeleteAction,
    JobPriorityAction,
    
    # Queue Actions
    QueueClearAction,
    QueuePauseAction,
    QueueResumeAction,
    QueueDrainAction,
    
    # Worker Actions
    WorkerRestartAction,
    WorkerScaleAction,
    WorkerPauseAction,
    WorkerResumeAction,
    
    # System Actions
    SystemBackupAction,
    SystemMaintenanceAction,
    CacheClearAction,
    CacheWarmAction
]

# ============ RESPONSE MODELS ============

class ActionResponse(BaseModel):
    """Standard response for all actions"""
    success: bool = Field(..., description="Whether the action succeeded")
    action: ActionType = Field(..., description="The action that was executed")
    result: dict = Field(..., description="Action-specific result data")
    trace_id: str = Field(..., description="Trace ID for debugging")
    timestamp: datetime = Field(..., description="When the action was executed")
    duration_ms: Optional[float] = Field(None, description="Action execution duration")

class ActionError(BaseModel):
    """Error response for failed actions"""
    success: bool = False
    action: ActionType = Field(..., description="The action that failed")
    error_code: str = Field(..., description="Machine-readable error code")
    error_message: str = Field(..., description="Human-readable error message")
    trace_id: str = Field(..., description="Trace ID for debugging")
    timestamp: datetime = Field(..., description="When the error occurred")
    details: Optional[dict] = Field(None, description="Additional error details")