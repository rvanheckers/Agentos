"""
Enterprise Action Dispatcher
Central orchestrator for all admin actions with enterprise features
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, List
from uuid import uuid4
import logging

# Core services
from services.jobs_service import JobsService
from services.queue_service import QueueService
from services.worker_service import WorkerService
from services.system_service import SystemService
from services.admin_data_manager import AdminDataManager

# Enterprise features
from services.idempotency_service import IdempotencyService
from services.authorization_service import AuthorizationService
from services.rate_limiter import RateLimiter
from services.circuit_breaker import CircuitBreaker
from services.audit_log import AuditLog

# Models
from api.models.action_models import ActionType
from events.dispatcher import EventDispatcher

logger = logging.getLogger("agentos.action_dispatcher")

class ActionDispatcher:
    """
    Enterprise-grade action dispatcher with:
    - Type safety via Pydantic models
    - Idempotency for safe retries
    - Circuit breakers for fault tolerance
    - Rate limiting per action type
    - Comprehensive authorization
    - Distributed tracing
    - Audit logging
    - Event propagation
    """
    
    def __init__(self):
        # Service instances (lazy loaded for performance)
        self._jobs_service = None
        self._queue_service = None
        self._worker_service = None
        self._system_service = None
        self._admin_data_manager = None
        
        # Enterprise services
        self.idempotency = IdempotencyService()
        self.auth = AuthorizationService()
        self.rate_limiter = RateLimiter()
        self.audit = AuditLog()
        self.events = EventDispatcher()
    
    # ============ SERVICE PROPERTIES (Lazy Loading) ============
    
    @property
    def jobs_service(self):
        if not self._jobs_service:
            self._jobs_service = JobsService()
        return self._jobs_service
    
    @property
    def queue_service(self):
        if not self._queue_service:
            self._queue_service = QueueService()
        return self._queue_service
    
    @property
    def worker_service(self):
        if not self._worker_service:
            self._worker_service = WorkerService()
        return self._worker_service
    
    @property
    def system_service(self):
        if not self._system_service:
            self._system_service = SystemService()
        return self._system_service
    
    @property
    def admin_data_manager(self):
        if not self._admin_data_manager:
            self._admin_data_manager = AdminDataManager()
        return self._admin_data_manager
    
    # ============ ACTION REGISTRY ============
    
    ACTION_HANDLERS: Dict[ActionType, Callable] = {
        # Job Actions
        ActionType.JOB_RETRY: lambda self, p, **kw: self.jobs_service.retry_job(**p, **kw),
        ActionType.JOB_CANCEL: lambda self, p, **kw: self.jobs_service.cancel_job(**p, **kw),
        ActionType.JOB_DELETE: lambda self, p, **kw: self.jobs_service.delete_job(**p, **kw),
        ActionType.JOB_PRIORITY: lambda self, p, **kw: self.jobs_service.set_job_priority(**p, **kw),
        
        # Queue Actions
        ActionType.QUEUE_CLEAR: lambda self, p, **kw: self.queue_service.clear_queue(**p, **kw),
        ActionType.QUEUE_PAUSE: lambda self, p, **kw: self.queue_service.pause_processing(**p, **kw),
        ActionType.QUEUE_RESUME: lambda self, p, **kw: self.queue_service.resume_processing(**p, **kw),
        ActionType.QUEUE_DRAIN: lambda self, p, **kw: self.queue_service.drain_queue(**p, **kw),
        
        # Worker Actions
        ActionType.WORKER_RESTART: lambda self, p, **kw: self.worker_service.restart_worker(**p, **kw),
        ActionType.WORKER_SCALE: lambda self, p, **kw: self.worker_service.scale_workers(**p, **kw),
        ActionType.WORKER_PAUSE: lambda self, p, **kw: self.worker_service.pause_worker(**p, **kw),
        ActionType.WORKER_RESUME: lambda self, p, **kw: self.worker_service.resume_worker(**p, **kw),
        
        # System Actions
        ActionType.SYSTEM_BACKUP: lambda self, p, **kw: self.system_service.create_backup(**p, **kw),
        ActionType.SYSTEM_MAINTENANCE: lambda self, p, **kw: self.system_service.set_maintenance(**p, **kw),
        ActionType.CACHE_CLEAR: lambda self, p, **kw: self.admin_data_manager.clear_cache(**p, **kw),
        ActionType.CACHE_WARM: lambda self, p, **kw: self.admin_data_manager.warm_cache(**p, **kw),
    }
    
    # ============ ACTION CONFIGURATION ============
    
    ACTION_CONFIG = {
        # Job Actions
        ActionType.JOB_RETRY: {
            "permissions": ["job:write", "job:retry"],
            "rate_limit": {"requests": 100, "window": 60},
            "timeout": 10,
            "circuit_breaker": True,
            "audit": True,
            "events": ["job:retry_requested", "cache:invalidate"],
        },
        ActionType.JOB_CANCEL: {
            "permissions": ["job:write", "job:cancel"],
            "rate_limit": {"requests": 50, "window": 60},
            "timeout": 5,
            "circuit_breaker": True,
            "audit": True,
            "events": ["job:cancelled", "cache:invalidate"],
        },
        ActionType.JOB_DELETE: {
            "permissions": ["job:write", "job:delete", "admin"],
            "rate_limit": {"requests": 20, "window": 60},
            "timeout": 15,
            "circuit_breaker": True,
            "audit": True,
            "events": ["job:deleted", "cache:invalidate"],
        },
        ActionType.JOB_PRIORITY: {
            "permissions": ["job:write", "job:priority"],
            "rate_limit": {"requests": 200, "window": 60},
            "timeout": 3,
            "circuit_breaker": False,
            "audit": False,
            "events": ["job:priority_changed"],
        },
        
        # Queue Actions
        ActionType.QUEUE_CLEAR: {
            "permissions": ["admin", "queue:manage", "queue:clear"],
            "rate_limit": {"requests": 1, "window": 300},  # 1 per 5 minutes
            "timeout": 60,
            "circuit_breaker": True,
            "audit": True,
            "events": ["queue:cleared", "cache:invalidate"],
        },
        ActionType.QUEUE_PAUSE: {
            "permissions": ["admin", "queue:manage"],
            "rate_limit": {"requests": 5, "window": 300},
            "timeout": 30,
            "circuit_breaker": True,
            "audit": True,
            "events": ["queue:paused", "cache:invalidate"],
        },
        ActionType.QUEUE_RESUME: {
            "permissions": ["admin", "queue:manage"],
            "rate_limit": {"requests": 10, "window": 60},
            "timeout": 10,
            "circuit_breaker": True,
            "audit": True,
            "events": ["queue:resumed", "cache:invalidate"],
        },
        ActionType.QUEUE_DRAIN: {
            "permissions": ["admin", "queue:manage"],
            "rate_limit": {"requests": 2, "window": 600},
            "timeout": 300,  # 5 minutes
            "circuit_breaker": True,
            "audit": True,
            "events": ["queue:draining", "cache:invalidate"],
        },
        
        # Worker Actions
        ActionType.WORKER_RESTART: {
            "permissions": ["admin", "worker:manage"],
            "rate_limit": {"requests": 5, "window": 300},
            "timeout": 120,
            "circuit_breaker": True,
            "audit": True,
            "events": ["worker:restarted", "cache:invalidate"],
        },
        ActionType.WORKER_SCALE: {
            "permissions": ["admin", "worker:manage"],
            "rate_limit": {"requests": 3, "window": 600},
            "timeout": 180,
            "circuit_breaker": True,
            "audit": True,
            "events": ["worker:scaled", "cache:invalidate"],
        },
        ActionType.WORKER_PAUSE: {
            "permissions": ["admin", "worker:manage"],
            "rate_limit": {"requests": 10, "window": 60},
            "timeout": 30,
            "circuit_breaker": True,
            "audit": True,
            "events": ["worker:paused"],
        },
        ActionType.WORKER_RESUME: {
            "permissions": ["admin", "worker:manage"],
            "rate_limit": {"requests": 10, "window": 60},
            "timeout": 10,
            "circuit_breaker": True,
            "audit": True,
            "events": ["worker:resumed"],
        },
        
        # System Actions
        ActionType.SYSTEM_BACKUP: {
            "permissions": ["admin", "system:backup"],
            "rate_limit": {"requests": 1, "window": 3600},  # 1 per hour
            "timeout": 600,  # 10 minutes
            "circuit_breaker": True,
            "audit": True,
            "events": ["system:backup_started"],
        },
        ActionType.SYSTEM_MAINTENANCE: {
            "permissions": ["admin", "system:maintenance"],
            "rate_limit": {"requests": 5, "window": 3600},
            "timeout": 30,
            "circuit_breaker": True,
            "audit": True,
            "events": ["system:maintenance_changed", "cache:invalidate"],
        },
        ActionType.CACHE_CLEAR: {
            "permissions": ["admin", "cache:manage"],
            "rate_limit": {"requests": 10, "window": 300},
            "timeout": 60,
            "circuit_breaker": True,
            "audit": True,
            "events": ["cache:cleared"],
        },
        ActionType.CACHE_WARM: {
            "permissions": ["admin", "cache:manage"],
            "rate_limit": {"requests": 20, "window": 60},
            "timeout": 120,
            "circuit_breaker": True,
            "audit": False,
            "events": ["cache:warmed"],
        },
    }
    
    # ============ MAIN EXECUTION METHOD ============
    
    async def execute(
        self,
        action: ActionType,
        payload: Dict[str, Any],
        user: Any,
        trace_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        **options
    ) -> Dict[str, Any]:
        """
        Execute action with full enterprise features
        
        Args:
            action: The action type to execute
            payload: Action-specific payload
            user: User executing the action
            trace_id: Trace ID for distributed tracing
            idempotency_key: Key for idempotency checking
            **options: Additional options
        
        Returns:
            Action result dictionary
        
        Raises:
            PermissionError: If user lacks permissions
            ValueError: If action or payload is invalid
            TimeoutError: If action times out
            Exception: For other execution errors
        """
        
        # Generate trace ID if not provided
        if not trace_id:
            trace_id = str(uuid4())
        
        # Setup logging context
        log_context = {
            "trace_id": trace_id,
            "action": action.value,
            "user_id": getattr(user, 'id', 'unknown'),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("Action execution started", extra=log_context)
        execution_start = time.time()
        
        try:
            # 1. Validate action exists
            if action not in self.ACTION_HANDLERS:
                raise ValueError(f"Unknown action: {action}")
            
            config = self.ACTION_CONFIG.get(action, {})
            
            # 2. Check idempotency
            if idempotency_key:
                cached_result = await self.idempotency.check(idempotency_key, action, user.id)
                if cached_result:
                    logger.info("Returning cached result (idempotent)", extra=log_context)
                    return cached_result
            
            # 3. Rate limiting
            rate_limit = config.get("rate_limit", {"requests": 100, "window": 60})
            if not await self.rate_limiter.check(user.id, action, **rate_limit):
                raise ValueError("Rate limit exceeded for this action")
            
            # 4. Authorization
            permissions = config.get("permissions", ["admin"])
            if not await self.auth.check_permissions(user, action, payload, permissions):
                # Log denied attempt
                await self.audit.log_denied_attempt(
                    user_id=user.id,
                    action=action,
                    payload=payload,
                    trace_id=trace_id
                )
                raise PermissionError(f"Insufficient permissions for {action}")
            
            # 5. Execute with circuit breaker and timeout
            handler = self.ACTION_HANDLERS[action]
            timeout = config.get("timeout", 30)
            
            if config.get("circuit_breaker", True):
                # Create circuit breaker instance and use its context manager
                circuit_breaker = CircuitBreaker(f"action:{action}")
                with circuit_breaker():
                    result = await asyncio.wait_for(
                        self._execute_handler(handler, payload, user=user, trace_id=trace_id, **options),
                        timeout=timeout
                    )
            else:
                result = await asyncio.wait_for(
                    self._execute_handler(handler, payload, user=user, trace_id=trace_id, **options),
                    timeout=timeout
                )
            
            execution_time = (time.time() - execution_start) * 1000  # ms
            
            # 6. Cache result for idempotency
            if idempotency_key:
                await self.idempotency.store(idempotency_key, result)
            
            # 7. Audit logging
            if config.get("audit", True):
                await self.audit.log_action(
                    user_id=user.id,
                    action=action,
                    payload=payload,
                    result=result,
                    trace_id=trace_id,
                    execution_time_ms=execution_time
                )
            
            # 8. Event propagation
            events = config.get("events", [])
            for event in events:
                await self.events.dispatch(event, {
                    **payload,
                    "action": action.value,
                    "user_id": user.id,
                    "trace_id": trace_id,
                    "result": result,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            
            # 9. Success logging
            logger.info(
                "Action execution completed successfully", 
                extra={**log_context, "execution_time_ms": execution_time, "result_size": len(str(result))}
            )
            
            return {
                "success": True,
                "result": result,
                "trace_id": trace_id,
                "execution_time_ms": execution_time,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except PermissionError:
            logger.warning("Action execution denied", extra=log_context)
            raise
        except ValueError:
            logger.warning("Action execution failed - invalid input", extra=log_context)
            raise
        except asyncio.TimeoutError:
            execution_time = (time.time() - execution_start) * 1000
            logger.error(
                "Action execution timed out", 
                extra={**log_context, "timeout_after_ms": execution_time}
            )
            raise TimeoutError(f"Action {action} timed out after {execution_time:.0f}ms")
        except Exception as e:
            execution_time = (time.time() - execution_start) * 1000
            logger.exception(
                "Action execution failed", 
                extra={**log_context, "error": str(e), "execution_time_ms": execution_time}
            )
            
            # Log failure for audit
            if config.get("audit", True):
                await self.audit.log_action_failure(
                    user_id=user.id,
                    action=action,
                    payload=payload,
                    error=str(e),
                    trace_id=trace_id,
                    execution_time_ms=execution_time
                )
            
            raise
    
    async def _execute_handler(self, handler: Callable, payload: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Execute the actual action handler"""
        try:
            # Call handler with payload and options
            if asyncio.iscoroutinefunction(handler):
                return await handler(self, payload, **kwargs)
            else:
                return handler(self, payload, **kwargs)
        except Exception as e:
            logger.error(f"Handler execution failed: {e}")
            raise
    
    # ============ UTILITY METHODS ============
    
    def get_action_config(self, action: ActionType) -> Dict[str, Any]:
        """Get configuration for a specific action"""
        return self.ACTION_CONFIG.get(action, {})
    
    def list_available_actions(self, user: Any) -> List[ActionType]:
        """List actions available to a user based on permissions"""
        available_actions = []
        
        for action, config in self.ACTION_CONFIG.items():
            permissions = config.get("permissions", ["admin"])
            if self.auth.has_any_permission(user, permissions):
                available_actions.append(action)
        
        return available_actions
    
    async def get_action_status(self, action: ActionType) -> Dict[str, Any]:
        """Get status information for an action (rate limits, circuit breaker, etc.)"""
        config = self.ACTION_CONFIG.get(action, {})
        
        return {
            "action": action.value,
            "rate_limit": config.get("rate_limit", {}),
            "circuit_breaker_open": CircuitBreaker(f"action:{action}").is_open if config.get("circuit_breaker") else False,
            "timeout": config.get("timeout", 30),
            "permissions_required": config.get("permissions", ["admin"]),
            "audit_enabled": config.get("audit", True),
            "events": config.get("events", [])
        }

# ============ SINGLETON INSTANCE ============

# Global dispatcher instance
action_dispatcher = ActionDispatcher()

# Export for easy importing
__all__ = ["ActionDispatcher", "action_dispatcher"]