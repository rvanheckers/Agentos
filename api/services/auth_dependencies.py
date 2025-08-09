"""
Auth Dependencies - Mock authenticatie voor AgentOS development

Tijdelijke authenticatie dependencies met hardcoded users voor development.
TODO: Vervangen door echte JWT authenticatie in productie.
Gebruikt door refactored routes voor get_current_user en get_admin_user.
"""
from fastapi import HTTPException, Header
from typing import Optional, Dict

# Mock users for development
MOCK_USERS = {
    "user1": {"id": "user1", "email": "user@example.com", "is_admin": False},
    "admin1": {"id": "admin1", "email": "admin@example.com", "is_admin": True}
}

async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict:
    """
    Get current user from authorization header
    In production, this would validate JWT tokens
    For development, returns mock user
    """
    # For development, return a default user
    # In production, decode JWT token here
    return MOCK_USERS["user1"]

async def get_admin_user(authorization: Optional[str] = Header(None)) -> Dict:
    """
    Get admin user from authorization header
    Raises 403 if not admin
    """
    # For development, return admin user
    # In production, validate JWT and check admin role
    user = MOCK_USERS["admin1"]

    if not user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")

    return user

# Backwards compatibility
get_current_user = get_current_user
get_admin_user = get_admin_user
