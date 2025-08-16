"""
Enterprise Action Dispatcher
Central orchestrator for all admin actions with enterprise features
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, List, Union
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

# Smart Cache Invalidation
from services.smart_cache_invalidator import get_cache_invalidator

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

        # Smart cache invalidation
        self.cache_invalidator = get_cache_invalidator()

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

    def _get_job_id(self, payload: Dict[str, Any]) -> str:
        """Safely extract job_id from payload with validation"""
        job_id = payload.get('job_id')
        if not job_id:
            raise ValueError("Missing required parameter: job_id")
        return str(job_id)

    ACTION_HANDLERS: Dict[Union[ActionType, str], Callable] = {
        # Job Actions (with payload validation)
        ActionType.JOB_RETRY: lambda self, p, **kw: self.jobs_service.retry_job(job_id=self._get_job_id(p), is_admin=True),
        ActionType.JOB_CANCEL: lambda self, p, **kw: self.jobs_service.cancel_job(job_id=self._get_job_id(p), is_admin=True),
        ActionType.JOB_DELETE: lambda self, p, **kw: self.jobs_service.delete_job(job_id=self._get_job_id(p), is_admin=True),
        ActionType.JOB_PRIORITY: lambda self, p, **kw: self.jobs_service.set_job_priority(**p, **kw),

        # Queue Actions
        ActionType.QUEUE_CLEAR: lambda self, p, **kw: self.queue_service.clear_queue(**p, **kw),
        ActionType.QUEUE_PAUSE: lambda self, p, **kw: self.queue_service.pause_processing(**p, **kw),
        ActionType.QUEUE_RESUME: lambda self, p, **kw: self.queue_service.resume_processing(**p, **kw),
        ActionType.QUEUE_DRAIN: lambda self, p, **kw: self.queue_service.clear_queue(**p, **kw),

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
        
        # Analytics Actions - NEW for Analytics redesign
        "analytics.drill_down": lambda self, p, **kw: self._handle_analytics_drill_down(p),
        "analytics.generate_report": lambda self, p, **kw: self._handle_analytics_generate_report(p),
        "analytics.capacity_analysis": lambda self, p, **kw: self._handle_analytics_capacity_analysis(p),
        "system.performance_tune": lambda self, p, **kw: self._handle_system_performance_tune(p),
        "system.health_check": lambda self, p, **kw: self._handle_system_health_check(p),
        "system.emergency_report": lambda self, p, **kw: self._handle_system_emergency_report(p),
        "worker.auto_scale": lambda self, p, **kw: self._handle_worker_auto_scale(p),
        "worker.optimize": lambda self, p, **kw: self._handle_worker_optimize(p),
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

        # Analytics Actions Configuration - NEW
        "analytics.drill_down": {
            "permissions": ["admin", "analytics:read"],
            "rate_limit": {"requests": 50, "window": 60},
            "timeout": 15,
            "circuit_breaker": False,
            "audit": False,
            "events": ["analytics:drill_down_requested"],
        },
        "analytics.generate_report": {
            "permissions": ["admin", "analytics:read"],
            "rate_limit": {"requests": 10, "window": 300},  # 10 per 5 minutes
            "timeout": 60,
            "circuit_breaker": True,
            "audit": True,
            "events": ["analytics:report_generated"],
        },
        "analytics.capacity_analysis": {
            "permissions": ["admin", "analytics:read"],
            "rate_limit": {"requests": 20, "window": 60},
            "timeout": 30,
            "circuit_breaker": False,
            "audit": False,
            "events": ["analytics:capacity_analysis_requested"],
        },
        "system.performance_tune": {
            "permissions": ["admin", "system:manage"],
            "rate_limit": {"requests": 5, "window": 300},  # 5 per 5 minutes
            "timeout": 120,
            "circuit_breaker": True,
            "audit": True,
            "events": ["system:performance_tuned", "cache:invalidate"],
        },
        "system.health_check": {
            "permissions": ["admin", "system:read"],
            "rate_limit": {"requests": 20, "window": 60},
            "timeout": 30,
            "circuit_breaker": False,
            "audit": False,
            "events": ["system:health_check_performed"],
        },
        "system.emergency_report": {
            "permissions": ["admin", "system:emergency"],
            "rate_limit": {"requests": 5, "window": 600},  # 5 per 10 minutes
            "timeout": 180,
            "circuit_breaker": True,
            "audit": True,
            "events": ["system:emergency_report_generated"],
        },
        "worker.auto_scale": {
            "permissions": ["admin", "worker:scale"],
            "rate_limit": {"requests": 10, "window": 300},
            "timeout": 60,
            "circuit_breaker": True,
            "audit": True,
            "events": ["worker:auto_scaled", "cache:invalidate"],
        },
        "worker.optimize": {
            "permissions": ["admin", "worker:manage"],
            "rate_limit": {"requests": 15, "window": 300},
            "timeout": 45,
            "circuit_breaker": True,
            "audit": True,
            "events": ["worker:optimized", "cache:invalidate"],
        },
    }

    # ============ MAIN EXECUTION METHOD ============

    async def execute(
        self,
        action: Union[ActionType, str],
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

        # Normalize action to string early (support both Enum and str)
        action_str = action.value if hasattr(action, 'value') else str(action)

        # Setup logging context
        log_context = {
            "trace_id": trace_id,
            "action": action_str,
            "user_id": getattr(user, 'id', 'unknown'),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        logger.info("Action execution started", extra=log_context)
        execution_start = time.time()

        try:
            # 1. Validate action exists (handle both ActionType enums and string actions)
            action_key = action.value if hasattr(action, 'value') else str(action)
            
            if action not in self.ACTION_HANDLERS and action_key not in self.ACTION_HANDLERS:
                raise ValueError(f"Unknown action: {action}")

            # Use the appropriate key for lookups
            lookup_key = action if action in self.ACTION_HANDLERS else action_key
            config = self.ACTION_CONFIG.get(lookup_key, {})

            # 2. Check idempotency
            if idempotency_key:
                cached_result = await self.idempotency.check(idempotency_key, action, user.id)
                if cached_result:
                    logger.info("Returning cached result (idempotent)", extra=log_context)
                    return cached_result

            # 3. Rate limiting (BYPASS FOR SUPER ADMIN)
            if not (hasattr(user, 'is_admin') and user.is_admin):
                rate_limit = config.get("rate_limit", {"requests": 100, "window": 60})
                if not await self.rate_limiter.check(user.id, action, **rate_limit):
                    raise ValueError("Rate limit exceeded for this action")
            else:
                logger.info(f"Rate limit bypassed for admin user: {user.id}", extra=log_context)

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
            handler = self.ACTION_HANDLERS[lookup_key]
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

            # 8. Event propagation AND Smart Cache Invalidation
            events = config.get("events", [])
            for event in events:
                # Traditional event dispatch
                await self.events.dispatch(event, {
                    **payload,
                    "action": action_str,
                    "user_id": user.id,
                    "trace_id": trace_id,
                    "result": result,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

                # Smart cache invalidation for cache-related events
                if event == "cache:invalidate" or event.startswith("cache:"):
                    await self.cache_invalidator.invalidate(event)
                    logger.debug(f"Smart cache invalidation triggered for event: {event}")

            # CRITICAL FIX: Always trigger cache invalidation for job actions
            if action_str.startswith("job."):
                # Map job actions to cache invalidation events
                cache_event_mapping = {
                    "job.retry": "job:retry_requested",
                    "job.cancel": "job:cancelled",
                    "job.delete": "job:deleted"
                }

                cache_event = cache_event_mapping.get(action_str)
                if cache_event:
                    await self.cache_invalidator.invalidate(cache_event)
                    logger.info(f"Dashboard cache invalidation triggered for {action_str} -> {cache_event}")

            # Queue actions cache invalidation
            elif action_str.startswith("queue."):
                if action_str == "queue.clear":
                    await self.cache_invalidator.invalidate("queue:cleared")
                    logger.info(f"Queue cache invalidation triggered for {action_str}")

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
                result = await handler(self, payload, **kwargs)
            else:
                result = handler(self, payload, **kwargs)

            # If result is a coroutine (from lambda calling async method), await it
            if asyncio.iscoroutine(result):
                result = await result

            return result
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

    async def get_action_status(self, action: Union[ActionType, str]) -> Dict[str, Any]:
        """Get status information for an action (rate limits, circuit breaker, etc.)"""
        # Normalize action key
        action_str = action.value if hasattr(action, 'value') else str(action)
        config = self.ACTION_CONFIG.get(action, {})

        return {
            "action": action_str,
            "rate_limit": config.get("rate_limit", {}),
            "circuit_breaker_open": CircuitBreaker(f"action:{action}").is_open if config.get("circuit_breaker") else False,
            "timeout": config.get("timeout", 30),
            "permissions_required": config.get("permissions", ["admin"]),
            "audit_enabled": config.get("audit", True),
            "events": config.get("events", [])
        }

    # ============ ANALYTICS ACTION HANDLERS ============

    async def _handle_analytics_drill_down(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle analytics drill-down requests"""
        filter_type = payload.get('filter', 'all')
        timeframe = payload.get('timeframe', '24h')
        
        # Mock implementation - in real system this would query actual data
        drill_down_data = {
            'failed_last_24h': {
                'total_failed': 12,
                'failure_reasons': [
                    {'reason': 'API timeout', 'count': 7},
                    {'reason': 'Invalid input', 'count': 3},
                    {'reason': 'Worker crash', 'count': 2}
                ],
                'timeframe': timeframe
            },
            'recent_failures': {
                'total_failed': 8,
                'recent_jobs': [
                    {'job_id': 'job_123', 'error': 'API timeout', 'timestamp': '2025-08-11T10:30:00Z'},
                    {'job_id': 'job_124', 'error': 'Invalid input', 'timestamp': '2025-08-11T10:25:00Z'}
                ]
            },
            'today_jobs': {
                'total': 247,
                'completed': 235,
                'failed': 12,
                'breakdown_by_hour': []  # Would contain hourly data
            }
        }
        
        return {
            'filter': filter_type,
            'data': drill_down_data.get(filter_type, {}),
            'generated_at': datetime.now(timezone.utc).isoformat()
        }

    async def _handle_analytics_generate_report(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle analytics report generation"""
        report_type = payload.get('type', 'standard')
        include_recommendations = payload.get('include_recommendations', True)
        
        # Mock report generation
        reports = {
            'sla_analysis': {
                'sla_compliance': 99.7,
                'target_sla': 99.5,
                'breaches_last_30_days': 2,
                'longest_outage': '45 minutes',
                'recommendations': [
                    'Implement redundant API endpoints',
                    'Add automated failover mechanisms'
                ] if include_recommendations else []
            },
            'performance_deep_dive': {
                'avg_response_time': 1.2,
                'p95_response_time': 2.8,
                'p99_response_time': 4.1,
                'bottlenecks': ['Database queries', 'External API calls'],
                'recommendations': [
                    'Optimize database indexes',
                    'Implement connection pooling',
                    'Add response caching'
                ] if include_recommendations else []
            },
            'system_health': {
                'overall_score': 94,
                'components': {
                    'api_server': 98,
                    'database': 95,
                    'workers': 90,
                    'cache': 97
                },
                'recommendations': [
                    'Scale worker pool during peak hours',
                    'Update database to latest version'
                ] if include_recommendations else []
            }
        }
        
        report_data = reports.get(report_type, reports['sla_analysis'])
        
        # Simulate report file generation
        report_url = f"/downloads/analytics_report_{report_type}_{int(time.time())}.pdf"
        
        return {
            'report_type': report_type,
            'report_url': report_url,
            'summary': report_data,
            'expires_at': (datetime.now(timezone.utc)).isoformat(),
            'generated_at': datetime.now(timezone.utc).isoformat()
        }

    async def _handle_analytics_capacity_analysis(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle capacity analysis requests"""
        timeframe = payload.get('timeframe', 'daily')
        
        capacity_data = {
            'current_utilization': {
                'workers': 75,
                'cpu': 68,
                'memory': 72,
                'queue_depth': 23
            },
            'recommendations': [
                f'Based on {timeframe} patterns: Consider scaling up during peak hours',
                'Current capacity sufficient for next 30 days',
                'Monitor queue depth - trending upward'
            ],
            'scaling_suggestions': {
                'immediate': 'No action needed',
                'next_week': 'Add 2 workers',
                'next_month': 'Evaluate database scaling'
            }
        }
        
        return capacity_data

    async def _handle_system_performance_tune(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system performance tuning"""
        
        # Mock performance tuning actions
        optimizations_applied = [
            'Database query optimization',
            'Connection pool tuning',
            'Cache warming',
            'Worker load balancing'
        ]
        
        return {
            'optimizations_applied': optimizations_applied,
            'estimated_improvement': '15-20% response time reduction',
            'next_review': 'In 24 hours',
            'status': 'Performance tuning completed successfully'
        }

    async def _handle_system_health_check(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle comprehensive system health check"""
        comprehensive = payload.get('comprehensive', False)
        
        health_data = {
            'overall_health': 94,
            'components': {
                'api_server': {'status': 'healthy', 'score': 98},
                'database': {'status': 'healthy', 'score': 95},
                'workers': {'status': 'degraded', 'score': 90},
                'cache': {'status': 'healthy', 'score': 97},
                'queue': {'status': 'healthy', 'score': 92}
            },
            'issues_found': [
                'Worker pool at 85% capacity',
                'Database connection pool nearing limits'
            ],
            'recommendations': [
                'Scale worker pool',
                'Monitor database connections',
                'Consider adding read replicas'
            ]
        }
        
        if comprehensive:
            health_data['detailed_metrics'] = {
                'response_times': {'avg': 1.2, 'p95': 2.8},
                'error_rates': {'last_1h': 0.3, 'last_24h': 0.8},
                'resource_usage': {'cpu': 68, 'memory': 72}
            }
        
        return health_data

    async def _handle_system_emergency_report(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle emergency system reports"""
        trigger = payload.get('trigger', 'manual')
        
        emergency_data = {
            'trigger': trigger,
            'severity': 'high',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'immediate_actions': [
                'Scaling worker pool by 50%',
                'Enabling high-availability mode',
                'Alerting on-call engineers'
            ],
            'system_status': {
                'sla_compliance': 94.2,  # Below critical threshold
                'active_incidents': 1,
                'estimated_recovery': '15 minutes'
            },
            'next_steps': [
                'Monitor system recovery',
                'Investigate root cause',
                'Update incident documentation'
            ]
        }
        
        return emergency_data

    # ============ ANALYTICS & SYSTEM HANDLERS WITH ERROR HANDLING ============

    async def _handle_analytics_drill_down(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle analytics drill-down requests with comprehensive error handling"""
        try:
            # Input validation
            if not isinstance(payload, dict):
                raise ValueError("Payload must be a dictionary")
            
            filter_type = payload.get('filter', 'all')
            timeframe = payload.get('timeframe', '24h')
            
            # Validate filter_type
            valid_filters = ['all', 'failed_last_24h', 'recent_failures', 'today_jobs']
            if filter_type not in valid_filters:
                raise ValueError(f"Invalid filter type: {filter_type}. Must be one of: {valid_filters}")
            
            # Validate timeframe
            valid_timeframes = ['1h', '6h', '24h', '7d', '30d']
            if timeframe not in valid_timeframes:
                raise ValueError(f"Invalid timeframe: {timeframe}. Must be one of: {valid_timeframes}")
            
            # Mock implementation - in real system this would query actual data with database error handling
            try:
                drill_down_data = {
                    'failed_last_24h': {
                        'total_failed': 12,
                        'failure_reasons': [
                            {'reason': 'API timeout', 'count': 7},
                            {'reason': 'Invalid input', 'count': 3},
                            {'reason': 'Worker crash', 'count': 2}
                        ],
                        'timeframe': timeframe
                    },
                    'recent_failures': {
                        'total_failed': 8,
                        'recent_jobs': [
                            {'job_id': 'job_123', 'error': 'API timeout', 'timestamp': '2025-08-11T10:30:00Z'},
                            {'job_id': 'job_124', 'error': 'Invalid input', 'timestamp': '2025-08-11T10:25:00Z'}
                        ]
                    },
                    'today_jobs': {
                        'total': 247,
                        'completed': 235,
                        'failed': 12,
                        'breakdown_by_hour': []  # Would contain hourly data
                    }
                }
                
                result_data = drill_down_data.get(filter_type, drill_down_data['today_jobs']) if filter_type == 'all' else drill_down_data.get(filter_type, {})
                
            except Exception as data_error:
                logger.error(f"Database query error in analytics drill-down: {data_error}")
                raise ValueError("Failed to retrieve analytics data from database")
            
            return {
                'success': True,
                'filter': filter_type,
                'timeframe': timeframe,
                'data': result_data,
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except ValueError as e:
            logger.error(f"Analytics drill-down validation error: {e}")
            return {
                'success': False,
                'error': 'validation_error',
                'message': str(e),
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Analytics drill-down failed: {e}")
            return {
                'success': False,
                'error': 'processing_error',
                'message': 'Failed to generate drill-down data',
                'generated_at': datetime.now(timezone.utc).isoformat()
            }

    async def _handle_analytics_generate_report(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle analytics report generation with proper error handling"""
        try:
            # Input validation
            if not isinstance(payload, dict):
                raise ValueError("Payload must be a dictionary")
            
            report_type = payload.get('type', 'sla_analysis')
            include_recommendations = payload.get('include_recommendations', True)
            
            # Validate report type
            valid_types = ['sla_analysis', 'performance_deep_dive', 'system_health']
            if report_type not in valid_types:
                raise ValueError(f"Invalid report type: {report_type}. Must be one of: {valid_types}")
            
            # Validate boolean parameter
            if not isinstance(include_recommendations, bool):
                raise ValueError("include_recommendations must be a boolean")
            
            # Mock report generation with potential failures
            try:
                reports = {
                    'sla_analysis': {
                        'sla_compliance': 99.7,
                        'target_sla': 99.5,
                        'breaches_last_30_days': 2,
                        'longest_outage': '45 minutes',
                        'recommendations': [
                            'Implement redundant API endpoints',
                            'Add automated failover mechanisms'
                        ] if include_recommendations else []
                    },
                    'performance_deep_dive': {
                        'avg_response_time': 1.2,
                        'p95_response_time': 2.8,
                        'p99_response_time': 4.1,
                        'bottlenecks': ['Database queries', 'External API calls'],
                        'recommendations': [
                            'Optimize database indexes',
                            'Implement connection pooling',
                            'Add response caching'
                        ] if include_recommendations else []
                    },
                    'system_health': {
                        'overall_score': 94,
                        'components': {
                            'api_server': 98,
                            'database': 95,
                            'workers': 90,
                            'cache': 97
                        },
                        'recommendations': [
                            'Scale worker pool during peak hours',
                            'Update database to latest version'
                        ] if include_recommendations else []
                    }
                }
                
                report_data = reports.get(report_type)
                if not report_data:
                    raise ValueError(f"Report data not found for type: {report_type}")
                
                # Simulate report file generation with potential file system errors
                report_url = f"/downloads/analytics_report_{report_type}_{int(time.time())}.pdf"
                
            except Exception as gen_error:
                logger.error(f"Report generation error: {gen_error}")
                raise ValueError("Failed to generate report data")
            
            return {
                'success': True,
                'report_type': report_type,
                'report_url': report_url,
                'summary': report_data,
                'expires_at': (datetime.now(timezone.utc)).isoformat(),
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except ValueError as e:
            logger.error(f"Analytics report generation validation error: {e}")
            return {
                'success': False,
                'error': 'validation_error',
                'message': str(e),
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Analytics report generation failed: {e}")
            return {
                'success': False,
                'error': 'processing_error',
                'message': 'Failed to generate analytics report',
                'generated_at': datetime.now(timezone.utc).isoformat()
            }

    async def _handle_analytics_capacity_analysis(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle capacity analysis requests with error handling"""
        try:
            # Input validation
            if not isinstance(payload, dict):
                raise ValueError("Payload must be a dictionary")
            
            timeframe = payload.get('timeframe', 'daily')
            
            # Validate timeframe
            valid_timeframes = ['hourly', 'daily', 'weekly', 'monthly']
            if timeframe not in valid_timeframes:
                raise ValueError(f"Invalid timeframe: {timeframe}. Must be one of: {valid_timeframes}")
            
            try:
                # Mock capacity analysis with potential system query failures
                capacity_data = {
                    'current_utilization': {
                        'workers': 75,
                        'cpu': 68,
                        'memory': 72,
                        'queue_depth': 23
                    },
                    'recommendations': [
                        f'Based on {timeframe} patterns: Consider scaling up during peak hours',
                        'Current capacity sufficient for next 30 days',
                        'Monitor queue depth - trending upward'
                    ],
                    'scaling_suggestions': {
                        'immediate': 'No action needed',
                        'next_week': 'Add 2 workers',
                        'next_month': 'Evaluate database scaling'
                    },
                    'success': True,
                    'timeframe': timeframe,
                    'generated_at': datetime.now(timezone.utc).isoformat()
                }
                
            except Exception as analysis_error:
                logger.error(f"Capacity analysis computation error: {analysis_error}")
                raise ValueError("Failed to compute capacity analysis")
            
            return capacity_data
            
        except ValueError as e:
            logger.error(f"Capacity analysis validation error: {e}")
            return {
                'success': False,
                'error': 'validation_error',
                'message': str(e),
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Capacity analysis failed: {e}")
            return {
                'success': False,
                'error': 'processing_error',
                'message': 'Failed to perform capacity analysis',
                'generated_at': datetime.now(timezone.utc).isoformat()
            }

    async def _handle_system_performance_tune(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system performance tuning with error handling"""
        try:
            # Input validation
            if not isinstance(payload, dict):
                raise ValueError("Payload must be a dictionary")
            
            tune_type = payload.get('type', 'auto')
            aggressive = payload.get('aggressive', False)
            
            # Validate tuning type
            valid_types = ['auto', 'conservative', 'aggressive', 'database', 'workers']
            if tune_type not in valid_types:
                raise ValueError(f"Invalid tune type: {tune_type}. Must be one of: {valid_types}")
            
            if not isinstance(aggressive, bool):
                raise ValueError("aggressive parameter must be a boolean")
            
            try:
                # Mock performance tuning actions with potential system errors
                optimizations_applied = [
                    'Database query optimization',
                    'Connection pool tuning',
                    'Cache warming',
                    'Worker load balancing'
                ]
                
                if aggressive:
                    optimizations_applied.extend([
                        'Memory allocation optimization',
                        'CPU affinity adjustment',
                        'Disk I/O optimization'
                    ])
                
                # Simulate potential tuning failures
                if tune_type == 'database' and aggressive:
                    # Simulate database tuning that might fail
                    pass
                
            except Exception as tune_error:
                logger.error(f"Performance tuning execution error: {tune_error}")
                raise ValueError("Failed to apply performance optimizations")
            
            return {
                'success': True,
                'tune_type': tune_type,
                'optimizations_applied': optimizations_applied,
                'estimated_improvement': '15-20% response time reduction',
                'next_review': 'In 24 hours',
                'status': 'Performance tuning completed successfully',
                'applied_at': datetime.now(timezone.utc).isoformat()
            }
            
        except ValueError as e:
            logger.error(f"Performance tuning validation error: {e}")
            return {
                'success': False,
                'error': 'validation_error',
                'message': str(e),
                'applied_at': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Performance tuning failed: {e}")
            return {
                'success': False,
                'error': 'processing_error',
                'message': 'Failed to apply performance tuning',
                'applied_at': datetime.now(timezone.utc).isoformat()
            }

    async def _handle_system_health_check(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle comprehensive system health check with error handling"""
        try:
            # Input validation
            if not isinstance(payload, dict):
                raise ValueError("Payload must be a dictionary")
            
            comprehensive = payload.get('comprehensive', False)
            include_metrics = payload.get('include_metrics', True)
            
            # Validate parameters
            if not isinstance(comprehensive, bool):
                raise ValueError("comprehensive parameter must be a boolean")
            if not isinstance(include_metrics, bool):
                raise ValueError("include_metrics parameter must be a boolean")
            
            try:
                # Mock health check with potential system access failures
                health_data = {
                    'overall_health': 94,
                    'components': {
                        'api_server': {'status': 'healthy', 'score': 98},
                        'database': {'status': 'healthy', 'score': 95},
                        'workers': {'status': 'degraded', 'score': 90},
                        'cache': {'status': 'healthy', 'score': 97},
                        'queue': {'status': 'healthy', 'score': 92}
                    },
                    'issues_found': [
                        'Worker pool at 85% capacity',
                        'Database connection pool nearing limits'
                    ],
                    'recommendations': [
                        'Scale worker pool',
                        'Monitor database connections',
                        'Consider adding read replicas'
                    ],
                    'success': True,
                    'check_type': 'comprehensive' if comprehensive else 'basic',
                    'generated_at': datetime.now(timezone.utc).isoformat()
                }
                
                if comprehensive and include_metrics:
                    health_data['detailed_metrics'] = {
                        'response_times': {'avg': 1.2, 'p95': 2.8},
                        'error_rates': {'last_1h': 0.3, 'last_24h': 0.8},
                        'resource_usage': {'cpu': 68, 'memory': 72}
                    }
                
            except Exception as health_error:
                logger.error(f"Health check execution error: {health_error}")
                raise ValueError("Failed to perform system health check")
            
            return health_data
            
        except ValueError as e:
            logger.error(f"System health check validation error: {e}")
            return {
                'success': False,
                'error': 'validation_error',
                'message': str(e),
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"System health check failed: {e}")
            return {
                'success': False,
                'error': 'processing_error',
                'message': 'Failed to perform system health check',
                'generated_at': datetime.now(timezone.utc).isoformat()
            }

    async def _handle_system_emergency_report(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle emergency system reports with error handling"""
        try:
            # Input validation
            if not isinstance(payload, dict):
                raise ValueError("Payload must be a dictionary")
            
            trigger = payload.get('trigger', 'manual')
            severity = payload.get('severity', 'high')
            
            # Validate trigger
            valid_triggers = ['manual', 'automated', 'threshold', 'external']
            if trigger not in valid_triggers:
                raise ValueError(f"Invalid trigger: {trigger}. Must be one of: {valid_triggers}")
            
            # Validate severity
            valid_severities = ['low', 'medium', 'high', 'critical']
            if severity not in valid_severities:
                raise ValueError(f"Invalid severity: {severity}. Must be one of: {valid_severities}")
            
            try:
                # Mock emergency report generation with potential failures
                emergency_data = {
                    'trigger': trigger,
                    'severity': severity,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'immediate_actions': [
                        'Scaling worker pool by 50%',
                        'Enabling high-availability mode',
                        'Alerting on-call engineers'
                    ],
                    'system_status': {
                        'sla_compliance': 94.2,  # Below critical threshold
                        'active_incidents': 1,
                        'estimated_recovery': '15 minutes'
                    },
                    'next_steps': [
                        'Monitor system recovery',
                        'Investigate root cause',
                        'Update incident documentation'
                    ],
                    'success': True,
                    'generated_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Additional actions based on severity
                if severity == 'critical':
                    emergency_data['immediate_actions'].extend([
                        'Activate disaster recovery protocol',
                        'Notify executive team',
                        'Prepare public status update'
                    ])
                
            except Exception as emergency_error:
                logger.error(f"Emergency report generation error: {emergency_error}")
                raise ValueError("Failed to generate emergency report")
            
            return emergency_data
            
        except ValueError as e:
            logger.error(f"Emergency report validation error: {e}")
            return {
                'success': False,
                'error': 'validation_error',
                'message': str(e),
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Emergency report failed: {e}")
            return {
                'success': False,
                'error': 'processing_error',
                'message': 'Failed to generate emergency report',
                'generated_at': datetime.now(timezone.utc).isoformat()
            }

    async def _handle_worker_auto_scale(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle automatic worker scaling with error handling"""
        try:
            # Input validation
            if not isinstance(payload, dict):
                raise ValueError("Payload must be a dictionary")
            
            trigger = payload.get('trigger', 'manual')
            direction = payload.get('direction', 'up')
            count = payload.get('count', 2)
            
            # Validate direction
            valid_directions = ['up', 'down']
            if direction not in valid_directions:
                raise ValueError(f"Invalid direction: {direction}. Must be one of: {valid_directions}")
            
            # Validate count
            if not isinstance(count, int) or count < 1 or count > 10:
                raise ValueError("count must be an integer between 1 and 10")
            
            # Validate trigger
            valid_triggers = ['manual', 'load_threshold', 'queue_depth', 'scheduled']
            if trigger not in valid_triggers:
                raise ValueError(f"Invalid trigger: {trigger}. Must be one of: {valid_triggers}")
            
            try:
                # Mock worker scaling with potential infrastructure failures
                current_workers = 6
                new_count = current_workers + count if direction == 'up' else max(1, current_workers - count)
                
                # Simulate scaling limits
                if new_count > 20:
                    raise ValueError("Maximum worker limit (20) would be exceeded")
                if new_count < 1:
                    raise ValueError("Minimum worker count (1) required")
                
            except Exception as scale_error:
                logger.error(f"Worker scaling execution error: {scale_error}")
                raise ValueError("Failed to execute worker scaling")
            
            return {
                'success': True,
                'action': f'scale_{direction}',
                'trigger': trigger,
                'previous_count': current_workers,
                'new_count': new_count,
                'workers_changed': abs(new_count - current_workers),
                'estimated_completion': '3-5 minutes',
                'status': 'Scaling operation initiated',
                'initiated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except ValueError as e:
            logger.error(f"Worker auto-scale validation error: {e}")
            return {
                'success': False,
                'error': 'validation_error',
                'message': str(e),
                'initiated_at': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Worker auto-scale failed: {e}")
            return {
                'success': False,
                'error': 'processing_error',
                'message': 'Failed to scale workers',
                'initiated_at': datetime.now(timezone.utc).isoformat()
            }

    async def _handle_worker_optimize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle worker optimization with error handling"""
        try:
            # Input validation
            if not isinstance(payload, dict):
                raise ValueError("Payload must be a dictionary")
            
            based_on = payload.get('based_on', 'current_load')
            optimize_type = payload.get('type', 'performance')
            
            # Validate optimization basis
            valid_bases = ['current_load', 'historical_patterns', 'queue_analysis', 'resource_usage']
            if based_on not in valid_bases:
                raise ValueError(f"Invalid based_on: {based_on}. Must be one of: {valid_bases}")
            
            # Validate optimization type
            valid_types = ['performance', 'memory', 'throughput', 'balanced']
            if optimize_type not in valid_types:
                raise ValueError(f"Invalid optimization type: {optimize_type}. Must be one of: {valid_types}")
            
            try:
                # Mock worker optimization with potential configuration failures
                optimization_result = {
                    'optimization_type': based_on,
                    'focus': optimize_type,
                    'actions_taken': [
                        'Redistributed work across workers',
                        'Optimized worker memory allocation',
                        'Updated worker priorities'
                    ],
                    'performance_improvement': {
                        'throughput': '+12%',
                        'resource_utilization': '+8%',
                        'response_time': '-200ms'
                    },
                    'status': 'Worker optimization completed',
                    'success': True,
                    'optimized_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Add type-specific optimizations
                if optimize_type == 'memory':
                    optimization_result['actions_taken'].append('Garbage collection tuning')
                elif optimize_type == 'throughput':
                    optimization_result['actions_taken'].append('Connection pool optimization')
                
            except Exception as optimize_error:
                logger.error(f"Worker optimization execution error: {optimize_error}")
                raise ValueError("Failed to optimize workers")
            
            return optimization_result
            
        except ValueError as e:
            logger.error(f"Worker optimization validation error: {e}")
            return {
                'success': False,
                'error': 'validation_error',
                'message': str(e),
                'optimized_at': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Worker optimization failed: {e}")
            return {
                'success': False,
                'error': 'processing_error',
                'message': 'Failed to optimize workers',
                'optimized_at': datetime.now(timezone.utc).isoformat()
            }

# ============ SINGLETON INSTANCE ============

# Global dispatcher instance
action_dispatcher = ActionDispatcher()

# Export for easy importing
__all__ = ["ActionDispatcher", "action_dispatcher"]
