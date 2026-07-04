import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.auth.dependencies import get_current_user
from app.database.connection import get_db_connection
from app.schemas.common import DataEnvelope

router = APIRouter(tags=["Board Members"])

@router.get("/boards/{board_id}/members")
async def get_board_members(
    board_id: int,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    try:
        # Check permissions: user must be able to view the board
        has_access = await conn.fetchval(
            "SELECT can_view_board($1, $2)",
            current_user["id"], board_id
        )
        role = current_user.get("role", "MEMBER")
        if not has_access and role not in ("SUPER_ADMIN", "MANAGER"):
            raise HTTPException(status_code=403, detail="Not authorized to view this board")

        rows = await conn.fetch(
            "SELECT id, email, first_name, last_name, avatar_url, joined_at FROM v_board_members_canonical WHERE board_id = $1",
            board_id
        )
        
        # Format the result
        members = [dict(row) for row in rows]

        return DataEnvelope(data=members)
    except HTTPException:
        raise
    except Exception as e:
        import logging; logging.getLogger(__name__).error(f'Unexpected error in get_board_members: {e}')
        raise HTTPException(status_code=400, detail='An unexpected error occurred')
