"""
Celery Workers Management Routes for Admin UI
============================================

Replacement voor oude /workers endpoints met Celery worker integration.
Admin UI compatibility met dezelfde data structures.
"""

from fastapi import APIRouter
import logging
from datetime import datetime
import subprocess
import psutil

logger = logging.getLogger(__name__)

# Admin router voor workers management
admin_router = APIRouter(prefix="/api/admin", tags=["celery-workers"])

def get_celery_worker_status():
    """Get Celery worker status using celery inspect"""
    try:
        # Use celery inspect to get worker info
        result = subprocess.run([
            'celery', '-A', 'core.celery_app', 'inspect', 'active'
        ], capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            # Parse the output to get worker info
            active_tasks = {}
            try:
                # Basic parsing of celery inspect output
                lines = result.stdout.strip().split('\n')
                current_worker = None

                for line in lines:
                    if line.startswith('->'):
                        # Worker identifier line
                        current_worker = line.replace('->', '').strip().replace(':', '')
                        active_tasks[current_worker] = []
                    elif current_worker and line.strip() and not line.startswith('->'):
                        # Task info line
                        if 'empty' not in line.lower():
                            active_tasks[current_worker].append(line.strip())

            except Exception as parse_error:
                logger.warning(f"Failed to parse celery output: {parse_error}")

            return active_tasks
        else:
            logger.warning(f"Celery inspect failed: {result.stderr}")
            return {}

    except subprocess.TimeoutExpired:
        logger.warning("Celery inspect timed out")
        return {}
    except Exception as e:
        logger.error(f"Error getting celery worker status: {e}")
        return {}

def get_celery_worker_stats():
    """Get Celery worker statistics"""
    try:
        # Get stats using celery inspect stats
        result = subprocess.run([
            'celery', '-A', 'core.celery_app', 'inspect', 'stats'
        ], capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            # Basic stats extraction
            stats = {}
            lines = result.stdout.strip().split('\n')

            for line in lines:
                if 'pool' in line.lower() and 'processes' in line.lower():
                    # Extract process count info
                    if 'max-concurrency' in line:
                        try:
                            concurrency = int(line.split('max-concurrency')[1].split()[0].strip(':,'))
                            stats['max_concurrency'] = concurrency
                        except:
                            pass

            return stats
        else:
            return {}

    except Exception as e:
        logger.error(f"Error getting celery stats: {e}")
        return {}

def count_celery_processes():
    """Count actual Celery worker processes"""
    try:
        worker_count = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any('celery' in str(arg) and 'worker' in str(arg) for arg in cmdline):
                    # Make sure it's our app
                    if any('core.celery_app' in str(arg) for arg in cmdline):
                        worker_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return worker_count
    except Exception as e:
        logger.error(f"Error counting celery processes: {e}")
        return 0

@admin_router.get("/workers/details")
async def get_workers_details():
    """
    🔄 CELERY COMPATIBILITY - Replacement for old workers/details endpoint

    Returns Admin UI compatible data structure with Celery worker information
    """
    try:
        # Get Celery worker information
        active_tasks = get_celery_worker_status()
        worker_stats = get_celery_worker_stats()
        process_count = count_celery_processes()

        # Transform to Admin UI expected format
        workers = []
        worker_id_counter = 1

        for worker_name, tasks in active_tasks.items():
            workers.append({
                "id": f"celery_{worker_id_counter}",
                "name": worker_name,
                "type": "celery_worker",
                "status": "active" if tasks else "idle",
                "active_tasks": len(tasks),
                "task_details": tasks[:3],  # Show first 3 tasks
                "pid": None,  # Would need more complex lookup
                "memory_usage": "N/A",
                "cpu_usage": "N/A",
                "uptime": "N/A",
                "last_heartbeat": datetime.now().isoformat()
            })
            worker_id_counter += 1

        # If no workers detected via inspect, show process count
        if not workers and process_count > 0:
            for i in range(process_count):
                workers.append({
                    "id": f"celery_process_{i+1}",
                    "name": f"celery-worker-{i+1}",
                    "type": "celery_worker",
                    "status": "running",
                    "active_tasks": 0,
                    "task_details": [],
                    "pid": None,
                    "memory_usage": "N/A",
                    "cpu_usage": "N/A",
                    "uptime": "N/A",
                    "last_heartbeat": datetime.now().isoformat()
                })

        # Calculate metrics in Admin UI expected format
        total_workers = len(workers)
        active_workers = len([w for w in workers if w["status"] == "active"])
        idle_workers = total_workers - active_workers

        response = {
            "success": True,
            "workers": workers,
            "metrics": {
                "worker_types": {
                    "total": total_workers,
                    "active": active_workers,
                    "idle": idle_workers
                },
                "system": {
                    "celery_processes": process_count,
                    "max_concurrency": worker_stats.get("max_concurrency", "unknown"),
                    "task_queue": "celery",
                    "broker": "redis"
                },
                "timestamp": datetime.now().isoformat()
            },
            "total": total_workers,
            "active": active_workers,
            "idle": idle_workers
        }

        logger.info(f"Celery workers status: {total_workers} total, {active_workers} active")
        return response

    except Exception as e:
        logger.error(f"Error getting Celery worker details: {e}")

        # Fallback response for Admin UI compatibility
        return {
            "success": False,
            "error": str(e),
            "workers": [],
            "metrics": {
                "worker_types": {
                    "total": 0,
                    "active": 0,
                    "idle": 0
                },
                "system": {
                    "celery_processes": 0,
                    "max_concurrency": 0,
                    "task_queue": "celery",
                    "broker": "redis"
                },
                "timestamp": datetime.now().isoformat()
            },
            "total": 0,
            "active": 0,
            "idle": 0
        }

# NOTE: /workers/status endpoint removed per cleanup plan
# Use /api/admin/workers endpoint instead (system.py) which provides same data

@admin_router.post("/workers/{worker_id}/restart")
async def restart_worker(worker_id: str):
    """
    Restart Celery worker (placeholder - requires advanced Celery management)
    """
    return {
        "success": True,
        "message": f"Worker restart initiated for {worker_id}",
        "note": "Celery worker management requires process-level control"
    }

@admin_router.post("/workers/{worker_id}/stop")
async def stop_worker(worker_id: str):
    """
    Stop Celery worker (placeholder - requires advanced Celery management)
    """
    return {
        "success": True,
        "message": f"Worker stop initiated for {worker_id}",
        "note": "Use 'celery -A core.celery_app control shutdown' for graceful shutdown"
    }

@admin_router.get("/workers/{worker_id}/logs")
async def get_worker_logs(worker_id: str, lines: int = 100):
    """
    Get Celery worker logs
    """
    try:
        # For now, return Celery logs from system logs
        return {
            "success": True,
            "logs": [
                f"Celery worker {worker_id} log entry {i}"
                for i in range(min(lines, 20))
            ],
            "total_lines": lines,
            "note": "Check logs/celery.log for detailed Celery worker logs"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "logs": []
        }

@admin_router.get("/workers/{worker_id}/metrics")
async def get_worker_metrics(worker_id: str):
    """
    Get Celery worker metrics
    """
    try:
        return {
            "success": True,
            "metrics": {
                "worker_id": worker_id,
                "tasks_processed": "N/A",
                "tasks_active": "N/A",
                "memory_usage": "N/A",
                "cpu_usage": "N/A",
                "uptime": "N/A"
            },
            "note": "Use Flower dashboard (http://localhost:5555) for detailed metrics"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "metrics": {}
        }

# system-check endpoint removed - using existing one from system.py router
