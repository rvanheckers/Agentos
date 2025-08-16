#!/usr/bin/env python3
"""
Enterprise Database Pool Manager - 0.1% Expert Implementation
=============================================================

Netflix/Google/Uber pattern: Single application-wide connection pool
with request-scoped sessions and smart resource management.

Key Principles:
1. ONE connection pool for entire application
2. Context-managed sessions (auto-cleanup)
3. Connection health monitoring
4. Graceful degradation under load
5. Metrics-driven pool sizing
"""

import logging
import threading
import time
from typing import Dict, Any
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
import os

logger = logging.getLogger(__name__)

class DatabasePoolManager:
    """
    Enterprise-grade database pool manager.
    
    Features:
    - Single application-wide pool (Netflix pattern)  
    - Environment-aware sizing (dev vs prod)
    - Connection health monitoring
    - Graceful failure handling
    - Performance metrics
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern - only one pool per application"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.database_url = self._get_database_url()
        self.engine = None
        self.SessionLocal = None
        self.session_factory = None
        self.pool_stats = {
            'created_sessions': 0,
            'closed_sessions': 0,
            'failed_connections': 0,
            'last_health_check': 0
        }
        
        self._initialize_pool()
        self._initialized = True
        
        logger.info("✅ Enterprise Database Pool initialized (Singleton)")
    
    def _get_database_url(self) -> str:
        """Get database URL with environment-specific defaults"""
        return os.getenv(
            'DATABASE_URL', 
            "postgresql://agentos_user:secure_agentos_2024@localhost:5432/agentos_production"
        )
    
    def _get_pool_config(self) -> Dict[str, Any]:
        """Environment-aware pool configuration"""
        env = os.getenv('ENV', 'development').lower()
        
        if env in ['production', 'prod']:
            # Production: Handle high traffic
            return {
                'pool_size': 20,           # Base connections
                'max_overflow': 30,        # Burst capacity  
                'pool_pre_ping': True,     # Connection validation
                'pool_recycle': 3600,      # 1 hour recycle
                'pool_timeout': 30,        # 30s acquisition timeout
                'pool_reset_on_return': 'commit'
            }
        elif env in ['staging', 'test']:
            # Staging: Moderate load
            return {
                'pool_size': 10,
                'max_overflow': 15,
                'pool_pre_ping': True,
                'pool_recycle': 1800,      # 30 min recycle
                'pool_timeout': 20,
                'pool_reset_on_return': 'commit'
            }
        else:
            # Development: Conservative (prevents crashes)
            return {
                'pool_size': 3,            # Minimal base
                'max_overflow': 7,         # Small burst
                'pool_pre_ping': True,
                'pool_recycle': 1800,
                'pool_timeout': 15,
                'pool_reset_on_return': 'commit'
            }
    
    def _initialize_pool(self):
        """Initialize the connection pool with expert configuration"""
        try:
            config = self._get_pool_config()
            
            self.engine = create_engine(
                self.database_url,
                poolclass=QueuePool,
                echo=False,  # Set to True for SQL debugging
                connect_args={
                    "application_name": f"AgentOS_{os.getenv('ENV', 'dev')}",
                    "options": "-c statement_timeout=30000"  # 30s query timeout
                },
                **config
            )
            
            # Test the pool
            self._health_check()
            
            # Create session factory with scoped sessions (thread-safe)
            self.SessionLocal = sessionmaker(bind=self.engine)
            self.session_factory = scoped_session(self.SessionLocal)
            
            total_capacity = config['pool_size'] + config['max_overflow']
            logger.info(f"🏊 Database pool ready: {config['pool_size']}+{config['max_overflow']} = {total_capacity} max connections")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize database pool: {e}")
            raise
    
    @contextmanager 
    def get_session(self):
        """
        Context manager for database sessions.
        
        Expert pattern:
        - Auto-commit on success
        - Auto-rollback on error  
        - Always cleanup connection
        - Track session lifecycle
        """
        session = self.session_factory()
        self.pool_stats['created_sessions'] += 1
        
        try:
            yield session
            session.commit()
            
        except Exception as e:
            session.rollback() 
            logger.error(f"Database session error: {e}")
            raise
            
        finally:
            session.close()
            self.pool_stats['closed_sessions'] += 1
            # Remove from scoped session registry
            self.session_factory.remove()
    
    def _health_check(self) -> bool:
        """Connection pool health check"""
        try:
            with self.engine.connect() as conn:
                start = time.time()
                result = conn.execute(text("SELECT 1"))
                response_time = (time.time() - start) * 1000
                
                if result.scalar() == 1:
                    self.pool_stats['last_health_check'] = time.time()
                    logger.debug(f"✅ Database health check OK ({response_time:.1f}ms)")
                    return True
                    
        except Exception as e:
            self.pool_stats['failed_connections'] += 1
            logger.error(f"❌ Database health check failed: {e}")
            return False
    
    def get_pool_metrics(self) -> Dict[str, Any]:
        """Get detailed pool metrics for monitoring"""
        try:
            pool = self.engine.pool
            config = self._get_pool_config()
            
            # Calculate usage percentage
            checked_out = pool.checkedout()
            total_capacity = config['pool_size'] + config['max_overflow']
            usage_pct = (checked_out / total_capacity) * 100
            
            return {
                "pool_size": pool.size(),
                "checked_out": checked_out,
                "checked_in": pool.checkedin(), 
                "overflow": pool.overflow(),
                "total_capacity": total_capacity,
                "usage_percentage": round(usage_pct, 1),
                "sessions_created": self.pool_stats['created_sessions'],
                "sessions_closed": self.pool_stats['closed_sessions'],
                "active_sessions": self.pool_stats['created_sessions'] - self.pool_stats['closed_sessions'],
                "failed_connections": self.pool_stats['failed_connections'],
                "last_health_check": self.pool_stats['last_health_check'],
                "environment": os.getenv('ENV', 'development')
            }
            
        except Exception as e:
            logger.error(f"Failed to get pool metrics: {e}")
            return {"error": str(e)}
    
    def log_high_usage_warning(self):
        """Log warning if pool usage is high"""
        try:
            metrics = self.get_pool_metrics()
            usage = metrics.get('usage_percentage', 0)
            
            if usage > 80:
                logger.warning(
                    f"⚠️ HIGH DATABASE POOL USAGE: {usage}% "
                    f"({metrics['checked_out']}/{metrics['total_capacity']} connections)"
                )
                return True
            return False
            
        except Exception:
            return False
    
    def emergency_cleanup(self):
        """Emergency pool cleanup if resources are exhausted"""
        try:
            logger.warning("🚨 Emergency database pool cleanup initiated")
            
            # Remove all scoped sessions
            self.session_factory.remove()
            
            # Force pool refresh
            self.engine.pool.recreate()
            
            logger.info("✅ Emergency cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Emergency cleanup failed: {e}")
    
    def shutdown(self):
        """Graceful shutdown of connection pool"""
        try:
            if self.session_factory:
                self.session_factory.remove()
                
            if self.engine:
                metrics = self.get_pool_metrics()
                logger.info(f"📊 Final pool stats: {metrics}")
                
                self.engine.dispose()
                logger.info("📪 Database pool shutdown complete")
                
        except Exception as e:
            logger.error(f"Error during pool shutdown: {e}")

# Global singleton instance
db_pool = DatabasePoolManager()

# Convenience function for services
def get_db_session():
    """Get database session context manager"""
    return db_pool.get_session()

def get_pool_metrics():
    """Get current pool metrics"""
    return db_pool.get_pool_metrics()

def check_pool_health():
    """Check if pool usage is getting high"""
    return db_pool.log_high_usage_warning()
