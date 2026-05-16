"""Role-based access control."""

from enum import Enum
from fastapi import Depends, HTTPException, status

from auth.middleware import get_current_user
from database.models import User, UserRole


class Permission(str, Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.VIEWER: {Permission.READ},
    UserRole.ANALYST: {Permission.READ, Permission.WRITE},
    UserRole.ADMIN: {Permission.READ, Permission.WRITE, Permission.ADMIN},
}


def has_permission(user: User, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(user.role, set())


def require_roles(*roles: UserRole):
    """FastAPI dependency: user must have one of the given roles."""

    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {', '.join(r.value for r in roles)}",
            )
        return current_user

    return checker


require_admin = require_roles(UserRole.ADMIN)
require_analyst = require_roles(UserRole.ADMIN, UserRole.ANALYST)
