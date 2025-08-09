"""
Rate Limiter Service
Token bucket and sliding window rate limiting
"""

import time
import json
from typing import Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum
import redis
import logging

logger = logging.getLogger("agentos.rate_limiter")

class LimitType(str, Enum):
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"

@dataclass
class RateLimit:
    """Rate limit configuration"""
    requests: int  # Number of requests allowed
    window: int    # Time window in seconds
    limit_type: LimitType = LimitType.SLIDING_WINDOW
    burst_multiplier: float = 1.5  # Allow bursts up to this multiplier

@dataclass
class RateLimitState:
    """Current state of rate limit"""
    current_requests: int
    window_start: float
    tokens: float  # For token bucket
    last_refill: float  # For token bucket

class RateLimiter:
    """
    Enterprise rate limiter with multiple algorithms

    Features:
    - Token bucket for burst handling
    - Sliding window for smooth limiting
    - Fixed window for simple limiting
    - Per-user, per-action limits
    - Redis-backed for distributed systems
    - Detailed metrics and monitoring
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/2"):
        """
        Initialize rate limiter

        Args:
            redis_url: Redis connection URL
        """
        self.redis_client = redis.from_url(redis_url)
        self.key_prefix = "rate_limit:"

    def _get_key(self, user_id: str, action: str) -> str:
        """Generate Redis key for rate limit"""
        return f"{self.key_prefix}{user_id}:{action}"

    async def check(
        self,
        user_id: str,
        action: str,
        requests: int = 100,
        window: int = 60,
        limit_type: LimitType = LimitType.SLIDING_WINDOW,
        **kwargs
    ) -> bool:
        """
        Check if request is within rate limit

        Args:
            user_id: User identifier
            action: Action being rate limited
            requests: Number of requests allowed
            window: Time window in seconds
            limit_type: Type of rate limiting algorithm

        Returns:
            True if within limit, False if exceeded
        """
        try:
            rate_limit = RateLimit(
                requests=requests,
                window=window,
                limit_type=limit_type,
                burst_multiplier=kwargs.get('burst_multiplier', 1.5)
            )

            key = self._get_key(user_id, action)

            if limit_type == LimitType.TOKEN_BUCKET:
                return await self._check_token_bucket(key, rate_limit)
            elif limit_type == LimitType.SLIDING_WINDOW:
                return await self._check_sliding_window(key, rate_limit)
            elif limit_type == LimitType.FIXED_WINDOW:
                return await self._check_fixed_window(key, rate_limit)
            else:
                logger.error(f"Unknown rate limit type: {limit_type}")
                return False

        except redis.RedisError as e:
            logger.error(f"Redis error in rate limiter: {e}")
            # Fail open - allow request if Redis is down
            return True
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # Fail open
            return True

    async def _check_token_bucket(self, key: str, rate_limit: RateLimit) -> bool:
        """
        Token bucket algorithm - good for allowing bursts

        Args:
            key: Redis key
            rate_limit: Rate limit configuration

        Returns:
            True if request allowed
        """
        now = time.time()

        # Get current state
        state_data = self.redis_client.get(key)

        if state_data:
            state = RateLimitState(**json.loads(state_data))
        else:
            # Initialize with full bucket
            state = RateLimitState(
                current_requests=0,
                window_start=now,
                tokens=float(rate_limit.requests),
                last_refill=now
            )

        # Refill tokens based on time passed
        time_passed = now - state.last_refill
        refill_rate = rate_limit.requests / rate_limit.window  # tokens per second
        new_tokens = time_passed * refill_rate

        # Cap at burst limit
        max_tokens = rate_limit.requests * rate_limit.burst_multiplier
        state.tokens = min(max_tokens, state.tokens + new_tokens)
        state.last_refill = now

        # Check if we have tokens
        if state.tokens >= 1.0:
            # Consume one token
            state.tokens -= 1.0
            state.current_requests += 1

            # Store updated state with expiry
            self.redis_client.setex(
                key,
                rate_limit.window * 2,  # Keep state longer than window
                json.dumps(asdict(state))
            )

            logger.debug(
                "Rate limit check passed (token bucket)",
                extra={
                    "key": key,
                    "tokens_remaining": state.tokens,
                    "requests_made": state.current_requests
                }
            )

            return True
        else:
            logger.info(
                "Rate limit exceeded (token bucket)",
                extra={
                    "key": key,
                    "tokens_remaining": state.tokens,
                    "required": 1.0
                }
            )
            return False

    async def _check_sliding_window(self, key: str, rate_limit: RateLimit) -> bool:
        """
        Sliding window algorithm - smooth rate limiting

        Args:
            key: Redis key
            rate_limit: Rate limit configuration

        Returns:
            True if request allowed
        """
        now = time.time()
        window_key = f"{key}:sliding"

        # Use Redis sorted set to track requests in time window
        pipe = self.redis_client.pipeline()

        # Remove old requests outside the window
        cutoff = now - rate_limit.window
        pipe.zremrangebyscore(window_key, 0, cutoff)

        # Count current requests in window
        pipe.zcard(window_key)

        # Add current request timestamp
        pipe.zadd(window_key, {str(now): now})

        # Set expiry
        pipe.expire(window_key, rate_limit.window + 60)

        results = pipe.execute()
        current_count = results[1]  # Count after cleanup

        if current_count < rate_limit.requests:
            logger.debug(
                "Rate limit check passed (sliding window)",
                extra={
                    "key": key,
                    "current_count": current_count,
                    "limit": rate_limit.requests
                }
            )
            return True
        else:
            # Remove the request we just added since it's rejected
            self.redis_client.zrem(window_key, str(now))

            logger.info(
                "Rate limit exceeded (sliding window)",
                extra={
                    "key": key,
                    "current_count": current_count,
                    "limit": rate_limit.requests
                }
            )
            return False

    async def _check_fixed_window(self, key: str, rate_limit: RateLimit) -> bool:
        """
        Fixed window algorithm - simple but can have bursts at window boundaries

        Args:
            key: Redis key
            rate_limit: Rate limit configuration

        Returns:
            True if request allowed
        """
        now = time.time()
        window_start = int(now // rate_limit.window) * rate_limit.window
        window_key = f"{key}:window:{int(window_start)}"

        # Get current count in this window
        current_count = self.redis_client.get(window_key)
        current_count = int(current_count) if current_count else 0

        if current_count < rate_limit.requests:
            # Increment counter
            pipe = self.redis_client.pipeline()
            pipe.incr(window_key)
            pipe.expire(window_key, rate_limit.window + 60)
            pipe.execute()

            logger.debug(
                "Rate limit check passed (fixed window)",
                extra={
                    "key": key,
                    "current_count": current_count + 1,
                    "limit": rate_limit.requests
                }
            )
            return True
        else:
            logger.info(
                "Rate limit exceeded (fixed window)",
                extra={
                    "key": key,
                    "current_count": current_count,
                    "limit": rate_limit.requests
                }
            )
            return False

    async def get_limit_status(
        self,
        user_id: str,
        action: str,
        requests: int = 100,
        window: int = 60,
        limit_type: LimitType = LimitType.SLIDING_WINDOW
    ) -> Dict[str, Any]:
        """
        Get current rate limit status for debugging

        Args:
            user_id: User identifier
            action: Action being rate limited
            requests: Number of requests allowed
            window: Time window in seconds
            limit_type: Type of rate limiting algorithm

        Returns:
            Status dictionary
        """
        try:
            key = self._get_key(user_id, action)
            now = time.time()

            status = {
                "user_id": user_id,
                "action": action,
                "limit_type": limit_type.value,
                "requests_allowed": requests,
                "window_seconds": window,
                "current_time": now
            }

            if limit_type == LimitType.TOKEN_BUCKET:
                state_data = self.redis_client.get(key)
                if state_data:
                    state = RateLimitState(**json.loads(state_data))
                    status.update({
                        "tokens_available": state.tokens,
                        "requests_made": state.current_requests,
                        "last_refill": state.last_refill
                    })
                else:
                    status.update({
                        "tokens_available": float(requests),
                        "requests_made": 0,
                        "last_refill": now
                    })

            elif limit_type == LimitType.SLIDING_WINDOW:
                window_key = f"{key}:sliding"
                cutoff = now - window

                # Clean up and count
                pipe = self.redis_client.pipeline()
                pipe.zremrangebyscore(window_key, 0, cutoff)
                pipe.zcard(window_key)
                results = pipe.execute()

                current_count = results[1]
                status.update({
                    "requests_in_window": current_count,
                    "requests_remaining": max(0, requests - current_count),
                    "window_start": cutoff
                })

            elif limit_type == LimitType.FIXED_WINDOW:
                window_start = int(now // window) * window
                window_key = f"{key}:window:{int(window_start)}"

                current_count = self.redis_client.get(window_key)
                current_count = int(current_count) if current_count else 0

                status.update({
                    "requests_in_window": current_count,
                    "requests_remaining": max(0, requests - current_count),
                    "window_start": window_start,
                    "window_end": window_start + window
                })

            return status

        except Exception as e:
            logger.error(f"Error getting rate limit status: {e}")
            return {"error": str(e)}

    async def reset_limit(self, user_id: str, action: str) -> bool:
        """
        Reset rate limit for user/action (admin function)

        Args:
            user_id: User identifier
            action: Action to reset

        Returns:
            True if reset successfully
        """
        try:
            key = self._get_key(user_id, action)

            # Delete all related keys
            pattern = f"{key}*"
            keys = self.redis_client.keys(pattern)

            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(
                    "Reset rate limit",
                    extra={
                        "user_id": user_id,
                        "action": action,
                        "keys_deleted": deleted
                    }
                )
                return bool(deleted)

            return True

        except Exception as e:
            logger.error(f"Error resetting rate limit: {e}")
            return False

# Global instance
rate_limiter = RateLimiter()
