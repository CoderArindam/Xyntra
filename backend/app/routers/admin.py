import json
import logging
import asyncpg
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.admin import UserCreateAdmin, UserRoleUpdate, AdminUserResponse, AdminBoardResponse, BoardMemberAssign, AdminBoardMemberResponse
from app.auth.permissions import require_super_admin
from app.auth.password import get_password_hash
from app.database.connection import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

VALID_ROLES = {"MEMBER", "MANAGER", "SUPER_ADMIN"}
VALID_BOARD_PERMISSIONS = {"VIEWER", "EDITOR", "OWNER"}

@router.get("/users", response_model=List[AdminUserResponse])
async def get_all_users(
    current_user: dict = Depends(require_super_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        result = await conn.fetchval(
            "SELECT admin_get_all_users($1)",
            current_user["organization_id"],
        )
        users_data = json.loads(result) if isinstance(result, str) else result
        return users_data
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

@router.post("/users", response_model=AdminUserResponse)
async def create_user(
    user_in: UserCreateAdmin,
    current_user: dict = Depends(require_super_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    hashed_password = get_password_hash(user_in.password)
    try:
        result = await conn.fetchval(
            "SELECT admin_create_user($1, $2, $3, $4)",
            user_in.email,
            hashed_password,
            user_in.role,
            current_user["organization_id"],
        )
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create user")

        user_data = json.loads(result) if isinstance(result, str) else result
        return user_data
    except asyncpg.exceptions.RaiseError as e:
        if "already exists" in str(e):
            raise HTTPException(status_code=400, detail="Email already registered")
        logger.error(f"PostgreSQL RaiseError in admin create_user: {e}")
        raise HTTPException(status_code=400, detail="An unexpected error occurred")
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

@router.patch("/users/{user_id}/role", response_model=AdminUserResponse)
async def update_user_role(
    user_id: int,
    role_in: UserRoleUpdate,
    current_user: dict = Depends(require_super_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    if role_in.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(sorted(VALID_ROLES))}")

    try:
        result = await conn.fetchval(
            "SELECT admin_update_user_role($1, $2, $3)",
            user_id,
            role_in.role,
            current_user["organization_id"],
        )
        if not result:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = json.loads(result) if isinstance(result, str) else result
        return user_data
    except asyncpg.exceptions.RaiseError as e:
        logger.error(f"PostgreSQL RaiseError in update_user_role: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: dict = Depends(require_super_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    if current_user["id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    try:
        result = await conn.fetchval(
            "SELECT admin_delete_user($1, $2)",
            user_id,
            current_user["organization_id"],
        )
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        return None
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

@router.get("/boards", response_model=List[AdminBoardResponse])
async def get_all_boards(
    current_user: dict = Depends(require_super_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        result = await conn.fetchval(
            "SELECT admin_get_all_boards($1)",
            current_user["organization_id"],
        )
        boards_data = json.loads(result) if isinstance(result, str) else result
        return boards_data
    except Exception as e:
        logger.error(f"Error getting all boards: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

@router.post("/boards/{board_id}/members", status_code=status.HTTP_201_CREATED)
async def assign_user(
    board_id: int,
    assign_in: BoardMemberAssign,
    current_user: dict = Depends(require_super_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    if assign_in.permission not in VALID_BOARD_PERMISSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid permission. Must be one of: {', '.join(sorted(VALID_BOARD_PERMISSIONS))}")

    try:
        await conn.execute(
            "SELECT assign_user_to_board($1, $2, $3, $4)",
            current_user["id"],
            board_id,
            assign_in.user_id,
            assign_in.permission
        )
        return {"message": "User assigned to board"}
    except asyncpg.exceptions.RaiseError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except asyncpg.exceptions.ForeignKeyViolationError:
        raise HTTPException(status_code=404, detail="Board or User not found")
    except Exception as e:
        logger.error(f"Error assigning user to board: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

@router.delete("/boards/{board_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(
    board_id: int,
    user_id: int,
    current_user: dict = Depends(require_super_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        result = await conn.fetchval(
            "SELECT remove_user_from_board($1, $2)",
            board_id,
            user_id
        )
        if not result:
            raise HTTPException(status_code=404, detail="User not found on this board")
        return None
    except Exception as e:
        logger.error(f"Error removing user from board: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

@router.get("/boards/{board_id}/members", response_model=List[AdminBoardMemberResponse])
async def get_board_members_admin(
    board_id: int,
    current_user: dict = Depends(require_super_admin),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        result = await conn.fetchval(
            "SELECT get_board_members($1)",
            board_id
        )
        members_data = json.loads(result) if isinstance(result, str) else result
        return members_data
    except Exception as e:
        logger.error(f"Error getting board members: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
