"""
Central Shutdown Manager for AgentOS

Provides centralized shutdown handling for services that require explicit cleanup,
particularly AgentsService instances that need database connection cleanup.

Features:
- Automatic atexit registration
- Signal handler integration
- Context manager support
- Thread-safe operations
- Graceful error handling during shutdown
"""

import atexit
import logging
import threading
import weakref
from typing import List, Callable, Any, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class ShutdownManager:
    """
    Central manager for service shutdown coordination.
    
    This class provides multiple patterns for ensuring services are properly
    shut down, particularly important for services with database connections
    or other resources that need explicit cleanup.
    """
    
    _instance: Optional['ShutdownManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'ShutdownManager':
        """Singleton pattern to ensure one shutdown manager per process."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the shutdown manager."""
        if getattr(self, '_initialized', False):
            return
            
        self._shutdown_callbacks: List[Callable[[], None]] = []
        self._services: List[Any] = []
        self._shutdown_called = False
        self._lock = threading.Lock()
        
        # Register atexit handler
        atexit.register(self._atexit_handler)
        
        self._initialized = True
        logger.debug("ShutdownManager initialized")
    
    def register_service(self, service: Any, shutdown_method: str = 'shutdown') -> None:
        """
        Register a service instance for shutdown.
        
        Args:
            service: Service instance that needs cleanup
            shutdown_method: Name of the shutdown method to call (default: 'shutdown')
        """
        with self._lock:
            if hasattr(service, shutdown_method):
                # Use weak reference to avoid circular references
                weak_service = weakref.ref(service)
                
                def shutdown_callback():
                    svc = weak_service()
                    if svc is not None:
                        try:
                            getattr(svc, shutdown_method)()
                            logger.debug(f"Successfully shut down {type(svc).__name__}")
                        except Exception as e:
                            logger.error(f"Error shutting down {type(svc).__name__}: {e}")
                
                self._shutdown_callbacks.append(shutdown_callback)
                self._services.append(weak_service)
                logger.debug(f"Registered {type(service).__name__} for shutdown")
            else:
                logger.warning(f"Service {type(service).__name__} does not have method '{shutdown_method}'")
    
    def register_callback(self, callback: Callable[[], None]) -> None:
        """
        Register a custom shutdown callback.
        
        Args:
            callback: Function to call during shutdown
        """
        with self._lock:
            self._shutdown_callbacks.append(callback)
            logger.debug("Registered custom shutdown callback")
    
    def shutdown(self) -> None:
        """
        Execute all registered shutdown callbacks.
        
        This method is idempotent - calling it multiple times is safe.
        """
        with self._lock:
            if self._shutdown_called:
                logger.debug("Shutdown already called, skipping")
                return
            
            self._shutdown_called = True
            logger.info(f"Executing shutdown for {len(self._shutdown_callbacks)} registered callbacks")
        
        # Execute callbacks in reverse order (LIFO - last registered, first shut down)
        for i, callback in enumerate(reversed(self._shutdown_callbacks)):
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in shutdown callback {i}: {e}")
        
        logger.info("Shutdown completed")
    
    def _atexit_handler(self) -> None:
        """Atexit handler to ensure cleanup on process exit."""
        logger.debug("Atexit handler called")
        self.shutdown()
    
    @contextmanager
    def managed_service(self, service_class, *args, **kwargs):
        """
        Context manager for automatic service lifecycle management.
        
        Args:
            service_class: Class to instantiate
            *args, **kwargs: Arguments to pass to service constructor
            
        Example:
            with shutdown_manager.managed_service(AgentsService) as agents:
                agents.do_something()
        """
        service = service_class(*args, **kwargs)
        self.register_service(service)
        try:
            yield service
        finally:
            # Service will be cleaned up by shutdown manager
            pass
    
    def clear(self) -> None:
        """Clear all registered callbacks (for testing purposes)."""
        with self._lock:
            self._shutdown_callbacks.clear()
            self._services.clear()
            self._shutdown_called = False
            logger.debug("ShutdownManager cleared")


# Global instance
shutdown_manager = ShutdownManager()

# Convenience functions
def register_service(service: Any, shutdown_method: str = 'shutdown') -> None:
    """Register a service for shutdown. Convenience wrapper."""
    shutdown_manager.register_service(service, shutdown_method)

def register_callback(callback: Callable[[], None]) -> None:
    """Register a shutdown callback. Convenience wrapper."""
    shutdown_manager.register_callback(callback)

def managed_service(service_class, *args, **kwargs):
    """Context manager for service lifecycle. Convenience wrapper."""
    return shutdown_manager.managed_service(service_class, *args, **kwargs)

def shutdown():
    """Execute shutdown. Convenience wrapper."""
    shutdown_manager.shutdown()