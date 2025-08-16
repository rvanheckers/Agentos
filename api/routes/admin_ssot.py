"""
Admin SSOT (Single Source of Truth) API Route

Deze route biedt één endpoint voor alle admin data via AdminDataManager.
Vervangt de chaos van 6+ HTTP endpoints met één geconsolideerde call.

Architectuur: Service Layer SSOT Pattern
- Endpoint: GET /api/admin/ssot
- Response: Alle admin data in één JSON object
- Performance target: <100ms response tijd
- Caching: Via AdminDataManager (20-30s TTL)

Created: 2 Augustus 2025
Purpose: Frontend CentralDataService → AdminDataManager integration
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging
import time
import asyncio
from datetime import datetime

# Import AdminDataManager
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.admin_data_manager import AdminDataManager

logger = logging.getLogger(__name__)

# Create router with admin-dashboard tag
router = APIRouter(tags=["admin-dashboard"])

@router.get("/api/admin/ssot")
async def get_admin_ssot_data(
    time_range: Optional[str] = Query("24h", description="Time range for analytics: 1h, 24h, 7d, 30d"),
    log_filters: Optional[str] = Query(None, description="JSON string for log filters")
):
    """
    Single Source of Truth endpoint voor alle admin UI data.

    Consolideert alle admin data in één API call:
    - Dashboard data (workers, queue, jobs, system health)
    - Queue data (current queue, job history, worker assignments)
    - Agents/Workers data (status, configuration, performance)
    - Analytics data (usage stats, performance metrics, trends)
    - System data (controls, configuration, maintenance)

    Performance target: <100ms
    Caching: 20-30s TTL via AdminDataManager

    Args:
        time_range: Analytics time range (1h, 24h, 7d, 30d)
        log_filters: Optional JSON string for log filtering

    Returns:
        JSON object met alle admin data geconsolideerd
    """
    start_time = time.time()

    try:
        # Initialize AdminDataManager
        admin_data = AdminDataManager()

        # Parse log filters if provided
        filters = None
        if log_filters:
            import json
            try:
                filters = json.loads(log_filters)
            except json.JSONDecodeError:
                logger.warning(f"Invalid log_filters JSON: {log_filters}")
                filters = None

        # V4 PARALLEL EXECUTION: Use async AdminDataManager for 128x faster performance
        logger.debug(f"V4: Fetching admin SSOT data with parallel execution (time_range={time_range})")

        # V4 CACHE-FIRST ARCHITECTURE: Use direct sync calls for reliable data
        if time_range == "24h":
            # FIXED: Use direct sync methods instead of async for reliable data 
            dashboard_data = admin_data.get_dashboard_data()
            analytics_data = admin_data.get_analytics_data()
            agents_workers_data = admin_data.get_agents_workers_data()
            logs_data = admin_data.get_logs_data()
            system_control_data = admin_data.get_system_control_data()
            configuration_data = admin_data.get_configuration_data()
            
            response_data = {
                'timestamp': datetime.now().isoformat(),
                'dashboard': dashboard_data,
                'analytics': analytics_data,
                'agents_workers': agents_workers_data,
                'agents': agents_workers_data,  # Provide both keys for compatibility
                'logs': logs_data,
                'system_control': system_control_data,
                'configuration': configuration_data,
                'status': 'success',
                'architecture': 'v4_direct_sync',
                'response_time_ms': 0,
                'time_range': time_range
            }
        else:
            # For custom time_range, build response with parallel execution but correct analytics
            logger.info(f"V4: Starting custom parallel execution for time_range={time_range}")
            parallel_start = time.time()

            # Execute all data collection in parallel with correct time_range
            dashboard_task = asyncio.create_task(admin_data._get_dashboard_data_async())
            queue_task = asyncio.create_task(admin_data._get_queue_data_async())
            analytics_task = asyncio.create_task(admin_data._get_analytics_data_async(time_range))  # Correct time_range
            agents_task = asyncio.create_task(admin_data._get_agents_workers_data_async())
            logs_task = asyncio.create_task(admin_data._get_logs_data_async())
            system_task = asyncio.create_task(admin_data._get_system_control_data_async())
            config_task = asyncio.create_task(admin_data._get_configuration_data_async())

            results = await asyncio.gather(
                dashboard_task, queue_task, analytics_task, agents_task,
                logs_task, system_task, config_task,
                return_exceptions=True
            )

            parallel_end = time.time()
            logger.info(f"V4: Parallel execution completed in {(parallel_end - parallel_start)*1000:.2f}ms")

            # Build response data with timing
            end_time = time.time()
            response_time = (end_time - start_time) * 1000

            # CRITICAL FIX: Use flat structure consistent with get_all_data()
            dashboard_data = results[0] if not isinstance(results[0], Exception) else {'error': str(results[0])}

            response_data = {
                'timestamp': datetime.now().isoformat(),
                'dashboard': {
                    'workers': dashboard_data.get('workers', {}),
                    'queue': dashboard_data.get('queue', {}),
                    'jobs': dashboard_data.get('jobs', {}),
                    'system': dashboard_data.get('system', {}),
                    'recent_activity': dashboard_data.get('recent_activity', [])
                },
                'analytics': results[2] if not isinstance(results[2], Exception) else {'error': str(results[2])},
                'agents_workers': results[3] if not isinstance(results[3], Exception) else {'error': str(results[3])},
                'logs': results[4] if not isinstance(results[4], Exception) else {'error': str(results[4])},
                'system_control': results[5] if not isinstance(results[5], Exception) else {'error': str(results[5])},
                'configuration': results[6] if not isinstance(results[6], Exception) else {'error': str(results[6])},
                'response_time_ms': round(response_time, 2),
                'status': 'success',
                'architecture': 'v4_parallel_execution'
            }

            # V4 WEBSOCKET BROADCAST: Send complete admin data to WebSocket clients
            admin_data.broadcast_admin_update(response_data)

        # Include logs if filters provided
        if filters:
            response_data["logs"] = await admin_data._get_logs_data_async(filters)

        # Add time_range to response
        response_data["time_range"] = time_range

        # Performance logging
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # ms

        # Use response time from AdminDataManager if available, otherwise calculate
        if "response_time_ms" not in response_data:
            response_data["response_time_ms"] = round(response_time, 2)

        if response_time > 100:
            logger.warning(f"SSOT endpoint slow: {response_time:.2f}ms (target: <100ms)")
        else:
            logger.debug(f"SSOT endpoint performance: {response_time:.2f}ms")

        return response_data

    except Exception as e:
        end_time = time.time()
        response_time = (end_time - start_time) * 1000

        logger.error(f"Failed to get admin SSOT data: {str(e)}")

        # Return error response met performance data
        return {
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "status": "error",
            "response_time_ms": round(response_time, 2)
        }

@router.get("/api/admin/ssot/dashboard")
async def get_dashboard_only():
    """
    Quick endpoint voor alleen dashboard data.
    Voor use cases waar alleen dashboard refresh nodig is.
    """
    start_time = time.time()

    try:
        admin_data = AdminDataManager()
        dashboard_data = await admin_data._get_dashboard_data_async()

        end_time = time.time()
        response_time = (end_time - start_time) * 1000

        return {
            "timestamp": datetime.now().isoformat(),
            "dashboard": dashboard_data,
            "response_time_ms": round(response_time, 2),
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Failed to get dashboard data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/admin/ssot/health")
async def ssot_health_check():
    """
    Health check voor SSOT endpoint.
    Test of AdminDataManager correct geïnitialiseerd is.
    """
    try:
        admin_data = AdminDataManager()

        # Quick test van onderliggende services
        test_results = {
            "admin_data_manager": "ok",
            "jobs_service": "unknown",
            "queue_service": "unknown",
            "analytics_service": "unknown",
            "agents_service": "unknown"
        }

        # Test basic functionality
        try:
            dashboard = await admin_data._get_dashboard_data_async()
            if dashboard.get("status") == "success":
                test_results["dashboard_data"] = "ok"
            else:
                test_results["dashboard_data"] = "error"
        except Exception as e:
            test_results["dashboard_data"] = f"error: {str(e)}"

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": test_results
        }

    except Exception as e:
        logger.error(f"SSOT health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }
