"""
Simple AdminDataManager service for SSOT endpoint
Provides mock data for admin dashboard
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any
import random
import logging

logger = logging.getLogger(__name__)

class AdminDataManager:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 30  # 30 seconds TTL
        self.last_update = None
    
    async def get_all_admin_data(self) -> Dict[str, Any]:
        """Get all admin data in SSOT format"""
        try:
            now = datetime.now()
            
            # Check cache
            if (self.last_update and 
                (now - self.last_update).total_seconds() < self.cache_ttl and
                self.cache):
                logger.info("Returning cached admin data")
                return self.cache
            
            # Generate fresh data
            logger.info("Generating fresh admin data")
            data = {
                "timestamp": now.isoformat(),
                "status": "success",
                "dashboard": await self.get_dashboard_data(),
                "jobs": await self.get_jobs_data(),
                "queue": await self.get_queue_data(),
                "agents": await self.get_agents_data(),
                "system": await self.get_system_data(),
                "analytics": await self.get_analytics_data()
            }
            
            # Update cache
            self.cache = data
            self.last_update = now
            
            return data
            
        except Exception as e:
            logger.error(f"Error generating admin data: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "error": str(e),
                "dashboard": {},
                "jobs": {"recent_jobs": []},
                "queue": {},
                "agents": {},
                "system": {},
                "analytics": {}
            }
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Generate dashboard data"""
        return {
            "jobs": {
                "recent_jobs": await self._generate_recent_jobs()
            },
            "stats": {
                "total_jobs": random.randint(100, 500),
                "completed_today": random.randint(20, 80),
                "failed_today": random.randint(0, 10),
                "processing_now": random.randint(0, 15),
                "queue_depth": random.randint(0, 25)
            }
        }
    
    async def get_jobs_data(self) -> Dict[str, Any]:
        """Generate jobs data"""
        return {
            "recent_jobs": await self._generate_recent_jobs(),
            "stats": {
                "total": random.randint(100, 500),
                "completed": random.randint(80, 400),
                "failed": random.randint(5, 30),
                "processing": random.randint(0, 15)
            }
        }
    
    async def _generate_recent_jobs(self) -> list:
        """Generate realistic recent jobs"""
        jobs = []
        statuses = ['completed', 'processing', 'failed', 'queued']
        task_types = ['video_processing', 'audio_extraction', 'transcription', 'analysis', 'export']
        priorities = ['high', 'medium', 'low']
        
        for i in range(random.randint(10, 25)):
            status = random.choice(statuses)
            created_time = datetime.now() - timedelta(
                hours=random.randint(0, 48),
                minutes=random.randint(0, 59)
            )
            
            job = {
                "id": f"job_{i+1}_{random.randint(1000, 9999)}",
                "name": f"Processing Task {i+1}",
                "description": f"Automated {random.choice(task_types).replace('_', ' ')} task",
                "status": status,
                "priority": random.choice(priorities),
                "type": random.choice(task_types),
                "task_type": random.choice(task_types),
                "created_at": created_time.isoformat(),
                "timestamp": created_time.isoformat(),
                "progress": random.randint(0, 100) if status == 'processing' else (100 if status == 'completed' else 0),
                "duration": random.randint(30, 600) if status == 'completed' else None,
                "processing_time": random.randint(30, 600) if status == 'completed' else None,
                "agent_id": f"agent_{random.randint(1, 5)}",
                "worker_id": f"worker_{random.randint(1, 10)}"
            }
            
            # Add completion/failure timestamps
            if status == 'completed':
                job["completed_at"] = (created_time + timedelta(seconds=job["duration"])).isoformat()
            elif status == 'failed':
                job["failed_at"] = (created_time + timedelta(seconds=random.randint(10, 300))).isoformat()
                job["error"] = random.choice([
                    "Connection timeout",
                    "Processing error", 
                    "Invalid input format",
                    "Resource unavailable",
                    "Worker crashed"
                ])
            elif status == 'processing':
                job["started_at"] = (created_time + timedelta(seconds=random.randint(1, 60))).isoformat()
            
            jobs.append(job)
        
        # Sort by created_at descending (newest first)
        jobs.sort(key=lambda x: x["created_at"], reverse=True)
        return jobs
    
    async def get_queue_data(self) -> Dict[str, Any]:
        """Generate queue data"""
        return {
            "depth": random.randint(0, 25),
            "processing": random.randint(0, 15),
            "throughput": {
                "jobs_per_hour": random.randint(10, 100),
                "avg_processing_time": random.randint(60, 300)
            }
        }
    
    async def get_agents_data(self) -> Dict[str, Any]:
        """Generate agents data"""
        agents = []
        for i in range(random.randint(3, 8)):
            agents.append({
                "id": f"agent_{i+1}",
                "name": f"Agent {i+1}",
                "status": random.choice(["active", "idle", "busy", "offline"]),
                "uptime": random.randint(3600, 86400),
                "jobs_completed": random.randint(10, 100),
                "last_seen": datetime.now().isoformat()
            })
        
        return {
            "agents": agents,
            "total": len(agents),
            "active": len([a for a in agents if a["status"] == "active"]),
            "busy": len([a for a in agents if a["status"] == "busy"])
        }
    
    async def get_system_data(self) -> Dict[str, Any]:
        """Generate system data"""
        return {
            "cpu_usage": random.randint(20, 80),
            "memory_usage": random.randint(30, 90),
            "disk_usage": random.randint(40, 85),
            "uptime": random.randint(86400, 604800),
            "status": "healthy"
        }
    
    async def get_analytics_data(self) -> Dict[str, Any]:
        """Generate analytics data"""
        return {
            "performance": {
                "success_rate": round(random.uniform(85.0, 99.0), 2),
                "avg_processing_time": random.randint(60, 300),
                "throughput_trend": "increasing"
            },
            "trends": {
                "daily_jobs": [random.randint(20, 100) for _ in range(7)],
                "hourly_jobs": [random.randint(0, 15) for _ in range(24)]
            }
        }

    # Additional methods expected by admin_ssot route
    def get_agents_workers_data(self) -> Dict[str, Any]:
        """Get agents/workers data (sync version)"""
        return {
            "agents": [],
            "workers": [],
            "total": 0
        }
    
    def get_logs_data(self) -> Dict[str, Any]:
        """Get logs data (sync version)"""
        return {
            "logs": [],
            "total": 0
        }
    
    def get_system_control_data(self) -> Dict[str, Any]:
        """Get system control data (sync version)"""
        return {
            "controls": {},
            "status": "healthy"
        }
    
    def get_configuration_data(self) -> Dict[str, Any]:
        """Get configuration data (sync version)"""
        return {
            "config": {},
            "version": "1.0.0"
        }

    # Async versions for the route
    async def _get_dashboard_data_async(self) -> Dict[str, Any]:
        """Async version of dashboard data"""
        return await self.get_dashboard_data()
    
    async def _get_queue_data_async(self) -> Dict[str, Any]:
        """Async version of queue data"""
        return await self.get_queue_data()
    
    async def _get_analytics_data_async(self, time_range: str = "24h") -> Dict[str, Any]:
        """Async version of analytics data with time range"""
        data = await self.get_analytics_data()
        data["time_range"] = time_range
        return data
    
    async def _get_agents_workers_data_async(self) -> Dict[str, Any]:
        """Async version of agents/workers data"""
        return await self.get_agents_data()
    
    async def _get_logs_data_async(self, filters: Dict = None) -> Dict[str, Any]:
        """Async version of logs data with filters"""
        return {
            "logs": [],
            "total": 0,
            "filters": filters or {}
        }
    
    async def _get_system_control_data_async(self) -> Dict[str, Any]:
        """Async version of system control data"""
        return await self.get_system_data()
    
    async def _get_configuration_data_async(self) -> Dict[str, Any]:
        """Async version of configuration data"""
        return {
            "config": {},
            "version": "1.0.0"
        }

# Global instance
admin_data_manager = AdminDataManager()