"""
Authorization Service
Enterprise-grade permission checking for actions
"""

from typing import List, Dict, Any, Optional, Set
from enum import Enum
import logging
from dataclasses import dataclass

logger = logging.getLogger("agentos.authorization")

class Permission(str, Enum):
    # Job permissions
    JOB_READ = "job:read"
    JOB_WRITE = "job:write"
    JOB_RETRY = "job:retry"
    JOB_CANCEL = "job:cancel"
    JOB_DELETE = "job:delete"
    JOB_PRIORITY = "job:priority"

    # Queue permissions
    QUEUE_READ = "queue:read"
    QUEUE_MANAGE = "queue:manage"
    QUEUE_CLEAR = "queue:clear"

    # Worker permissions
    WORKER_READ = "worker:read"
    WORKER_MANAGE = "worker:manage"

    # System permissions
    SYSTEM_READ = "system:read"
    SYSTEM_MANAGE = "system:manage"
    SYSTEM_BACKUP = "system:backup"
    SYSTEM_MAINTENANCE = "system:maintenance"

    # Cache permissions
    CACHE_READ = "cache:read"
    CACHE_MANAGE = "cache:manage"

    # Admin permission (overrides all)
    ADMIN = "admin"

@dataclass
class User:
    """User model for authorization"""
    id: str
    email: str
    roles: List[str]
    permissions: List[str]
    is_admin: bool = False
    is_active: bool = True

class AuthorizationService:
    """
    Service for checking user permissions for actions

    Features:
    - Role-based access control (RBAC)
    - Permission-based access control
    - Resource-level permissions
    - Admin overrides
    - Audit trail for denied access
    """

    # Role to permissions mapping
    ROLE_PERMISSIONS = {
        "admin": [Permission.ADMIN],  # Admin has all permissions
        "operator": [
            Permission.JOB_READ, Permission.JOB_WRITE, Permission.JOB_RETRY, Permission.JOB_CANCEL,
            Permission.QUEUE_READ, Permission.QUEUE_MANAGE,
            Permission.WORKER_READ, Permission.WORKER_MANAGE,
            Permission.CACHE_READ, Permission.CACHE_MANAGE,
        ],
        "supervisor": [
            Permission.JOB_READ, Permission.JOB_WRITE, Permission.JOB_RETRY, Permission.JOB_CANCEL,
            Permission.QUEUE_READ,
            Permission.WORKER_READ,
            Permission.SYSTEM_READ,
        ],
        "user": [
            Permission.JOB_READ, Permission.JOB_WRITE,  # Only own jobs
            Permission.QUEUE_READ,
            Permission.WORKER_READ,
        ],
        "readonly": [
            Permission.JOB_READ,
            Permission.QUEUE_READ,
            Permission.WORKER_READ,
            Permission.SYSTEM_READ,
            Permission.CACHE_READ,
        ]
    }

    # Action to required permissions mapping
    ACTION_PERMISSIONS = {
        "job.retry": [Permission.JOB_RETRY],
        "job.cancel": [Permission.JOB_CANCEL],
        "job.delete": [Permission.JOB_DELETE, Permission.ADMIN],  # Requires admin
        "job.priority": [Permission.JOB_PRIORITY],

        "queue.clear": [Permission.QUEUE_CLEAR, Permission.ADMIN],  # Requires admin
        "queue.pause": [Permission.QUEUE_MANAGE],
        "queue.resume": [Permission.QUEUE_MANAGE],
        "queue.drain": [Permission.QUEUE_MANAGE],

        "worker.restart": [Permission.WORKER_MANAGE],
        "worker.scale": [Permission.WORKER_MANAGE],
        "worker.pause": [Permission.WORKER_MANAGE],
        "worker.resume": [Permission.WORKER_MANAGE],

        "system.backup": [Permission.SYSTEM_BACKUP, Permission.ADMIN],
        "system.maintenance": [Permission.SYSTEM_MAINTENANCE, Permission.ADMIN],

        "cache.clear": [Permission.CACHE_MANAGE],
        "cache.warm": [Permission.CACHE_MANAGE],
    }

    def __init__(self):
        """Initialize authorization service"""
        pass

    def get_user_permissions(self, user: User) -> Set[Permission]:
        """
        Get all permissions for a user based on roles and direct permissions

        Args:
            user: User object

        Returns:
            Set of permissions
        """
        permissions = set()

        # Admin override
        if user.is_admin:
            permissions.add(Permission.ADMIN)
            return permissions

        # Add permissions from roles
        for role in user.roles:
            role_permissions = self.ROLE_PERMISSIONS.get(role, [])
            permissions.update(role_permissions)

        # Add direct permissions
        for perm in user.permissions:
            try:
                permissions.add(Permission(perm))
            except ValueError:
                logger.warning(f"Unknown permission: {perm}")

        return permissions

    def has_permission(self, user: User, permission: Permission) -> bool:
        """
        Check if user has a specific permission

        Args:
            user: User object
            permission: Permission to check

        Returns:
            True if user has permission
        """
        if not user.is_active:
            return False

        user_permissions = self.get_user_permissions(user)

        # Admin has all permissions
        if Permission.ADMIN in user_permissions:
            return True

        return permission in user_permissions

    def has_any_permission(self, user: User, permissions: List[Permission]) -> bool:
        """
        Check if user has any of the specified permissions

        Args:
            user: User object
            permissions: List of permissions to check

        Returns:
            True if user has at least one permission
        """
        if not user.is_active:
            return False

        user_permissions = self.get_user_permissions(user)

        # Admin has all permissions
        if Permission.ADMIN in user_permissions:
            return True

        return any(perm in user_permissions for perm in permissions)

    def has_all_permissions(self, user: User, permissions: List[Permission]) -> bool:
        """
        Check if user has all specified permissions

        Args:
            user: User object
            permissions: List of permissions to check

        Returns:
            True if user has all permissions
        """
        if not user.is_active:
            return False

        user_permissions = self.get_user_permissions(user)

        # Admin has all permissions
        if Permission.ADMIN in user_permissions:
            return True

        return all(perm in user_permissions for perm in permissions)

    async def check_permissions(
        self,
        user: User,
        action: str,
        payload: Dict[str, Any],
        required_permissions: Optional[List[str]] = None
    ) -> bool:
        """
        Check if user can execute an action

        Args:
            user: User attempting the action
            action: Action being attempted
            payload: Action payload (for resource-level checks)
            required_permissions: Override required permissions

        Returns:
            True if authorized, False otherwise
        """
        try:
            if not user.is_active:
                logger.info(f"Inactive user attempted action: {user.id}")
                return False

            # Get required permissions for action
            if required_permissions:
                # Use provided permissions (convert strings to Permission enum)
                perms = []
                for perm_str in required_permissions:
                    try:
                        if perm_str == "admin":
                            perms.append(Permission.ADMIN)
                        else:
                            perms.append(Permission(perm_str))
                    except ValueError:
                        logger.warning(f"Unknown permission in requirements: {perm_str}")
            else:
                # Use action-based permissions
                perm_strings = self.ACTION_PERMISSIONS.get(action, [Permission.ADMIN])
                perms = [Permission(p) if isinstance(p, str) else p for p in perm_strings]

            # Check if user has any required permission
            has_permission = self.has_any_permission(user, perms)

            if has_permission:
                # Additional resource-level checks
                resource_check = await self._check_resource_permissions(user, action, payload)
                if not resource_check:
                    logger.info(
                        "Resource permission denied",
                        extra={
                            "user_id": user.id,
                            "action": action,
                            "payload": payload
                        }
                    )
                    return False

            return has_permission

        except Exception as e:
            logger.error(f"Authorization check failed: {e}")
            # Fail secure - deny access on errors
            return False

    async def _check_resource_permissions(
        self,
        user: User,
        action: str,
        payload: Dict[str, Any]
    ) -> bool:
        """
        Check resource-level permissions (e.g., user can only modify their own jobs)

        Args:
            user: User attempting the action
            action: Action being attempted
            payload: Action payload

        Returns:
            True if authorized at resource level
        """
        try:
            # Job-related actions
            if action.startswith("job."):
                job_id = payload.get("job_id")
                if job_id:
                    # Check if user owns the job (unless they're admin/operator)
                    user_permissions = self.get_user_permissions(user)
                    if Permission.ADMIN not in user_permissions and "operator" not in user.roles:
                        # TODO: Implement job ownership check
                        # job = await JobService.get_job(job_id)
                        # return job.user_id == user.id
                        pass

            # Queue actions - only admins and operators
            if action.startswith("queue."):
                user_permissions = self.get_user_permissions(user)
                if Permission.ADMIN not in user_permissions and "operator" not in user.roles:
                    return False

            # Worker actions - only admins and operators
            if action.startswith("worker."):
                user_permissions = self.get_user_permissions(user)
                if Permission.ADMIN not in user_permissions and "operator" not in user.roles:
                    return False

            # System actions - admin only
            if action.startswith("system."):
                user_permissions = self.get_user_permissions(user)
                return Permission.ADMIN in user_permissions

            return True

        except Exception as e:
            logger.error(f"Resource permission check failed: {e}")
            # Fail secure
            return False

    def get_action_permissions(self, action: str) -> List[Permission]:
        """
        Get required permissions for an action

        Args:
            action: Action name

        Returns:
            List of required permissions
        """
        perm_strings = self.ACTION_PERMISSIONS.get(action, [Permission.ADMIN])
        return [Permission(p) if isinstance(p, str) else p for p in perm_strings]

    def can_user_execute_action(self, user: User, action: str) -> bool:
        """
        Quick check if user can execute an action (without resource checks)

        Args:
            user: User object
            action: Action name

        Returns:
            True if user has required permissions
        """
        required_perms = self.get_action_permissions(action)
        return self.has_any_permission(user, required_perms)

    def get_user_role_summary(self, user: User) -> Dict[str, Any]:
        """
        Get summary of user's roles and permissions

        Args:
            user: User object

        Returns:
            Summary dictionary
        """
        user_permissions = self.get_user_permissions(user)

        return {
            "user_id": user.id,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
            "roles": user.roles,
            "permissions": [p.value for p in user_permissions],
            "can_execute_actions": {
                action: self.can_user_execute_action(user, action)
                for action in self.ACTION_PERMISSIONS.keys()
            }
        }

# Global instance
authorization_service = AuthorizationService()
