"""
Clean Agents routes - Admin duplicates removed
Only user endpoints remain to eliminate duplicate chaos
"""

from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, Optional
from services.agents_service import AgentsService
import logging

logger = logging.getLogger("agentos.api.routes.agents")

# Create service instance
agents_service = AgentsService()

# Single router - user endpoints only (admin can use these too)
user_router = APIRouter(prefix="/api/agents", tags=["agents"])

# === USER ENDPOINTS (CLEAN) ===

@user_router.get("")
async def list_agents(category: Optional[str] = None) -> Dict[str, Any]:
    """List all available agents"""
    try:
        return agents_service.list_agents(category=category, is_admin=False)
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@user_router.get("/{agent_name}")
async def get_agent_info(agent_name: str) -> Dict[str, Any]:
    """Get detailed information about a specific agent"""
    try:
        return agents_service.get_agent_info(agent_name, is_admin=False)
    except Exception as e:
        logger.error(f"Failed to get agent info for {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@user_router.post("/{agent_name}/execute")
async def execute_agent(agent_name: str, params: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Execute a specific agent with given parameters"""
    try:
        return agents_service.execute_agent(agent_name, params, is_admin=False)
    except Exception as e:
        logger.error(f"Failed to execute agent {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@user_router.get("/{agent_name}/status")
async def get_agent_status(agent_name: str) -> Dict[str, Any]:
    """Get current status of a specific agent"""
    try:
        return agents_service.get_agent_status(agent_name, is_admin=False)
    except Exception as e:
        logger.error(f"Failed to get agent status for {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@user_router.get("/{agent_name}/logs")
async def get_agent_logs(agent_name: str, limit: int = 100) -> Dict[str, Any]:
    """Get logs for a specific agent"""
    try:
        return agents_service.get_agent_logs(agent_name, limit=limit, is_admin=False)
    except Exception as e:
        logger.error(f"Failed to get agent logs for {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@user_router.post("/{agent_name}/stop")
async def stop_agent(agent_name: str) -> Dict[str, Any]:
    """Stop a running agent"""
    try:
        return agents_service.stop_agent(agent_name, is_admin=False)
    except Exception as e:
        logger.error(f"Failed to stop agent {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@user_router.post("/{agent_name}/restart")
async def restart_agent(agent_name: str) -> Dict[str, Any]:
    """Restart a specific agent"""
    try:
        return agents_service.restart_agent(agent_name, is_admin=False)
    except Exception as e:
        logger.error(f"Failed to restart agent {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@user_router.get("/{agent_name}/config")
async def get_agent_config(agent_name: str) -> Dict[str, Any]:
    """Get configuration for a specific agent"""
    try:
        return agents_service.get_agent_config(agent_name, is_admin=False)
    except Exception as e:
        logger.error(f"Failed to get agent config for {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@user_router.put("/{agent_name}/config")
async def update_agent_config(agent_name: str, config: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Update configuration for a specific agent"""
    try:
        return agents_service.update_agent_config(agent_name, config, is_admin=False)
    except Exception as e:
        logger.error(f"Failed to update agent config for {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@user_router.get("/{agent_name}/metrics")
async def get_agent_metrics(agent_name: str) -> Dict[str, Any]:
    """Get performance metrics for a specific agent"""
    try:
        return agents_service.get_agent_metrics(agent_name, is_admin=False)
    except Exception as e:
        logger.error(f"Failed to get agent metrics for {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@user_router.get("/{agent_name}/health")
async def get_agent_health(agent_name: str) -> Dict[str, Any]:
    """Get health status for a specific agent"""
    try:
        return agents_service.get_agent_health(agent_name, is_admin=False)
    except Exception as e:
        logger.error(f"Failed to get agent health for {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@user_router.post("/{agent_name}/test")
async def test_agent(agent_name: str, test_params: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Test a specific agent with test parameters"""
    try:
        return agents_service.test_agent(agent_name, test_params, is_admin=False)
    except Exception as e:
        logger.error(f"Failed to test agent {agent_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
