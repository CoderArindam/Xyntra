from fastapi import Depends, HTTPException, status
from app.auth.dependencies import get_current_user

VALID_ROLES = {"MEMBER", "MANAGER", "SUPER_ADMIN"}


def require_super_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin privileges required"
        )
    return current_user


def require_manager_or_above(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") not in ("MANAGER", "SUPER_ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager or Super Admin privileges required"
        )
    return current_user
