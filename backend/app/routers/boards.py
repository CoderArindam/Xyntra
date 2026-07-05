import logging
import asyncpg
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.board import BoardCreate, CanonicalBoardResponse
from app.schemas.common import DataEnvelope
from app.auth.dependencies import get_current_user
from app.auth.permissions import require_manager_or_above
from app.database.connection import get_db_connection
import re

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/boards", tags=["Boards"])

def generate_project_key(name: str) -> str:
    # Basic generation: uppercase, alphanumeric, max 5 chars
    key = re.sub(r'[^A-Z0-9]', '', name.upper())
    if len(key) < 3:
        key = (key + "XXX")[:3]
    return key[:5]

@router.post("", response_model=DataEnvelope[CanonicalBoardResponse])
async def create_board(
    board_in: BoardCreate,
    current_user: dict = Depends(require_manager_or_above),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    owner_id = current_user["id"]
    organization_id = current_user["organization_id"]
    
    project_key = board_in.project_key or generate_project_key(board_in.name)

    try:
        async with conn.transaction():
            await conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(current_user["id"]))
            
            board_id = await conn.fetchval(
                """
                INSERT INTO boards (organization_id, owner_id, name, project_key, description, icon, color, cover_gradient, default_assignee_id, project_lead_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10) RETURNING id
                """,
                organization_id, owner_id, board_in.name, project_key,
                board_in.description, board_in.icon, board_in.color, board_in.cover_gradient,
                board_in.default_assignee_id, board_in.project_lead_id
            )
            
            row = await conn.fetchrow("SELECT * FROM v_boards_canonical WHERE id = $1", board_id)
            return DataEnvelope(data=CanonicalBoardResponse(**dict(row)))
    except asyncpg.exceptions.UniqueViolationError:
        raise HTTPException(status_code=400, detail="A project with this key already exists.")
    except Exception as e:
        logger.error(f"Error creating board: {e}")
        raise HTTPException(status_code=400, detail="An unexpected error occurred")

@router.get("", response_model=DataEnvelope[List[CanonicalBoardResponse]])
async def get_user_boards(
    include_archived: bool = False,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        if include_archived:
            query = "SELECT * FROM v_boards_canonical WHERE organization_id = $1 AND can_view_board($2, id)"
        else:
            query = "SELECT * FROM v_boards_canonical WHERE organization_id = $1 AND can_view_board($2, id) AND archived_at IS NULL"
            
        rows = await conn.fetch(query, current_user["organization_id"], current_user["id"])
        return DataEnvelope(data=[CanonicalBoardResponse(**dict(row)) for row in rows])
    except Exception as e:
        logger.error(f"Error getting user boards: {e}")
        raise HTTPException(status_code=400, detail="An unexpected error occurred")

from app.schemas.board import ProjectSettingsResponse, ProjectSettingsUpdate
from app.services.project_settings import ProjectSettingsService

@router.get("/{board_id}/settings", response_model=DataEnvelope[ProjectSettingsResponse])
async def get_project_settings(
    board_id: int,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    # Any member can view settings if they have access to board, but let's check basic access
    has_access = await conn.fetchval("SELECT can_view_board($1, $2)", current_user["id"], board_id)
    if not has_access:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    settings = await ProjectSettingsService.get_settings(conn, board_id)
    return DataEnvelope(data=settings)

@router.patch("/{board_id}/settings", response_model=DataEnvelope[ProjectSettingsResponse])
async def update_project_settings(
    board_id: int,
    updates: ProjectSettingsUpdate,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    # Need to be manager or above, or have specific permission (EDITOR or OWNER). Let's use can_manage_board or check roles.
    has_access = await conn.fetchval("SELECT can_manage_board($1, $2)", current_user["id"], board_id)
    if not has_access:
        role = current_user.get("role", "MEMBER")
        if role != "SUPER_ADMIN" and role != "MANAGER": # Managers can update settings too. Wait, can_manage_board includes board owners.
            raise HTTPException(status_code=403, detail="Insufficient permissions to update settings")
            
    try:
        async with conn.transaction():
            await conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(current_user["id"]))
            settings = await ProjectSettingsService.update_settings(conn, board_id, updates)
            return DataEnvelope(data=settings)
    except Exception as e:
        logger.error(f"Error updating project settings: {e}")
        raise HTTPException(status_code=400, detail="Failed to update project settings")

@router.post("/{board_id}/archive", response_model=DataEnvelope[ProjectSettingsResponse])
async def archive_project(
    board_id: int,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    has_access = await conn.fetchval("SELECT can_manage_board($1, $2)", current_user["id"], board_id)
    if not has_access:
        role = current_user.get("role", "MEMBER")
        if role != "SUPER_ADMIN":
            raise HTTPException(status_code=403, detail="Insufficient permissions to archive project")
            
    try:
        async with conn.transaction():
            await conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(current_user["id"]))
            settings = await ProjectSettingsService.archive_project(conn, board_id)
            return DataEnvelope(data=settings)
    except Exception as e:
        logger.error(f"Error archiving project: {e}")
        raise HTTPException(status_code=400, detail="Failed to archive project")

@router.delete("/{board_id}", status_code=204)
async def delete_board(
    board_id: int,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        has_access = await conn.fetchval("SELECT can_manage_board($1, $2)", current_user["id"], board_id)
        if not has_access:
            role = current_user.get("role", "MEMBER")
            if role != "SUPER_ADMIN":
                raise HTTPException(status_code=403, detail="Insufficient permissions to delete a board")

        async with conn.transaction():
            await conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(current_user["id"]))
            result = await conn.execute(
                "UPDATE boards SET deleted_at = CURRENT_TIMESTAMP WHERE id = $1 AND organization_id = $2 AND deleted_at IS NULL",
                board_id, current_user["organization_id"]
            )
            if result == "UPDATE 0":
                raise HTTPException(status_code=404, detail="Board not found")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting board: {e}")
        raise HTTPException(status_code=400, detail="An unexpected error occurred")
