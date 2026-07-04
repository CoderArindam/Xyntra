import json
import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from app.schemas.attachments import AttachmentCreate
from app.auth.dependencies import get_current_user
from app.database.connection import get_db_connection

router = APIRouter(tags=["Attachments"])

@router.post("/tasks/{task_id}/attachments")
async def create_attachment(
    task_id: int,
    attachment_in: AttachmentCreate,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        # Enforce organization isolation
        board_org_id = await conn.fetchval(
            "SELECT b.organization_id FROM boards b JOIN tasks t ON b.id = t.board_id WHERE t.id = $1", 
            task_id
        )
        if not board_org_id or board_org_id != current_user["organization_id"]:
            raise HTTPException(status_code=403, detail="Task not found or access denied")

        result = await conn.fetchval(
            "SELECT create_attachment($1, $2, $3, $4)",
            task_id,
            current_user["id"],
            attachment_in.file_name,
            attachment_in.file_url
        )
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create attachment")
        return json.loads(result) if isinstance(result, str) else result
    except HTTPException:
        raise
    except Exception as e:
        import logging; logging.getLogger(__name__).error(f'Unexpected error: {e}')
        raise HTTPException(status_code=400, detail='An unexpected error occurred')

@router.get("/tasks/{task_id}/attachments")
async def get_task_attachments(
    task_id: int,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        # Enforce organization isolation
        board_org_id = await conn.fetchval(
            "SELECT b.organization_id FROM boards b JOIN tasks t ON b.id = t.board_id WHERE t.id = $1", 
            task_id
        )
        if not board_org_id or board_org_id != current_user["organization_id"]:
            raise HTTPException(status_code=403, detail="Task not found or access denied")

        result = await conn.fetchval(
            "SELECT get_task_attachments($1)",
            task_id
        )
        return json.loads(result) if isinstance(result, str) else result
    except HTTPException:
        raise
    except Exception as e:
        import logging; logging.getLogger(__name__).error(f'Unexpected error: {e}')
        raise HTTPException(status_code=400, detail='An unexpected error occurred')
