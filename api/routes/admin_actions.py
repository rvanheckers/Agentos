"""
Enterprise Admin Actions API
Single endpoint for all admin actions with full enterprise features
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import uuid4

from fastapi import (
    APIRouter, 
    HTTPException, 
    Depends, 
    Header, 
    Request,
    Response,
    status
)

# Import our enterprise models and services
from api.models.action_models import (
    ActionRequest, 
    ActionResponse, 
    ActionError, 
    ActionType
)
from services.action_dispatcher import action_dispatcher
from services.authorization_service import authorization_service, User
from services.idempotency_service import idempotency_service
from services.rate_limiter import rate_limiter, LimitType
from services.audit_log import audit_log

import logging

logger = logging.getLogger("agentos.admin_actions")

# Create router
router = APIRouter(
    prefix="/api/admin",
    tags=["admin-actions"]
)

def generate_trace_id() -> str:
    """Generate unique trace ID"""
    return str(uuid4())

async def get_current_user(request: Request) -> User:
    """Extract user from request - TODO: implement real auth"""
    # For now, return a mock admin user
    # In production, this would extract user from JWT token or session
    return User(
        id="admin",
        email="admin@agentos.ai", 
        roles=["admin"],
        permissions=[],
        is_admin=True,
        is_active=True
    )

@router.post(
    "/action",
    response_model=ActionResponse,
    summary="Execute Admin Action",
    description="""
    **Enterprise Single Action Endpoint**
    
    Execute any admin action through a unified, type-safe interface with full enterprise features:
    
    - **Type Safety**: Discriminated unions ensure correct payloads
    - **Authorization**: Fine-grained permission checking
    - **Audit Logging**: Comprehensive compliance logging
    - **Distributed Tracing**: Full request tracing with `X-Trace-Id`
    
    **Available Actions:**
    - `job.retry` - Retry a failed job
    - `job.cancel` - Cancel a running job  
    - `queue.clear` - Clear job queue (admin only)
    - `worker.restart` - Restart workers
    - `cache.clear` - Clear system cache
    """
)
async def execute_action(
    request: ActionRequest,
    current_request: Request,
    response: Response,
    x_trace_id: Optional[str] = Header(None, alias="X-Trace-Id"),
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key")
) -> ActionResponse:
    """
    Execute admin action with full enterprise features
    """
    
    # Setup tracing
    trace_id = x_trace_id or generate_trace_id()
    execution_start = time.time()
    
    # Add trace ID to response headers
    response.headers["X-Trace-Id"] = trace_id
    
    # Get user info
    client_ip = current_request.client.host if current_request.client else None
    user_agent = current_request.headers.get("user-agent", "unknown")
    
    logger.info(f"Action execution started: {request.action.value}", extra={
        "trace_id": trace_id,
        "action": request.action.value,
        "ip_address": client_ip
    })
    
    try:
        # Get current user
        user = await get_current_user(current_request)
        
        # Rate limiting check
        rate_limit_passed = await rate_limiter.check(
            user_id=user.id,
            action=request.action.value,
            requests=50,  # 50 requests per minute per action
            window=60,
            limit_type=LimitType.SLIDING_WINDOW
        )
        
        if not rate_limit_passed:
            await audit_log.log_denied_attempt(
                user_id=user.id,
                action=request.action.value,
                payload=request.payload.dict(),
                trace_id=trace_id,
                reason="Rate limit exceeded",
                ip_address=client_ip,
                user_agent=user_agent
            )
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for action {request.action.value}",
                headers={"X-Trace-Id": trace_id}
            )
        
        # Authorization check
        authorized = await authorization_service.check_permissions(
            user=user,
            action=request.action.value,
            payload=request.payload.dict()
        )
        
        if not authorized:
            await audit_log.log_denied_attempt(
                user_id=user.id,
                action=request.action.value,
                payload=request.payload.dict(),
                trace_id=trace_id,
                reason="Insufficient permissions",
                ip_address=client_ip,
                user_agent=user_agent
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions for action {request.action.value}",
                headers={"X-Trace-Id": trace_id}
            )
        
        # Idempotency check if key provided
        if x_idempotency_key:
            idempotency_result = await idempotency_service.check(
                idempotency_key=x_idempotency_key,
                action=request.action.value,
                user_id=user.id,
                payload=request.payload.dict()
            )
            
            if idempotency_result["exists"]:
                logger.info(f"Returning cached result for idempotent request", extra={
                    "trace_id": trace_id,
                    "idempotency_key": x_idempotency_key
                })
                
                cached_result = idempotency_result["result"]
                return ActionResponse(
                    success=cached_result["success"],
                    action=request.action,
                    result=cached_result.get("result", {}),
                    trace_id=trace_id,
                    timestamp=datetime.now(timezone.utc),
                    duration_ms=0.0  # Cached response
                )
        
        # Execute action via dispatcher
        result = await action_dispatcher.execute(
            action=request.action,
            payload=request.payload.dict(),
            user=user,
            trace_id=trace_id,
            idempotency_key=x_idempotency_key
        )
        
        execution_time = (time.time() - execution_start) * 1000  # ms
        
        # Audit successful execution
        await audit_log.log_action(
            user_id=user.id,
            action=request.action.value,
            payload=request.payload.dict(),
            result=result,
            trace_id=trace_id,
            execution_time_ms=execution_time,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        logger.info(f"Action executed successfully: {request.action.value}", extra={
            "trace_id": trace_id,
            "execution_time_ms": execution_time,
            "user_id": user.id
        })
        
        return ActionResponse(
            success=True,
            action=request.action,
            result=result.get("result", {}),
            trace_id=trace_id,
            timestamp=datetime.now(timezone.utc),
            duration_ms=execution_time
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
        
    except Exception as e:
        execution_time = (time.time() - execution_start) * 1000
        
        # Get user for audit (if we got that far)
        try:
            user = await get_current_user(current_request)
            user_id = user.id
        except:
            user_id = "unknown"
        
        # Audit failure
        await audit_log.log_action_failure(
            user_id=user_id,
            action=request.action.value,
            payload=request.payload.dict(),
            error=str(e),
            trace_id=trace_id,
            execution_time_ms=execution_time,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        logger.error(f"Action failed: {request.action.value}", extra={
            "trace_id": trace_id,
            "error": str(e),
            "execution_time_ms": execution_time,
            "user_id": user_id
        })
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Action failed: {str(e)}",
            headers={"X-Trace-Id": trace_id}
        )

# Export router
__all__ = ["router"]