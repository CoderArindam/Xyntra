import logging
from typing import List, Optional
import asyncpg
from fastapi import HTTPException
from app.schemas.activity import CanonicalActivityResponse
from app.schemas.common import MetaResponse

logger = logging.getLogger(__name__)

class ActivityService:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def get_task_activity(self, task_id: int, cursor: Optional[int], limit: int, current_user: dict):
        try:
            has_access = await self.conn.fetchval("SELECT can_view_task($1, $2)", current_user["id"], task_id)
            if not has_access:
                raise HTTPException(status_code=403, detail="Task not found or access denied")

            query = "SELECT * FROM v_activities_canonical WHERE entity_type = 'TASK' AND entity_id = $1"
            args = [task_id]
            
            if cursor is not None:
                query += " AND id < $2"
                args.append(cursor)
                
            args.append(limit + 1)
            query += f" ORDER BY id DESC LIMIT ${len(args)}"
            
            rows = await self.conn.fetch(query, *args)
            
            has_more = len(rows) > limit
            activities = rows[:limit]
            
            next_cursor = str(activities[-1]["id"]) if activities else None
            
            return [CanonicalActivityResponse(**dict(row)) for row in activities], MetaResponse(cursor=next_cursor, has_more=has_more)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Unexpected error: {e}')
            raise HTTPException(status_code=400, detail='An unexpected error occurred')