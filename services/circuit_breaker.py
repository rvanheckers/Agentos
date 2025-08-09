"""
Circuit Breaker Service
Prevents cascade failures by temporarily disabling failing operations
"""

import time
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from contextlib import contextmanager
import redis
import logging

logger = logging.getLogger("agentos.circuit_breaker")

class CircuitState(str, Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit tripped, failing fast
    HALF_OPEN = "half_open"  # Testing if service recovered

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5        # Number of failures to trip circuit
    success_threshold: int = 3        # Number of successes to close circuit in half-open
    timeout_seconds: int = 60         # How long to stay open before trying half-open
    window_seconds: int = 300         # Time window for failure counting
    expected_exception_types: tuple = (Exception,)  # Exception types that count as failures

@dataclass
class CircuitBreakerState:
    """Current state of circuit breaker"""
    state: CircuitState
    failure_count: int
    success_count: int
    last_failure_time: float
    last_success_time: float
    state_changed_time: float
    total_requests: int
    total_failures: int
    total_successes: int

class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass

class CircuitBreaker:
    """
    Circuit breaker implementation with Redis storage for distributed systems

    Features:
    - Fail-fast when service is down
    - Automatic recovery testing
    - Configurable thresholds and timeouts
    - Metrics collection
    - Distributed state via Redis
    """

    # Global Redis client for all circuit breakers
    _redis_client = None

    @classmethod
    def get_redis_client(cls):
        """Get shared Redis client"""
        if cls._redis_client is None:
            cls._redis_client = redis.from_url("redis://localhost:6379/3")
        return cls._redis_client

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """
        Initialize circuit breaker

        Args:
            name: Unique name for this circuit breaker
            config: Configuration object
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.redis_client = self.get_redis_client()
        self.key = f"circuit_breaker:{name}"

        # Initialize state if not exists
        self._initialize_state()

    def _initialize_state(self):
        """Initialize circuit breaker state if not exists"""
        if not self.redis_client.exists(self.key):
            initial_state = CircuitBreakerState(
                state=CircuitState.CLOSED,
                failure_count=0,
                success_count=0,
                last_failure_time=0.0,
                last_success_time=0.0,
                state_changed_time=time.time(),
                total_requests=0,
                total_failures=0,
                total_successes=0
            )
            self._save_state(initial_state)

    def _load_state(self) -> CircuitBreakerState:
        """Load current state from Redis"""
        try:
            data = self.redis_client.get(self.key)
            if data:
                state_dict = json.loads(data)
                # Convert string back to enum
                state_dict['state'] = CircuitState(state_dict['state'])
                return CircuitBreakerState(**state_dict)
            else:
                # State was deleted, reinitialize
                self._initialize_state()
                return self._load_state()
        except Exception as e:
            logger.error(f"Error loading circuit breaker state: {e}")
            # Return default state on error
            return CircuitBreakerState(
                state=CircuitState.CLOSED,
                failure_count=0,
                success_count=0,
                last_failure_time=0.0,
                last_success_time=0.0,
                state_changed_time=time.time(),
                total_requests=0,
                total_failures=0,
                total_successes=0
            )

    def _save_state(self, state: CircuitBreakerState):
        """Save state to Redis"""
        try:
            state_dict = asdict(state)
            # Convert enum to string for JSON serialization
            state_dict['state'] = state.state.value

            self.redis_client.setex(
                self.key,
                3600,  # 1 hour expiry
                json.dumps(state_dict)
            )
        except Exception as e:
            logger.error(f"Error saving circuit breaker state: {e}")

    def _should_trip(self, state: CircuitBreakerState) -> bool:
        """Check if circuit should trip to open state"""
        if state.state != CircuitState.CLOSED:
            return False

        # Check failure threshold
        if state.failure_count >= self.config.failure_threshold:
            return True

        return False

    def _should_attempt_reset(self, state: CircuitBreakerState) -> bool:
        """Check if we should attempt to reset (move to half-open)"""
        if state.state != CircuitState.OPEN:
            return False

        # Check timeout
        now = time.time()
        time_since_trip = now - state.state_changed_time

        return time_since_trip >= self.config.timeout_seconds

    def _should_reset(self, state: CircuitBreakerState) -> bool:
        """Check if circuit should reset to closed state"""
        if state.state != CircuitState.HALF_OPEN:
            return False

        return state.success_count >= self.config.success_threshold

    def _clean_old_failures(self, state: CircuitBreakerState) -> CircuitBreakerState:
        """Clean old failures outside the time window"""
        now = time.time()

        # If last failure was outside window, reset failure count
        if (state.last_failure_time > 0 and
            now - state.last_failure_time > self.config.window_seconds):
            state.failure_count = 0

        return state

    @contextmanager
    def __call__(self):
        """Context manager for circuit breaker usage"""
        state = self._load_state()
        state = self._clean_old_failures(state)
        now = time.time()

        # Increment total requests
        state.total_requests += 1

        # Check if we should attempt reset
        if self._should_attempt_reset(state):
            state.state = CircuitState.HALF_OPEN
            state.state_changed_time = now
            state.success_count = 0
            logger.info(f"Circuit breaker {self.name} moved to HALF_OPEN")

        # Fail fast if circuit is open
        if state.state == CircuitState.OPEN:
            logger.info(f"Circuit breaker {self.name} is OPEN, failing fast")
            self._save_state(state)
            raise CircuitBreakerError(f"Circuit breaker {self.name} is open")

        # Allow limited requests in half-open state
        if state.state == CircuitState.HALF_OPEN and state.success_count >= 1:
            logger.info(f"Circuit breaker {self.name} limiting requests in HALF_OPEN")
            self._save_state(state)
            raise CircuitBreakerError(f"Circuit breaker {self.name} is half-open and limiting requests")

        # Execute the protected operation
        try:
            yield

            # Success - update state
            state.success_count += 1
            state.total_successes += 1
            state.last_success_time = now

            # Check if we should reset to closed
            if self._should_reset(state):
                state.state = CircuitState.CLOSED
                state.state_changed_time = now
                state.failure_count = 0
                state.success_count = 0
                logger.info(f"Circuit breaker {self.name} RESET to CLOSED")

            self._save_state(state)

        except self.config.expected_exception_types:
            # Failure - update state
            state.failure_count += 1
            state.total_failures += 1
            state.last_failure_time = now

            # Reset success count in half-open state
            if state.state == CircuitState.HALF_OPEN:
                state.success_count = 0

            # Check if we should trip
            if self._should_trip(state):
                state.state = CircuitState.OPEN
                state.state_changed_time = now
                logger.warning(f"Circuit breaker {self.name} TRIPPED to OPEN after {state.failure_count} failures")

            self._save_state(state)

            # Re-raise the exception
            raise

    @property
    def is_open(self) -> bool:
        """Check if circuit breaker is open"""
        state = self._load_state()
        return state.state == CircuitState.OPEN

    @property
    def is_closed(self) -> bool:
        """Check if circuit breaker is closed"""
        state = self._load_state()
        return state.state == CircuitState.CLOSED

    @property
    def is_half_open(self) -> bool:
        """Check if circuit breaker is half-open"""
        state = self._load_state()
        return state.state == CircuitState.HALF_OPEN

    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
        state = self._load_state()
        now = time.time()

        return {
            "name": self.name,
            "state": state.state.value,
            "failure_count": state.failure_count,
            "success_count": state.success_count,
            "total_requests": state.total_requests,
            "total_failures": state.total_failures,
            "total_successes": state.total_successes,
            "failure_rate": (
                state.total_failures / state.total_requests
                if state.total_requests > 0 else 0.0
            ),
            "last_failure_time": state.last_failure_time,
            "last_success_time": state.last_success_time,
            "state_changed_time": state.state_changed_time,
            "time_in_current_state": now - state.state_changed_time,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "timeout_seconds": self.config.timeout_seconds,
                "window_seconds": self.config.window_seconds
            }
        }

    def reset(self) -> bool:
        """Force reset circuit breaker to closed state"""
        try:
            now = time.time()
            reset_state = CircuitBreakerState(
                state=CircuitState.CLOSED,
                failure_count=0,
                success_count=0,
                last_failure_time=0.0,
                last_success_time=0.0,
                state_changed_time=now,
                total_requests=0,
                total_failures=0,
                total_successes=0
            )
            self._save_state(reset_state)

            logger.info(f"Circuit breaker {self.name} manually reset")
            return True

        except Exception as e:
            logger.error(f"Error resetting circuit breaker {self.name}: {e}")
            return False

    def trip(self) -> bool:
        """Force trip circuit breaker to open state"""
        try:
            state = self._load_state()
            state.state = CircuitState.OPEN
            state.state_changed_time = time.time()
            self._save_state(state)

            logger.warning(f"Circuit breaker {self.name} manually tripped")
            return True

        except Exception as e:
            logger.error(f"Error tripping circuit breaker {self.name}: {e}")
            return False

class CircuitBreakerManager:
    """
    Manager for all circuit breakers in the system
    """

    _instances: Dict[str, CircuitBreaker] = {}

    @classmethod
    def get_circuit_breaker(
        cls,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """
        Get or create circuit breaker instance

        Args:
            name: Circuit breaker name
            config: Optional configuration

        Returns:
            CircuitBreaker instance
        """
        if name not in cls._instances:
            cls._instances[name] = CircuitBreaker(name, config)
        return cls._instances[name]

    @classmethod
    def get_all_states(cls) -> Dict[str, Any]:
        """Get states of all circuit breakers"""
        return {
            name: breaker.get_state()
            for name, breaker in cls._instances.items()
        }

    @classmethod
    def reset_all(cls) -> Dict[str, bool]:
        """Reset all circuit breakers"""
        return {
            name: breaker.reset()
            for name, breaker in cls._instances.items()
        }

# Convenience function for creating circuit breakers
def create_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    success_threshold: int = 3,
    timeout_seconds: int = 60,
    window_seconds: int = 300
) -> CircuitBreaker:
    """
    Create circuit breaker with custom configuration

    Args:
        name: Circuit breaker name
        failure_threshold: Number of failures to trip
        success_threshold: Number of successes to reset
        timeout_seconds: How long to stay open
        window_seconds: Time window for counting failures

    Returns:
        CircuitBreaker instance
    """
    config = CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        success_threshold=success_threshold,
        timeout_seconds=timeout_seconds,
        window_seconds=window_seconds
    )

    return CircuitBreakerManager.get_circuit_breaker(name, config)

# Export commonly used items
__all__ = [
    "CircuitBreaker",
    "CircuitBreakerManager",
    "CircuitBreakerConfig",
    "CircuitBreakerError",
    "create_circuit_breaker"
]
