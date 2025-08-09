# Deze file bevat de PostgreSQL manager voor AgentOS
# Verplaatst van database/postgresql_manager.py naar root

"""
PostgreSQL Database Manager voor AgentOS
========================================

Complete database manager met connection pooling, SQLAlchemy ORM,
en optimalisaties voor high-concurrency video processing.

Features:
- Connection pooling (20 base + 30 overflow)
- Automatic reconnection
- Thread-safe operations
- Performance logging
- Error handling
"""

from typing import Dict, Any
from datetime import datetime, timezone, timedelta
import uuid
import logging
import contextlib
from sqlalchemy import create_engine, text, Column, String, DateTime, Integer, Text, Boolean, Float, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.pool import QueuePool
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID

# Logging
logger = logging.getLogger(__name__)

# SQLAlchemy Base
Base = declarative_base()

# Database Models
class Job(Base):
    __tablename__ = 'jobs'

    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(36), nullable=False, index=True)
    video_url = Column(Text, nullable=False)
    video_title = Column(String(500), nullable=True)  # Add missing video_title column
    status = Column(String(20), default='pending', index=True)
    progress = Column(Integer, default=0)
    current_step = Column(String(100), nullable=True)  # Add missing current_step column
    error_message = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    result_data = Column(Text)
    priority = Column(Integer, default=5, index=True)
    retry_count = Column(Integer, default=0)
    worker_id = Column(String(50))

    # Relationships
    clips = relationship("Clip", back_populates="job", cascade="all, delete-orphan")
    processing_steps = relationship("ProcessingStep", back_populates="job", cascade="all, delete-orphan")

class Clip(Base):
    __tablename__ = 'clips'

    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey('jobs.id'), nullable=False, index=True)
    clip_number = Column(Integer, nullable=False, default=1)  # Add missing clip_number column
    file_path = Column(Text, nullable=False)
    duration = Column(Float)
    title = Column(String(255))
    description = Column(Text)
    tags = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    file_size = Column(Integer)
    thumbnail_path = Column(Text)

    # Relationships
    job = relationship("Job", back_populates="clips")

class ProcessingStep(Base):
    __tablename__ = 'processing_steps'

    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey('jobs.id'), nullable=False, index=True)
    step_name = Column(String(100), nullable=False)
    status = Column(String(20), default='pending')
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)
    agent_output = Column(Text)
    error_message = Column(Text)
    metadata_json = Column(Text)

    # Relationships
    job = relationship("Job", back_populates="processing_steps")

class SystemEvent(Base):
    __tablename__ = 'system_events'

    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False, index=True)
    message = Column(Text)
    severity = Column(String(20), default='info', index=True)
    component = Column(String(50), index=True)
    metadata_json = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

class SystemConfig(Base):
    __tablename__ = 'system_config'

    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text)
    description = Column(Text)
    is_editable = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_by = Column(String(36))

class PostgreSQLManager:
    """
    PostgreSQL Database Manager met connection pooling en high-performance features
    """

    def __init__(self, database_url: str = None):
        self.database_url = database_url or "postgresql://agentos_user:secure_agentos_2024@localhost:5432/agentos_production"
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()
        logger.info("✅ PostgreSQL Manager initialized with connection pooling")

    def _initialize_engine(self):
        """Initialize SQLAlchemy engine with connection pooling"""
        try:
            self.engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                pool_size=50,           # Increased for concurrency (was 20)
                max_overflow=100,       # Higher burst capacity (was 30)
                pool_pre_ping=True,     # Validate connections
                pool_recycle=1800,      # Faster refresh - 30min (was 1 hour)
                pool_timeout=30,        # Connection acquisition timeout
                pool_reset_on_return='commit',  # Clean connection state
                echo=False,             # Set to True for SQL debugging
                # Performance optimizations voor concurrent access
                connect_args={
                    "application_name": "AgentOS_AdminUI"
                }
            )

            # Test connection
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                logger.info(f"✅ PostgreSQL connection test successful: {result.scalar()}")

            # Create session factory
            self.SessionLocal = sessionmaker(bind=self.engine)

        except Exception as e:
            logger.error(f"❌ Failed to initialize PostgreSQL engine: {e}")
            raise

    @contextlib.contextmanager
    def get_session(self):
        """Context manager for database sessions"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def update_job_status(self, job_id: str, status: str, progress: int = None, error_message: str = None):
        """Update job status in database"""
        try:
            with self.get_session() as session:
                job = session.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.status = status
                    if progress is not None:
                        job.progress = progress
                    if error_message:
                        job.error_message = error_message
                    if status == 'processing' and not job.started_at:
                        job.started_at = datetime.now(timezone.utc)
                    elif status == 'completed':
                        job.completed_at = datetime.now(timezone.utc)

                    session.commit()
                    logger.info(f"✅ Job {job_id} updated: {status} ({progress}%)")
                else:
                    logger.warning(f"⚠️ Job {job_id} not found for status update")
        except Exception as e:
            logger.error(f"❌ Failed to update job status: {e}")

    def save_clip(self, job_id: str, file_path: str, duration: float = None, title: str = None, description: str = None):
        """Save clip to database"""
        try:
            with self.get_session() as session:
                clip = Clip(
                    job_id=job_id,
                    file_path=file_path,
                    duration=duration,
                    title=title,
                    description=description
                )
                session.add(clip)
                session.commit()
                logger.info(f"✅ Clip saved for job {job_id}: {file_path}")
                return str(clip.id)
        except Exception as e:
            logger.error(f"❌ Failed to save clip: {e}")
            return None

    def log_system_event(self, event_type: str, message: str, severity: str = 'info', component: str = None, metadata: dict = None):
        """Log system event to database"""
        try:
            with self.get_session() as session:
                event = SystemEvent(
                    event_type=event_type,
                    message=message,
                    severity=severity,
                    component=component,
                    metadata=str(metadata) if metadata else None
                )
                session.add(event)
                session.commit()
                logger.info(f"📝 System event logged: {event_type}")
        except Exception as e:
            logger.error(f"❌ Failed to log system event: {e}")

    def get_job_by_id(self, job_id: str):
        """Get job by ID"""
        try:
            with self.get_session() as session:
                job = session.query(Job).filter(Job.id == job_id).first()
                return job
        except Exception as e:
            logger.error(f"❌ Failed to get job {job_id}: {e}")
            return None

    def create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("✅ Database tables created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {e}")
            raise

    def get_recent_clips(self, limit: int = 10):
        """Get recent clips for dashboard"""
        try:
            with self.get_session() as session:
                clips = session.query(Clip)\
                              .order_by(Clip.created_at.desc())\
                              .limit(limit)\
                              .all()

                result = []
                for clip in clips:
                    result.append({
                        "id": str(clip.id),
                        "job_id": str(clip.job_id),
                        "clip_number": clip.clip_number,
                        "file_path": clip.file_path,
                        "title": clip.title,
                        "duration": clip.duration,
                        "created_at": clip.created_at.isoformat() if clip.created_at else None
                    })

                return result
        except Exception as e:
            logger.error(f"❌ Failed to get recent clips: {e}")
            return []

    def get_stats(self):
        """Get database statistics for admin dashboard"""
        try:
            with self.get_session() as session:
                # Get table counts
                total_jobs = session.query(Job).count()
                total_clips = session.query(Clip).count()
                total_processing_steps = session.query(ProcessingStep).count()
                total_system_events = session.query(SystemEvent).count()

                # Get status counts
                pending_jobs = session.query(Job).filter(Job.status == 'pending').count()
                processing_jobs = session.query(Job).filter(Job.status == 'processing').count()
                completed_jobs = session.query(Job).filter(Job.status == 'completed').count()
                failed_jobs = session.query(Job).filter(Job.status == 'failed').count()

                # Get recent activity (last 24 hours)
                yesterday = datetime.now(timezone.utc) - timedelta(days=1)
                recent_jobs = session.query(Job).filter(Job.created_at >= yesterday).count()
                recent_clips = session.query(Clip).filter(Clip.created_at >= yesterday).count()
                recent_events = session.query(SystemEvent).filter(SystemEvent.created_at >= yesterday).count()

                # Calculate success rate (last 100 jobs)
                last_100_jobs = session.query(Job).order_by(Job.created_at.desc()).limit(100).all()
                success_rate = 0
                if last_100_jobs:
                    completed_count = sum(1 for job in last_100_jobs if job.status == 'completed')
                    success_rate = (completed_count / len(last_100_jobs)) * 100

                return {
                    "total_jobs": total_jobs,
                    "total_clips": total_clips,
                    "total_processing_steps": total_processing_steps,
                    "total_system_events": total_system_events,
                    "pending_jobs": pending_jobs,
                    "processing_jobs": processing_jobs,
                    "completed_jobs": completed_jobs,
                    "failed_jobs": failed_jobs,
                    "recent_jobs_24h": recent_jobs,
                    "recent_clips_24h": recent_clips,
                    "recent_events_24h": recent_events,
                    "success_rate": round(success_rate, 1),
                    "connection_pool_size": self.engine.pool.size() if hasattr(self.engine.pool, 'size') else 50,
                    "connection_pool_checked_out": self.engine.pool.checkedout() if hasattr(self.engine.pool, 'checkedout') else 0,
                    "connection_pool_overflow": self.engine.pool.overflow() if hasattr(self.engine.pool, 'overflow') else 0,
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }
        except Exception as e:
            logger.error(f"❌ Failed to get database stats: {e}")
            return {
                "total_jobs": 0,
                "total_clips": 0,
                "total_processing_steps": 0,
                "total_system_events": 0,
                "pending_jobs": 0,
                "processing_jobs": 0,
                "completed_jobs": 0,
                "failed_jobs": 0,
                "recent_jobs_24h": 0,
                "recent_clips_24h": 0,
                "recent_events_24h": 0,
                "success_rate": 0,
                "connection_pool_size": 0,
                "connection_pool_checked_out": 0,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }

    def get_combined_recent_activity(self, limit: int = 20):
        """Get combined recent activity from system events, jobs, and processing steps"""
        try:
            with self.get_session() as session:
                activities = []

                # Get recent system events
                recent_events = session.query(SystemEvent)\
                                     .order_by(SystemEvent.created_at.desc())\
                                     .limit(limit//2)\
                                     .all()

                for event in recent_events:
                    activities.append({
                        "id": str(event.id),
                        "type": "system_event",
                        "event_type": event.event_type,
                        "message": event.message,
                        "severity": event.severity,
                        "component": event.component,
                        "timestamp": event.created_at.isoformat() if event.created_at else None,
                        "metadata": event.metadata_json
                    })

                # Get recent job completions
                recent_jobs = session.query(Job)\
                                   .filter(Job.status.in_(['completed', 'failed']))\
                                   .order_by(Job.completed_at.desc())\
                                   .limit(limit//2)\
                                   .all()

                for job in recent_jobs:
                    activities.append({
                        "id": str(job.id),
                        "type": "job_completion",
                        "event_type": "job_completed" if job.status == 'completed' else "job_failed",
                        "message": f"Job {str(job.id)[:8]} {job.status}",
                        "severity": "info" if job.status == 'completed' else "error",
                        "component": "job_processor",
                        "timestamp": (job.completed_at or job.created_at).isoformat() if (job.completed_at or job.created_at) else None,
                        "metadata": f'{{"video_title": "{job.video_title or "Unknown"}", "progress": {job.progress}}}'
                    })

                # Sort all activities by timestamp (most recent first)
                activities.sort(key=lambda x: x['timestamp'] or '', reverse=True)

                # Limit to requested count
                return activities[:limit]

        except Exception as e:
            logger.error(f"❌ Failed to get combined recent activity: {e}")
            return []

    def get_database_health(self) -> Dict[str, Any]:
        """
        Get database health metrics for system monitoring
        Returns connection count, query performance, etc.
        """
        try:
            with self.engine.connect() as connection:
                # Get connection count
                result = connection.execute(text("""
                    SELECT count(*) as active_connections
                    FROM pg_stat_activity
                    WHERE state = 'active'
                """))
                active_connections = result.fetchone()[0]

                # Get database size
                result = connection.execute(text("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as db_size
                """))
                db_size = result.fetchone()[0]

                # Basic performance test
                start_time = datetime.now()
                connection.execute(text("SELECT 1"))
                query_time = (datetime.now() - start_time).total_seconds() * 1000

                return {
                    "status": "healthy",
                    "connections": active_connections,
                    "database_size": db_size,
                    "query_response_ms": round(query_time, 2),
                    "pool_size": self.engine.pool.size(),
                    "pool_checked_out": self.engine.pool.checkedout(),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def close(self):
        """Close database connections"""
        if self.engine:
            self.engine.dispose()
            logger.info("📪 PostgreSQL connections closed")
