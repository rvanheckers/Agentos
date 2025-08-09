"""
Idempotency Service
Ensures actions can be safely retried without side effects
"""

import json
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
import redis
import logging

logger = logging.getLogger("agentos.idempotency")

class IdempotencyService:
    """
    Service for handling idempotent operations

    Features:
    - SHA256-based key generation
    - Redis-backed storage with TTL
    - Payload fingerprinting
    - Collision detection
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/1", default_ttl: int = 86400):
        """
        Initialize idempotency service

        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds (24 hours)
        """
        self.redis_client = redis.from_url(redis_url)
        self.default_ttl = default_ttl
        self.key_prefix = "idempotency:"

    def _generate_key(self, idempotency_key: str, action: str, user_id: str) -> str:
        """Generate unique key for idempotency checking"""
        key_data = f"{idempotency_key}:{action}:{user_id}"
        return f"{self.key_prefix}{hashlib.sha256(key_data.encode()).hexdigest()}"

    def _generate_payload_fingerprint(self, payload: Dict[str, Any]) -> str:
        """Generate fingerprint of payload to detect changes"""
        # Sort keys for consistent hashing
        sorted_payload = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(sorted_payload.encode()).hexdigest()

    async def check(
        self,
        idempotency_key: str,
        action: str,
        user_id: str,
        payload: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Check if operation was already executed

        Args:
            idempotency_key: Client-provided idempotency key
            action: Action being performed
            user_id: User performing the action
            payload: Action payload for fingerprinting

        Returns:
            Previous result if found, None otherwise

        Raises:
            ValueError: If payload fingerprint doesn't match
        """
        try:
            cache_key = self._generate_key(idempotency_key, action, user_id)
            cached_data = self.redis_client.get(cache_key)

            if not cached_data:
                return None

            stored_data = json.loads(cached_data)

            # Check payload fingerprint if provided
            if payload is not None:
                current_fingerprint = self._generate_payload_fingerprint(payload)
                stored_fingerprint = stored_data.get("payload_fingerprint")

                if stored_fingerprint and current_fingerprint != stored_fingerprint:
                    logger.warning(
                        "Idempotency key reused with different payload",
                        extra={
                            "idempotency_key": idempotency_key,
                            "action": action,
                            "user_id": user_id
                        }
                    )
                    raise ValueError("Idempotency key reused with different payload")

            logger.info(
                "Idempotent operation found",
                extra={
                    "idempotency_key": idempotency_key,
                    "action": action,
                    "original_timestamp": stored_data.get("timestamp")
                }
            )

            return stored_data.get("result")

        except redis.RedisError as e:
            logger.error(f"Redis error in idempotency check: {e}")
            # Don't fail the operation, just skip idempotency
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in idempotency check: {e}")
            # Corrupt cache entry, remove it
            try:
                self.redis_client.delete(cache_key)
            except:
                pass
            return None

    async def store(
        self,
        idempotency_key: str,
        action: str,
        user_id: str,
        result: Dict[str, Any],
        payload: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store operation result for idempotency

        Args:
            idempotency_key: Client-provided idempotency key
            action: Action that was performed
            user_id: User who performed the action
            result: Result of the operation
            payload: Action payload for fingerprinting
            ttl: Custom TTL in seconds

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            cache_key = self._generate_key(idempotency_key, action, user_id)

            storage_data = {
                "action": action,
                "user_id": user_id,
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
                "idempotency_key": idempotency_key
            }

            # Add payload fingerprint if provided
            if payload is not None:
                storage_data["payload_fingerprint"] = self._generate_payload_fingerprint(payload)

            # Store with TTL
            storage_ttl = ttl or self.default_ttl
            self.redis_client.setex(
                cache_key,
                storage_ttl,
                json.dumps(storage_data, default=str)
            )

            logger.debug(
                "Stored idempotency result",
                extra={
                    "idempotency_key": idempotency_key,
                    "action": action,
                    "ttl": storage_ttl
                }
            )

            return True

        except redis.RedisError as e:
            logger.error(f"Redis error storing idempotency result: {e}")
            return False
        except Exception as e:
            logger.error(f"Error storing idempotency result: {e}")
            return False

    async def invalidate(
        self,
        idempotency_key: str,
        action: str,
        user_id: str
    ) -> bool:
        """
        Invalidate stored idempotency result

        Args:
            idempotency_key: Client-provided idempotency key
            action: Action to invalidate
            user_id: User who performed the action

        Returns:
            True if invalidated, False otherwise
        """
        try:
            cache_key = self._generate_key(idempotency_key, action, user_id)
            deleted = self.redis_client.delete(cache_key)

            logger.debug(
                "Invalidated idempotency result",
                extra={
                    "idempotency_key": idempotency_key,
                    "action": action,
                    "deleted": bool(deleted)
                }
            )

            return bool(deleted)

        except redis.RedisError as e:
            logger.error(f"Redis error invalidating idempotency result: {e}")
            return False

    async def cleanup_expired(self) -> int:
        """
        Clean up expired idempotency keys (Redis handles this automatically with TTL)
        This method is for manual cleanup if needed

        Returns:
            Number of keys cleaned up
        """
        try:
            # Find all idempotency keys
            pattern = f"{self.key_prefix}*"
            keys = self.redis_client.keys(pattern)

            cleaned = 0
            for key in keys:
                # Check if key exists (Redis TTL cleanup might have removed it)
                if not self.redis_client.exists(key):
                    cleaned += 1

            logger.info(f"Idempotency cleanup completed, {cleaned} expired keys found")
            return cleaned

        except redis.RedisError as e:
            logger.error(f"Redis error during idempotency cleanup: {e}")
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get idempotency service statistics

        Returns:
            Statistics dictionary
        """
        try:
            pattern = f"{self.key_prefix}*"
            keys = self.redis_client.keys(pattern)

            total_keys = len(keys)

            # Sample some keys to get statistics
            sample_size = min(100, total_keys)
            sample_keys = keys[:sample_size] if total_keys > 0 else []

            actions = {}
            oldest_timestamp = None
            newest_timestamp = None

            for key in sample_keys:
                try:
                    data = self.redis_client.get(key)
                    if data:
                        stored_data = json.loads(data)
                        action = stored_data.get("action", "unknown")
                        actions[action] = actions.get(action, 0) + 1

                        timestamp = stored_data.get("timestamp")
                        if timestamp:
                            if not oldest_timestamp or timestamp < oldest_timestamp:
                                oldest_timestamp = timestamp
                            if not newest_timestamp or timestamp > newest_timestamp:
                                newest_timestamp = timestamp
                except:
                    continue

            return {
                "total_keys": total_keys,
                "sample_size": sample_size,
                "actions_breakdown": actions,
                "oldest_entry": oldest_timestamp,
                "newest_entry": newest_timestamp,
                "default_ttl_hours": self.default_ttl / 3600
            }

        except redis.RedisError as e:
            logger.error(f"Redis error getting idempotency stats: {e}")
            return {"error": str(e)}

# Global instance
idempotency_service = IdempotencyService()
