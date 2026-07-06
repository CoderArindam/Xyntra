import json
import logging
import asyncpg
from fastapi import HTTPException
from app.schemas.attachments import AttachmentCreate

logger = logging.getLogger(__name__)

class AttachmentService:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def create_attachment(self, task_id: int, attachment_in: AttachmentCreate, current_user: dict):
        try:
            board_org_id = await self.conn.fetchval(
                "SELECT b.organization_id FROM boards b JOIN tasks t ON b.id = t.board_id WHERE t.id = $1", 
                task_id
            )
            if not board_org_id or board_org_id != current_user["organization_id"]:
                raise HTTPException(status_code=403, detail="Task not found or access denied")

            result = await self.conn.fetchval(
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
            logger.error(f'Unexpected error: {e}')
            raise HTTPException(status_code=400, detail='An unexpected error occurred')

    async def get_task_attachments(self, task_id: int, current_user: dict):
        try:
            board_org_id = await self.conn.fetchval(
                "SELECT b.organization_id FROM boards b JOIN tasks t ON b.id = t.board_id WHERE t.id = $1", 
                task_id
            )
            if not board_org_id or board_org_id != current_user["organization_id"]:
                raise HTTPException(status_code=403, detail="Task not found or access denied")

            result = await self.conn.fetchval(
                "SELECT get_task_attachments($1)",
                task_id
            )
            return json.loads(result) if isinstance(result, str) else result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Unexpected error: {e}')
            raise HTTPException(status_code=400, detail='An unexpected error occurred')