"""
Admin Cache Warming Task
========================
Runs every 5 seconds to keep admin dashboard cache fresh.
This ensures dashboard loads in <5ms instead of 500ms+.

V4 Architecture: Cache-first pattern for instant dashboard
"""

import asyncio
import json
import redis
import logging
import uuid
import sys
import os
from datetime import datetime
from celery import shared_task

class AdminDataEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles UUIDs and datetimes"""
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Import AdminDataManager after path setup
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.admin_data_manager import AdminDataManager  # noqa: E402

logger = logging.getLogger(__name__)

@shared_task(name='warm_admin_cache')
def warm_admin_cache():
    """
    Background task that runs every 5 seconds to keep cache warm.
    This ensures users ALWAYS get instant dashboard loads (5ms).
    """
    try:
        start_time = datetime.now()

        # Initialize services
        admin_manager = AdminDataManager()
        redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

        # Fetch ALL data in parallel (including agents_workers!)
        logger.info("🔥 Cache warming: Starting parallel data collection")

        # Use asyncio to run the async method
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Get fresh data from all services
            fresh_data = loop.run_until_complete(admin_manager._collect_all_data_fresh())
        finally:
            loop.close()

        # Validate data completeness
        required_keys = ['dashboard', 'agents_workers', 'analytics', 'queue', 'logs', 'system_control']
        missing_keys = [key for key in required_keys if key not in fresh_data]

        if missing_keys:
            logger.warning(f"⚠️ Cache warming: Missing keys: {missing_keys}")

        # Store in Redis with 15 second TTL (task runs every 5 seconds = 3x safety)
        cache_key = "admin:dashboard:v4"
        cache_data = json.dumps(fresh_data, cls=AdminDataEncoder)

        redis_client.setex(cache_key, 15, cache_data)

        # Calculate performance
        elapsed = (datetime.now() - start_time).total_seconds() * 1000

        # Log success
        logger.info(f"✅ Cache warmed successfully in {elapsed:.2f}ms")
        logger.debug(f"   - Dashboard: {bool(fresh_data.get('dashboard'))}")
        logger.debug(f"   - Agents: {fresh_data.get('agents_workers', {}).get('agents', {}).get('status', {}).get('total_agents', 0)} agents")
        logger.debug(f"   - Cache size: {len(cache_data)} bytes")

        return {
            "status": "success",
            "elapsed_ms": elapsed,
            "cache_size": len(cache_data),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Cache warming failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@shared_task(name='validate_cache_health')
def validate_cache_health():
    """
    Validates that cache contains complete data.
    Runs every minute to ensure cache quality.
    """
    try:
        redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

        # Get current cache
        cache_data = redis_client.get("admin:dashboard:v4")

        if not cache_data:
            logger.warning("⚠️ Cache validation: Cache is empty!")
            return {"status": "empty"}

        # Parse and validate
        data = json.loads(cache_data)

        # Check data freshness
        cache_age = redis_client.ttl("admin:dashboard:v4")

        # Validate structure
        validation = {
            "has_dashboard": "dashboard" in data,
            "has_agents": "agents_workers" in data,
            "has_analytics": "analytics" in data,
            "cache_age_seconds": 15 - cache_age if cache_age > 0 else "expired",
            "total_agents": data.get('agents_workers', {}).get('agents', {}).get('status', {}).get('total_agents', 0)
        }

        # Log any issues
        if validation["total_agents"] == 0:
            logger.warning("⚠️ Cache validation: No agents in cache!")

        if not validation["has_dashboard"]:
            logger.error("❌ Cache validation: Missing dashboard data!")

        return {
            "status": "validated",
            "validation": validation,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"❌ Cache validation failed: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }
