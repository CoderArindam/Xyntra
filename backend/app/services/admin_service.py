import json
import logging
import asyncpg
from typing import List
from fastapi import HTTPException
from app.schemas.admin import UserCreateAdmin, UserRoleUpdate, BoardMemberAssign
from app.auth.password import get_password_hash

logger = logging.getLogger(__name__)

VALID_ROLES = {"MEMBER", "MANAGER", "SUPER_ADMIN"}
VALID_BOARD_PERMISSIONS = {"VIEWER", "EDITOR", "OWNER"}

class AdminService:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def get_all_users(self, current_user: dict) -> List[dict]:
        try:
            result = await self.conn.fetchval(
                "SELECT admin_get_all_users($1)",
                current_user["organization_id"],
            )
            return json.loads(result) if isinstance(result, str) else result
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred")

    async def create_user(self, user_in: UserCreateAdmin, current_user: dict) -> dict:
        hashed_password = get_password_hash(user_in.password)
        try:
            result = await self.conn.fetchval(
                "SELECT admin_create_user($1, $2, $3, $4)",
                user_in.email,
                hashed_password,
                user_in.role,
                current_user["organization_id"],
            )
            if not result:
                raise HTTPException(status_code=500, detail="Failed to create user")

            return json.loads(result) if isinstance(result, str) else result
        except asyncpg.exceptions.RaiseError as e:
            if "already exists" in str(e):
                raise HTTPException(status_code=400, detail="Email already registered")
            logger.error(f"PostgreSQL RaiseError in admin create_user: {e}")
            raise HTTPException(status_code=400, detail="An unexpected error occurred")
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred")

    async def update_user_role(self, user_id: int, role_in: UserRoleUpdate, current_user: dict) -> dict:
        if role_in.role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(sorted(VALID_ROLES))}")

        try:
            result = await self.conn.fetchval(
                "SELECT admin_update_user_role($1, $2, $3)",
                user_id,
                role_in.role,
                current_user["organization_id"],
            )
            if not result:
                raise HTTPException(status_code=404, detail="User not found")

            return json.loads(result) if isinstance(result, str) else result
        except asyncpg.exceptions.RaiseError as e:
            logger.error(f"PostgreSQL RaiseError in update_user_role: {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error updating user role: {e}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred")

    async def delete_user(self, user_id: int, current_user: dict):
        if current_user["id"] == user_id:
            raise HTTPException(status_code=400, detail="Cannot delete yourself")

        try:
            result = await self.conn.fetchval(
                "SELECT admin_delete_user($1, $2)",
                user_id,
                current_user["organization_id"],
            )
            if not result:
                raise HTTPException(status_code=404, detail="User not found")
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred")

    async def get_all_boards(self, current_user: dict) -> List[dict]:
        try:
            result = await self.conn.fetchval(
                "SELECT admin_get_all_boards($1)",
                current_user["organization_id"],
            )
            return json.loads(result) if isinstance(result, str) else result
        except Exception as e:
            logger.error(f"Error getting all boards: {e}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred")

    async def assign_user(self, board_id: int, assign_in: BoardMemberAssign, current_user: dict):
        if assign_in.permission not in VALID_BOARD_PERMISSIONS:
            raise HTTPException(status_code=400, detail=f"Invalid permission. Must be one of: {', '.join(sorted(VALID_BOARD_PERMISSIONS))}")

        try:
            await self.conn.execute(
                "SELECT assign_user_to_board($1, $2, $3, $4)",
                current_user["id"],
                board_id,
                assign_in.user_id,
                assign_in.permission
            )
        except asyncpg.exceptions.RaiseError as e:
            raise HTTPException(status_code=403, detail=str(e))
        except asyncpg.exceptions.ForeignKeyViolationError:
            raise HTTPException(status_code=404, detail="Board or User not found")
        except Exception as e:
            logger.error(f"Error assigning user to board: {e}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred")

    async def remove_user(self, board_id: int, user_id: int):
        try:
            result = await self.conn.fetchval(
                "SELECT remove_user_from_board($1, $2)",
                board_id,
                user_id
            )
            if not result:
                raise HTTPException(status_code=404, detail="User not found on this board")
        except Exception as e:
            logger.error(f"Error removing user from board: {e}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred")

    async def get_board_members_admin(self, board_id: int) -> List[dict]:
        try:
            result = await self.conn.fetchval(
                "SELECT get_board_members($1)",
                board_id
            )
            return json.loads(result) if isinstance(result, str) else result
        except Exception as e:
            logger.error(f"Error getting board members: {e}")
            raise HTTPException(status_code=500, detail="An unexpected error occurred")