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
                INSERT INTO boards (organization_id, owner_id, name, project_key)
                VALUES ($1, $2, $3, $4) RETURNING id
                """,
                organization_id, owner_id, board_in.name, project_key
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
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        rows = await conn.fetch(
            "SELECT * FROM v_boards_canonical WHERE organization_id = $1 AND can_view_board($2, id)",
            current_user["organization_id"], current_user["id"]
        )
        return DataEnvelope(data=[CanonicalBoardResponse(**dict(row)) for row in rows])
    except Exception as e:
        logger.error(f"Error getting user boards: {e}")
        raise HTTPException(status_code=400, detail="An unexpected error occurred")

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
