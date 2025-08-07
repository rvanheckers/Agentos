"""
Managers Performance Monitoring - New Domain
=============================================

Admin endpoints voor monitoring van service layer performance.
In de admin UI worden deze "Managers" genoemd voor business logic monitoring.

Metrics per Manager:
- Response times
- Success rates  
- Error counts
- Load statistics
- Uptime monitoring
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import time
import psutil
import logging

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from api.services.auth_dependencies import get_admin_user
# Temporarily disabled to fix imports
# from database.postgresql_manager import get_db_manager
get_db_manager = None

# Import services with error handling  
try:
    from services.jobs_service import JobsService
except ImportError:
    JobsService = None

try:
    from services.agents_service import AgentsService  
except ImportError:
    AgentsService = None

# Workers service removed - replaced by Celery monitoring
WorkersService = None

try:
    from services.queue_service import QueueService
except ImportError:
    QueueService = None

try:
    from services.upload_service import UploadService
except ImportError:
    UploadService = None

try:
    from services.analytics_service import AnalyticsService
except ImportError:
    AnalyticsService = None

try:
    from services.cleanup_service import CleanupService
except ImportError:
    CleanupService = None

logger = logging.getLogger(__name__)

# Admin only router for managers monitoring
admin_router = APIRouter(prefix="/api/admin", tags=["managers"])

# Service instances for monitoring (with safety checks)
managers = {}

if JobsService:
    try:
        managers["jobs"] = JobsService()
    except Exception as e:
        logger.warning(f"Failed to initialize JobsService: {e}")

if AgentsService:
    try:
        managers["agents"] = AgentsService()
    except Exception as e:
        logger.warning(f"Failed to initialize AgentsService: {e}")
        
if WorkersService:
    try:
        managers["workers"] = WorkersService()
    except Exception as e:
        logger.warning(f"Failed to initialize WorkersService: {e}")
        
if QueueService:
    try:
        managers["queue"] = QueueService()
    except Exception as e:
        logger.warning(f"Failed to initialize QueueService: {e}")
        
if UploadService:
    try:
        managers["upload"] = UploadService()
    except Exception as e:
        logger.warning(f"Failed to initialize UploadService: {e}")
        
if AnalyticsService:
    try:
        managers["analytics"] = AnalyticsService()
    except Exception as e:
        logger.warning(f"Failed to initialize AnalyticsService: {e}")

if CleanupService:
    try:
        from services.cleanup_service import cleanup_service  # Use singleton instance
        managers["cleanup"] = cleanup_service  # Use existing instance
    except Exception as e:
        logger.warning(f"Failed to initialize CleanupService: {e}")

logger.info(f"Managers monitoring initialized with {len(managers)} services: {list(managers.keys())}")


@admin_router.get("/managers/help")
async def get_managers_help():
    """Get help information for all managers - no auth required for help"""
    try:
        import json
        import os
        
        # Load help content from help.json
        help_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'ui-v2', 'docs', 'help.json')
        
        try:
            with open(help_file_path, 'r', encoding='utf-8') as f:
                help_data = json.load(f)
            
            # Return managers help section
            managers_help = help_data.get('nl', {}).get('managers', {})
            
            if not managers_help:
                # Fallback if help not found
                return {
                    "available": False,
                    "message": "Manager help content not available"
                }
            
            return {
                "available": True,
                "content": managers_help,
                "available_managers": list(managers.keys()),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except FileNotFoundError:
            return {
                "available": False,
                "message": "Help file not found",
                "fallback": {
                    "title": "Service Managers Help",
                    "description": "Managers are service layers that handle different parts of the system.",
                    "available_managers": list(managers.keys())
                }
            }
        except json.JSONDecodeError:
            return {
                "available": False,
                "message": "Help file format error"
            }
            
    except Exception as e:
        logger.error(f"Failed to load managers help: {e}")
        return {
            "available": False,
            "message": f"Error loading help: {str(e)}"
        }


@admin_router.get("/managers/{manager_name}/help")
async def get_manager_help(manager_name: str):
    """Get help information for specific manager - no auth required for help"""
    try:
        import json
        import os
        
        # Validate manager exists
        if manager_name not in managers:
            raise HTTPException(status_code=404, detail=f"Manager '{manager_name}' not found")
        
        # Load help content
        help_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'ui-v2', 'docs', 'help.json')
        
        try:
            with open(help_file_path, 'r', encoding='utf-8') as f:
                help_data = json.load(f)
            
            managers_help = help_data.get('nl', {}).get('managers', {})
            manager_help = managers_help.get(manager_name, {})
            
            if not manager_help:
                return {
                    "manager_name": manager_name,
                    "available": False,
                    "message": f"No help available for manager '{manager_name}'"
                }
            
            return {
                "manager_name": manager_name,
                "available": True,
                "help": manager_help,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except FileNotFoundError:
            return {
                "manager_name": manager_name,
                "available": False,
                "message": "Help file not found"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get help for manager {manager_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get manager help: {str(e)}")


@admin_router.get("/managers/status")
async def get_managers_status(current_user = Depends(get_admin_user)):
    """Get overall managers health status"""
    try:
        status_summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "managers_count": len(managers),
            "healthy": 0,
            "unhealthy": 0,
            "managers": {}
        }
        
        for name, service in managers.items():
            try:
                # Test if service responds
                start_time = time.time()
                
                # Call a lightweight method to test responsiveness
                if hasattr(service, 'get_stats'):
                    service.get_stats()
                elif hasattr(service, 'get_status'):
                    service.get_status()
                else:
                    # Fallback - just instantiate
                    service.__class__()
                
                response_time = (time.time() - start_time) * 1000  # ms
                
                status_summary["managers"][name] = {
                    "status": "healthy",
                    "response_time_ms": round(response_time, 2),
                    "last_check": datetime.utcnow().isoformat()
                }
                status_summary["healthy"] += 1
                
            except Exception as e:
                status_summary["managers"][name] = {
                    "status": "unhealthy", 
                    "error": str(e),
                    "last_check": datetime.utcnow().isoformat()
                }
                status_summary["unhealthy"] += 1
                logger.error(f"Manager {name} health check failed: {e}")
        
        # Overall system health
        status_summary["overall_health"] = "healthy" if status_summary["unhealthy"] == 0 else "degraded"
        
        return status_summary
        
    except Exception as e:
        logger.error(f"Managers status check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check managers status: {str(e)}")


@admin_router.get("/managers/{manager_name}/metrics")
async def get_manager_metrics(manager_name: str, current_user = Depends(get_admin_user)):
    """Get detailed performance metrics for specific manager"""
    
    if manager_name not in managers:
        raise HTTPException(status_code=404, detail=f"Manager '{manager_name}' not found")
    
    try:
        service = managers[manager_name]
        
        # Performance test
        start_time = time.time()
        method_results = {}
        
        # Test common methods
        test_methods = ['get_stats', 'get_status', 'get_summary']
        
        for method_name in test_methods:
            if hasattr(service, method_name):
                try:
                    method_start = time.time()
                    method = getattr(service, method_name)
                    result = method()
                    method_time = (time.time() - method_start) * 1000
                    
                    method_results[method_name] = {
                        "response_time_ms": round(method_time, 2),
                        "success": True,
                        "result_size": len(str(result)) if result else 0
                    }
                except Exception as e:
                    method_results[method_name] = {
                        "response_time_ms": 0,
                        "success": False,
                        "error": str(e)
                    }
        
        total_time = (time.time() - start_time) * 1000
        
        # System resource usage
        process = psutil.Process()
        
        # Calculate success rate
        successful_methods = len([r for r in method_results.values() if r.get("success")])
        success_rate = successful_methods / len(method_results) if method_results else 0
        
        metrics = {
            "manager_name": manager_name,
            "timestamp": datetime.utcnow().isoformat(),
            "performance": {
                "total_response_time_ms": round(total_time, 2),
                "methods_tested": len(method_results),
                "methods_successful": successful_methods,
                "avg_method_time_ms": round(sum(r.get("response_time_ms", 0) for r in method_results.values()) / len(method_results), 2) if method_results else 0
            },
            "method_details": method_results,
            "system_resources": {
                "cpu_percent": process.cpu_percent(),
                "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "open_files": len(process.open_files()) if hasattr(process, 'open_files') else 0
            },
            "health_score": calculate_health_score(method_results, total_time)
        }
        
        # Log performance data to database voor historical tracking
        try:
            db_manager = get_db_manager()
            db_manager.log_manager_performance(manager_name, {
                "response_time_ms": round(total_time, 2),
                "success_rate": success_rate,
                "methods_tested": len(method_results),
                "methods_successful": successful_methods,
                "cpu_usage": process.cpu_percent() / 100,  # Normalize to 0-1
                "memory_usage": round(process.memory_info().rss / 1024 / 1024, 2),
                "health_score": metrics["health_score"]
            })
        except Exception as e:
            logger.warning(f"Failed to log performance data for {manager_name}: {e}")
        
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get metrics for manager {manager_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get manager metrics: {str(e)}")


@admin_router.get("/managers/performance-summary")
async def get_managers_performance_summary(current_user = Depends(get_admin_user)):
    """Get performance summary for all managers - ideal for dashboard"""
    try:
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "overview": {
                "total_managers": len(managers),
                "healthy_managers": 0,
                "avg_response_time_ms": 0,
                "total_methods_tested": 0
            },
            "managers": []
        }
        
        total_response_times = []
        
        for name, service in managers.items():
            try:
                # Quick performance test
                start_time = time.time()
                
                # Test primary method
                if hasattr(service, 'get_stats'):
                    service.get_stats()
                elif hasattr(service, 'get_status'):
                    service.get_status()
                
                response_time = (time.time() - start_time) * 1000
                total_response_times.append(response_time)
                
                manager_summary = {
                    "name": name,
                    "status": "healthy",
                    "response_time_ms": round(response_time, 2),
                    "health_indicator": "🟢" if response_time < 100 else "🟡" if response_time < 500 else "🔴"
                }
                
                # Log performance data for this manager
                try:
                    db_manager = get_db_manager()
                    db_manager.log_manager_performance(name, {
                        "response_time_ms": round(response_time, 2),
                        "success_rate": 1.0,  # Healthy = 100% success
                        "status": "healthy",
                        "cpu_usage": psutil.cpu_percent() / 100,
                        "memory_usage": psutil.virtual_memory().percent / 100,
                        "health_indicator": manager_summary["health_indicator"]
                    })
                except Exception as log_e:
                    logger.warning(f"Failed to log performance data for {name}: {log_e}")
                
                summary["overview"]["healthy_managers"] += 1
                
            except Exception as e:
                manager_summary = {
                    "name": name,
                    "status": "error",
                    "error": str(e),
                    "health_indicator": "🔴"
                }
                logger.warning(f"Manager {name} performance test failed: {e}")
            
            summary["managers"].append(manager_summary)
        
        # Calculate overview metrics
        if total_response_times:
            summary["overview"]["avg_response_time_ms"] = round(sum(total_response_times) / len(total_response_times), 2)
        
        summary["overview"]["total_methods_tested"] = len(total_response_times)
        summary["overview"]["system_health"] = "🟢 Healthy" if summary["overview"]["healthy_managers"] == len(managers) else "🟡 Degraded"
        
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get managers performance summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance summary: {str(e)}")


@admin_router.get("/managers/{manager_name}/history")
async def get_manager_performance_history(
    manager_name: str,
    start_date: str,
    end_date: str,
    current_user = Depends(get_admin_user)
):
    """Get historical performance data for specific manager"""
    try:
        # Validate manager exists
        if manager_name not in managers:
            raise HTTPException(status_code=404, detail=f"Manager '{manager_name}' not found")
        
        db_manager = get_db_manager()
        history_data = db_manager.get_manager_performance_history(manager_name, start_date, end_date)
        
        return {
            "manager_name": manager_name,
            "start_date": start_date,
            "end_date": end_date,
            "data_points": len(history_data),
            "history": history_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get performance history for {manager_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance history: {str(e)}")


# NOTE: /managers/history/all endpoint removed per cleanup plan
# Use /api/admin/managers?include=history query parameter instead

# @admin_router.get("/managers/history/all")
async def get_all_managers_performance_history(
    start_date: str,
    end_date: str,
    current_user = Depends(get_admin_user)
):
    """Get historical performance data for all managers"""
    try:
        db_manager = get_db_manager()
        all_history_data = db_manager.get_all_managers_performance_history(start_date, end_date)
        
        # Add summary statistics
        summary = {
            "start_date": start_date,
            "end_date": end_date,
            "managers_tracked": len(all_history_data),
            "total_data_points": sum(len(data) for data in all_history_data.values()),
            "managers": list(all_history_data.keys())
        }
        
        return {
            "summary": summary,
            "data": all_history_data
        }
        
    except Exception as e:
        logger.error(f"Failed to get all managers performance history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance history: {str(e)}")


def calculate_health_score(method_results: Dict, total_time_ms: float) -> str:
    """Calculate health score based on performance metrics"""
    
    if not method_results:
        return "Unknown"
    
    successful_methods = len([r for r in method_results.values() if r.get("success")])
    total_methods = len(method_results)
    success_rate = successful_methods / total_methods
    
    # Score based on success rate and response time
    if success_rate == 1.0 and total_time_ms < 100:
        return "Excellent"
    elif success_rate >= 0.8 and total_time_ms < 500:
        return "Good"
    elif success_rate >= 0.6 and total_time_ms < 1000:
        return "Fair"
    else:
        return "Poor"