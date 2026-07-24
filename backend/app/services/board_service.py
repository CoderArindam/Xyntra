import logging
import re
from typing import List
import asyncpg
from fastapi import HTTPException

from app.schemas.board import BoardCreate, CanonicalBoardResponse, ProjectSettingsResponse, ProjectSettingsUpdate
from app.services.project_settings import ProjectSettingsService

logger = logging.getLogger(__name__)

def generate_project_key(name: str) -> str:
    # Basic generation: uppercase, alphanumeric, max 5 chars
    key = re.sub(r'[^A-Z0-9]', '', name.upper())
    if len(key) < 3:
        key = (key + "XXX")[:3]
    return key[:5]

class BoardService:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def create_board(self, board_in: BoardCreate, current_user: dict) -> CanonicalBoardResponse:
        owner_id = current_user["id"]
        organization_id = current_user["organization_id"]
        project_key = board_in.project_key or generate_project_key(board_in.name)

        try:
            async with self.conn.transaction():
                await self.conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(current_user["id"]))
                
                board_id = await self.conn.fetchval(
                    """
                    INSERT INTO boards (organization_id, owner_id, name, project_key, description, icon, color, cover_gradient, default_assignee_id, project_lead_id)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10) RETURNING id
                    """,
                    organization_id, owner_id, board_in.name, project_key,
                    board_in.description, board_in.icon, board_in.color, board_in.cover_gradient,
                    board_in.default_assignee_id, board_in.project_lead_id
                )
                
                row = await self.conn.fetchrow("SELECT * FROM v_boards_canonical WHERE id = $1", board_id)
                return CanonicalBoardResponse(**dict(row))
        except asyncpg.exceptions.UniqueViolationError:
            raise HTTPException(status_code=400, detail="A project with this key already exists.")
        except Exception as e:
            logger.error(f"Error creating board: {e}")
            raise HTTPException(status_code=400, detail="An unexpected error occurred")

    async def get_user_boards(self, include_archived: bool, current_user: dict) -> List[CanonicalBoardResponse]:
        try:
            if include_archived:
                query = "SELECT * FROM v_boards_canonical WHERE organization_id = $1 AND can_view_board($2, id)"
            else:
                query = "SELECT * FROM v_boards_canonical WHERE organization_id = $1 AND can_view_board($2, id) AND archived_at IS NULL"
                
            rows = await self.conn.fetch(query, current_user["organization_id"], current_user["id"])
            return [CanonicalBoardResponse(**dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting user boards: {e}")
            raise HTTPException(status_code=400, detail="An unexpected error occurred")

    async def get_project_settings(self, board_id: int, current_user: dict) -> ProjectSettingsResponse:
        has_access = await self.conn.fetchval("SELECT can_view_board($1, $2)", current_user["id"], board_id)
        if not has_access:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        role = current_user.get("role", "MEMBER")
        if role not in ("SUPER_ADMIN", "MANAGER"):
            raise HTTPException(status_code=403, detail="Only Managers or Super Admins can access project settings")
        
        return await ProjectSettingsService.get_settings(self.conn, board_id)

    async def update_project_settings(self, board_id: int, updates: ProjectSettingsUpdate, current_user: dict) -> ProjectSettingsResponse:
        has_access = await self.conn.fetchval("SELECT can_manage_board($1, $2)", current_user["id"], board_id)
        if not has_access:
            role = current_user.get("role", "MEMBER")
            if role != "SUPER_ADMIN" and role != "MANAGER":
                raise HTTPException(status_code=403, detail="Insufficient permissions to update settings")
                
        try:
            async with self.conn.transaction():
                await self.conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(current_user["id"]))
                return await ProjectSettingsService.update_settings(self.conn, board_id, updates)
        except Exception as e:
            logger.error(f"Error updating project settings: {e}")
            raise HTTPException(status_code=400, detail="Failed to update project settings")

    async def archive_project(self, board_id: int, current_user: dict) -> ProjectSettingsResponse:
        has_access = await self.conn.fetchval("SELECT can_manage_board($1, $2)", current_user["id"], board_id)
        if not has_access:
            role = current_user.get("role", "MEMBER")
            if role != "SUPER_ADMIN":
                raise HTTPException(status_code=403, detail="Insufficient permissions to archive project")
                
        try:
            async with self.conn.transaction():
                await self.conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(current_user["id"]))
                return await ProjectSettingsService.archive_project(self.conn, board_id)
        except Exception as e:
            logger.error(f"Error archiving project: {e}")
            raise HTTPException(status_code=400, detail="Failed to archive project")

    async def delete_board(self, board_id: int, current_user: dict):
        try:
            has_access = await self.conn.fetchval("SELECT can_manage_board($1, $2)", current_user["id"], board_id)
            if not has_access:
                role = current_user.get("role", "MEMBER")
                if role != "SUPER_ADMIN":
                    raise HTTPException(status_code=403, detail="Insufficient permissions to delete a board")

            async with self.conn.transaction():
                await self.conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(current_user["id"]))
                result = await self.conn.execute(
                    "UPDATE boards SET deleted_at = CURRENT_TIMESTAMP WHERE id = $1 AND organization_id = $2 AND deleted_at IS NULL",
                    board_id, current_user["organization_id"]
                )
                if result == "UPDATE 0":
                    raise HTTPException(status_code=404, detail="Board not found")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting board: {e}")
            raise HTTPException(status_code=400, detail="An unexpected error occurred")

    async def get_board_members(self, board_id: int, current_user: dict) -> List[dict]:
        try:
            has_access = await self.conn.fetchval(
                "SELECT can_view_board($1, $2)",
                current_user["id"], board_id
            )
            role = current_user.get("role", "MEMBER")
            if not has_access and role not in ("SUPER_ADMIN", "MANAGER"):
                raise HTTPException(status_code=403, detail="Not authorized to view this board")

            rows = await self.conn.fetch(
                "SELECT id, email, first_name, last_name, avatar_url, joined_at FROM v_board_members_canonical WHERE board_id = $1",
                board_id
            )
            return [dict(row) for row in rows]
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Unexpected error in get_board_members: {e}')
            raise HTTPException(status_code=400, detail='An unexpected error occurred')