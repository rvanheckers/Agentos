"""
System Event Logger for AgentOS

Provides centralized system event logging using the shared database pool.
Replaces the old session.log_system_event pattern with a proper service.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import uuid
from sqlalchemy import text

logger = logging.getLogger(__name__)

class SystemEventLogger:
    """Centralized system event logger using shared database pool"""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern for system event logger"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize system event logger"""
        if self._initialized:
            return
            
        try:
            from core.database_pool import get_db_session
            self.get_db_session = get_db_session
            self._initialized = True
            logger.debug("SystemEventLogger initialized with database pool")
        except ImportError:
            logger.error("Failed to import database pool")
            self.get_db_session = None
            self._initialized = False
    
    def log_event(self, 
                  event_type: str,
                  message: str,
                  severity: str = 'info',
                  component: Optional[str] = None,
                  metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Log a system event to the database
        
        Args:
            event_type: Type of event (e.g., 'upload_started', 'job_created')
            message: Human-readable event message
            severity: Event severity ('debug', 'info', 'warning', 'error', 'critical')
            component: Component that generated the event
            metadata: Additional event metadata
            
        Returns:
            bool: True if event was logged successfully, False otherwise
        """
        if not self.get_db_session:
            # Fallback to regular logging when database is not available
            log_level = getattr(logging, severity.upper(), logging.INFO)
            logger.log(log_level, f"[{component or 'system'}] {event_type}: {message}")
            return False
            
        try:
            with self.get_db_session() as session:
                # Try different table/column combinations for compatibility
                try:
                    # Try with metadata column first
                    session.execute(
                        text("""
                            INSERT INTO system_events 
                            (id, event_type, message, severity, component, metadata, created_at)
                            VALUES (:id, :event_type, :message, :severity, :component, :metadata, :created_at)
                        """),
                        {
                            'id': str(uuid.uuid4()),
                            'event_type': event_type,
                            'message': message,
                            'severity': severity,
                            'component': component,
                            'metadata': str(metadata) if metadata else None,
                            'created_at': datetime.now(timezone.utc)
                        }
                    )
                except Exception:
                    # Fallback: try without metadata column
                    session.execute(
                        text("""
                            INSERT INTO system_events 
                            (id, event_type, message, severity, component, created_at)
                            VALUES (:id, :event_type, :message, :severity, :component, :created_at)
                        """),
                        {
                            'id': str(uuid.uuid4()),
                            'event_type': event_type,
                            'message': message,
                            'severity': severity,
                            'component': component,
                            'created_at': datetime.now(timezone.utc)
                        }
                    )
                
                session.commit()
                logger.debug(f"System event logged: {event_type} - {message}")
                return True
                
        except Exception as e:
            # Graceful fallback to regular logging
            log_level = getattr(logging, severity.upper(), logging.INFO)
            logger.log(log_level, f"[{component or 'system'}] {event_type}: {message} (DB log failed: {e})")
            return False
    
    def log_upload_event(self, upload_id: str, status: str, message: str, **kwargs):
        """Convenience method for upload events"""
        return self.log_event(
            event_type='upload',
            message=f"Upload {upload_id}: {message}",
            severity='info',
            component='upload_service',
            metadata={'upload_id': upload_id, 'status': status, **kwargs}
        )
    
    def log_job_event(self, job_id: str, status: str, message: str, **kwargs):
        """Convenience method for job events"""
        return self.log_event(
            event_type='job',
            message=f"Job {job_id}: {message}",
            severity='info',
            component='job_service',
            metadata={'job_id': job_id, 'status': status, **kwargs}
        )
    
    def log_error(self, component: str, error: str, **kwargs):
        """Convenience method for error events"""
        return self.log_event(
            event_type='error',
            message=error,
            severity='error',
            component=component,
            metadata=kwargs
        )

# Global instance
system_event_logger = SystemEventLogger()

# Convenience functions
def log_system_event(event_type: str, message: str, **kwargs):
    """Global function to log system events"""
    return system_event_logger.log_event(event_type, message, **kwargs)

def log_upload_event(upload_id: str, status: str, message: str, **kwargs):
    """Global function to log upload events"""
    return system_event_logger.log_upload_event(upload_id, status, message, **kwargs)

def log_job_event(job_id: str, status: str, message: str, **kwargs):
    """Global function to log job events"""
    return system_event_logger.log_job_event(job_id, status, message, **kwargs)

def log_error(component: str, error: str, **kwargs):
    """Global function to log error events"""
    return system_event_logger.log_error(component, error, **kwargs)