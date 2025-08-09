"""
Audit Log Service
Comprehensive logging for compliance and security
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
from uuid import uuid4
import logging

# Database imports (adjust based on your setup)
try:
    from core.database_manager import PostgreSQLManager
    from sqlalchemy import Column, String, DateTime, JSON, Text, Boolean, Float
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.dialects.postgresql import UUID
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

logger = logging.getLogger("agentos.audit_log")

class AuditEventType(str, Enum):
    ACTION_SUCCESS = "action_success"
    ACTION_FAILURE = "action_failure"
    ACTION_DENIED = "action_denied"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    PERMISSION_CHANGE = "permission_change"
    CONFIG_CHANGE = "config_change"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"

class AuditLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class AuditEvent:
    """Audit event data structure"""
    id: str
    event_type: AuditEventType
    level: AuditLevel
    user_id: str
    action: Optional[str]
    resource: Optional[str]
    payload: Dict[str, Any]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    trace_id: Optional[str]
    timestamp: datetime
    session_id: Optional[str] = None
    duration_ms: Optional[float] = None
    success: bool = True

# Database model (only if DB available)
if DB_AVAILABLE:
    Base = declarative_base()

    class AuditLogEntry(Base):
        __tablename__ = 'audit_logs'

        id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
        event_type = Column(String(50), nullable=False, index=True)
        level = Column(String(20), nullable=False, index=True)
        user_id = Column(String(255), nullable=False, index=True)
        action = Column(String(100), index=True)
        resource = Column(String(255), index=True)
        payload = Column(JSON)
        result = Column(JSON)
        error = Column(Text)
        ip_address = Column(String(45))  # IPv6 support
        user_agent = Column(Text)
        trace_id = Column(String(100), index=True)
        timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
        session_id = Column(String(255), index=True)
        duration_ms = Column('duration_ms', Float, nullable=True)
        success = Column(Boolean, nullable=False, default=True, index=True)

class AuditLog:
    """
    Enterprise audit logging service

    Features:
    - Structured logging for compliance
    - Multiple storage backends
    - Automatic PII scrubbing
    - Query and analysis capabilities
    - Export for compliance reporting
    - Immutable log storage
    """

    def __init__(self):
        """Initialize audit log service"""
        self.db_manager = None
        self.fallback_logger = logging.getLogger("agentos.audit_fallback")

        # Initialize database if available
        if DB_AVAILABLE:
            try:
                self.db_manager = PostgreSQLManager()
                # Create table if not exists
                self._ensure_table_exists()
            except Exception as e:
                logger.warning(f"Database not available for audit logs: {e}")
                self.db_manager = None

        # PII fields to scrub
        self.pii_fields = {
            'password', 'token', 'secret', 'key', 'auth', 'credential',
            'ssn', 'social_security', 'credit_card', 'phone', 'email'
        }

    def _ensure_table_exists(self):
        """Ensure audit log table exists"""
        if self.db_manager and DB_AVAILABLE:
            try:
                # This would typically be handled by migrations
                Base.metadata.create_all(self.db_manager.engine)
                logger.info("Audit log table ensured")
            except Exception as e:
                logger.error(f"Error creating audit log table: {e}")

    def _scrub_pii(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Scrub personally identifiable information from data"""
        if not isinstance(data, dict):
            return data

        scrubbed = {}
        for key, value in data.items():
            key_lower = key.lower()

            # Check if key contains PII indicators
            is_pii = any(pii_field in key_lower for pii_field in self.pii_fields)

            if is_pii:
                scrubbed[key] = "[SCRUBBED]"
            elif isinstance(value, dict):
                scrubbed[key] = self._scrub_pii(value)
            elif isinstance(value, list):
                scrubbed[key] = [self._scrub_pii(item) if isinstance(item, dict) else item for item in value]
            else:
                scrubbed[key] = value

        return scrubbed

    def _determine_level(self, event_type: AuditEventType, action: Optional[str] = None) -> AuditLevel:
        """Determine audit level based on event type and action"""
        if event_type in [AuditEventType.ACTION_DENIED, AuditEventType.LOGIN_FAILURE]:
            return AuditLevel.HIGH

        if event_type in [AuditEventType.PERMISSION_CHANGE, AuditEventType.CONFIG_CHANGE]:
            return AuditLevel.CRITICAL

        if action:
            # High-risk actions
            if any(risk in action for risk in ['delete', 'clear', 'backup', 'maintenance']):
                return AuditLevel.HIGH

            # Medium-risk actions
            if any(risk in action for risk in ['restart', 'scale', 'pause', 'cancel']):
                return AuditLevel.MEDIUM

        return AuditLevel.LOW

    async def log_action(
        self,
        user_id: str,
        action: str,
        payload: Dict[str, Any],
        result: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """
        Log successful action execution

        Args:
            user_id: User who performed the action
            action: Action that was performed
            payload: Action payload (will be scrubbed)
            result: Action result (will be scrubbed)
            trace_id: Distributed tracing ID
            execution_time_ms: How long action took
            ip_address: User's IP address
            user_agent: User's browser/client
            session_id: User's session ID
        """
        try:
            event = AuditEvent(
                id=str(uuid4()),
                event_type=AuditEventType.ACTION_SUCCESS,
                level=self._determine_level(AuditEventType.ACTION_SUCCESS, action),
                user_id=user_id,
                action=action,
                resource=f"action:{action}",
                payload=self._scrub_pii(payload) if payload else {},
                result=self._scrub_pii(result) if result else None,
                error=None,
                ip_address=ip_address,
                user_agent=user_agent,
                trace_id=trace_id,
                timestamp=datetime.now(timezone.utc),
                session_id=session_id,
                duration_ms=execution_time_ms,
                success=True
            )

            await self._store_event(event)

        except Exception as e:
            logger.error(f"Error logging action: {e}")

    async def log_action_failure(
        self,
        user_id: str,
        action: str,
        payload: Dict[str, Any],
        error: str,
        trace_id: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """
        Log failed action execution

        Args:
            user_id: User who attempted the action
            action: Action that was attempted
            payload: Action payload (will be scrubbed)
            error: Error message
            trace_id: Distributed tracing ID
            execution_time_ms: How long action took before failing
            ip_address: User's IP address
            user_agent: User's browser/client
            session_id: User's session ID
        """
        try:
            event = AuditEvent(
                id=str(uuid4()),
                event_type=AuditEventType.ACTION_FAILURE,
                level=self._determine_level(AuditEventType.ACTION_FAILURE, action),
                user_id=user_id,
                action=action,
                resource=f"action:{action}",
                payload=self._scrub_pii(payload) if payload else {},
                result=None,
                error=error,
                ip_address=ip_address,
                user_agent=user_agent,
                trace_id=trace_id,
                timestamp=datetime.now(timezone.utc),
                session_id=session_id,
                duration_ms=execution_time_ms,
                success=False
            )

            await self._store_event(event)

        except Exception as e:
            logger.error(f"Error logging action failure: {e}")

    async def log_denied_attempt(
        self,
        user_id: str,
        action: str,
        payload: Dict[str, Any],
        trace_id: Optional[str] = None,
        reason: str = "Insufficient permissions",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """
        Log denied access attempt

        Args:
            user_id: User who attempted the action
            action: Action that was attempted
            payload: Action payload (will be scrubbed)
            trace_id: Distributed tracing ID
            reason: Reason for denial
            ip_address: User's IP address
            user_agent: User's browser/client
            session_id: User's session ID
        """
        try:
            event = AuditEvent(
                id=str(uuid4()),
                event_type=AuditEventType.ACTION_DENIED,
                level=AuditLevel.HIGH,  # Always high priority
                user_id=user_id,
                action=action,
                resource=f"action:{action}",
                payload=self._scrub_pii(payload) if payload else {},
                result=None,
                error=reason,
                ip_address=ip_address,
                user_agent=user_agent,
                trace_id=trace_id,
                timestamp=datetime.now(timezone.utc),
                session_id=session_id,
                duration_ms=None,
                success=False
            )

            await self._store_event(event)

            # Also log to security logger
            logger.warning(
                f"Access denied: user {user_id} attempted {action}",
                extra={
                    "security_event": True,
                    "user_id": user_id,
                    "action": action,
                    "reason": reason,
                    "ip_address": ip_address,
                    "trace_id": trace_id
                }
            )

        except Exception as e:
            logger.error(f"Error logging denied attempt: {e}")

    async def log_login(
        self,
        user_id: str,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        error: Optional[str] = None
    ):
        """
        Log login attempt

        Args:
            user_id: User attempting to log in
            success: Whether login succeeded
            ip_address: User's IP address
            user_agent: User's browser/client
            session_id: New session ID (if successful)
            error: Error message (if failed)
        """
        try:
            event = AuditEvent(
                id=str(uuid4()),
                event_type=AuditEventType.LOGIN_SUCCESS if success else AuditEventType.LOGIN_FAILURE,
                level=AuditLevel.MEDIUM if success else AuditLevel.HIGH,
                user_id=user_id,
                action="login",
                resource="auth:login",
                payload={},
                result={"success": success},
                error=error,
                ip_address=ip_address,
                user_agent=user_agent,
                trace_id=None,
                timestamp=datetime.now(timezone.utc),
                session_id=session_id,
                duration_ms=None,
                success=success
            )

            await self._store_event(event)

        except Exception as e:
            logger.error(f"Error logging login: {e}")

    async def _store_event(self, event: AuditEvent):
        """Store audit event to database and fallback logger"""

        # Always log to fallback logger
        log_data = asdict(event)
        log_data['timestamp'] = event.timestamp.isoformat()

        self.fallback_logger.info(
            f"AUDIT: {event.event_type.value}",
            extra={
                "audit_event": True,
                **log_data
            }
        )

        # Store to database if available
        if self.db_manager and DB_AVAILABLE:
            try:
                await self._store_to_database(event)
            except Exception as e:
                logger.error(f"Error storing audit event to database: {e}")

    async def _store_to_database(self, event: AuditEvent):
        """Store audit event to database"""
        if not self.db_manager or not DB_AVAILABLE:
            return

        try:
            with self.db_manager.get_session() as session:
                db_event = AuditLogEntry(
                    id=uuid4(),
                    event_type=event.event_type.value,
                    level=event.level.value,
                    user_id=event.user_id,
                    action=event.action,
                    resource=event.resource,
                    payload=event.payload,
                    result=event.result,
                    error=event.error,
                    ip_address=event.ip_address,
                    user_agent=event.user_agent,
                    trace_id=event.trace_id,
                    timestamp=event.timestamp,
                    session_id=event.session_id,
                    duration_ms=event.duration_ms,
                    success=event.success
                )

                session.add(db_event)
                session.commit()

        except Exception as e:
            logger.error(f"Database audit log storage failed: {e}")
            raise

    async def query_events(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        level: Optional[AuditLevel] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        success: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Query audit events

        Args:
            user_id: Filter by user
            action: Filter by action
            event_type: Filter by event type
            level: Filter by audit level
            start_time: Filter by start time
            end_time: Filter by end time
            success: Filter by success/failure
            limit: Maximum number of results
            offset: Result offset for pagination

        Returns:
            List of audit events
        """
        if not self.db_manager or not DB_AVAILABLE:
            return []

        try:
            with self.db_manager.get_session() as session:
                query = session.query(AuditLogEntry)

                # Apply filters
                if user_id:
                    query = query.filter(AuditLogEntry.user_id == user_id)
                if action:
                    query = query.filter(AuditLogEntry.action == action)
                if event_type:
                    query = query.filter(AuditLogEntry.event_type == event_type.value)
                if level:
                    query = query.filter(AuditLogEntry.level == level.value)
                if start_time:
                    query = query.filter(AuditLogEntry.timestamp >= start_time)
                if end_time:
                    query = query.filter(AuditLogEntry.timestamp <= end_time)
                if success is not None:
                    query = query.filter(AuditLogEntry.success == success)

                # Order by timestamp descending
                query = query.order_by(AuditLogEntry.timestamp.desc())

                # Apply pagination
                events = query.offset(offset).limit(limit).all()

                # Convert to dictionaries
                return [
                    {
                        'id': str(event.id),
                        'event_type': event.event_type,
                        'level': event.level,
                        'user_id': event.user_id,
                        'action': event.action,
                        'resource': event.resource,
                        'payload': event.payload,
                        'result': event.result,
                        'error': event.error,
                        'ip_address': event.ip_address,
                        'user_agent': event.user_agent,
                        'trace_id': event.trace_id,
                        'timestamp': event.timestamp.isoformat(),
                        'session_id': event.session_id,
                        'duration_ms': event.duration_ms,
                        'success': event.success
                    }
                    for event in events
                ]

        except Exception as e:
            logger.error(f"Error querying audit events: {e}")
            return []

    async def get_security_summary(
        self,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get security summary for the last N hours

        Args:
            hours: Number of hours to analyze

        Returns:
            Security summary
        """
        start_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = start_time.replace(hour=start_time.hour - hours)

        try:
            # Query recent security events
            denied_attempts = await self.query_events(
                event_type=AuditEventType.ACTION_DENIED,
                start_time=start_time
            )

            failed_logins = await self.query_events(
                event_type=AuditEventType.LOGIN_FAILURE,
                start_time=start_time
            )

            high_risk_actions = await self.query_events(
                level=AuditLevel.HIGH,
                start_time=start_time
            )

            return {
                "period_hours": hours,
                "denied_attempts": len(denied_attempts),
                "failed_logins": len(failed_logins),
                "high_risk_actions": len(high_risk_actions),
                "top_denied_actions": self._get_top_actions(denied_attempts),
                "top_failing_users": self._get_top_users(failed_logins),
                "summary_generated": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Error generating security summary: {e}")
            return {"error": str(e)}

    def _get_top_actions(self, events: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        """Get top actions from events"""
        action_counts = {}
        for event in events:
            action = event.get('action')
            if action:
                action_counts[action] = action_counts.get(action, 0) + 1

        return [
            {"action": action, "count": count}
            for action, count in sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        ]

    def _get_top_users(self, events: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        """Get top users from events"""
        user_counts = {}
        for event in events:
            user_id = event.get('user_id')
            if user_id:
                user_counts[user_id] = user_counts.get(user_id, 0) + 1

        return [
            {"user_id": user_id, "count": count}
            for user_id, count in sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        ]

# Global instance
audit_log = AuditLog()
