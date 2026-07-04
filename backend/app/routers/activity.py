import logging
import asyncpg
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from app.auth.dependencies import get_current_user
from app.database.connection import get_db_connection
from app.schemas.activity import CanonicalActivityResponse
from app.schemas.common import DataEnvelope, MetaResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Activity"])

@router.get("/tasks/{task_id}/activity", response_model=DataEnvelope[List[CanonicalActivityResponse]])
async def get_task_activity_endpoint(
    task_id: int,
    cursor: Optional[int] = Query(None, description="Cursor for pagination (id)"),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        has_access = await conn.fetchval("SELECT can_view_task($1, $2)", current_user["id"], task_id)
        if not has_access:
            raise HTTPException(status_code=403, detail="Task not found or access denied")

        query = "SELECT * FROM v_activities_canonical WHERE entity_type = 'TASK' AND entity_id = $1"
        args = [task_id]
        
        if cursor is not None:
            query += " AND id < $2"
            args.append(cursor)
            
        args.append(limit + 1)
        query += f" ORDER BY id DESC LIMIT ${len(args)}"
        
        rows = await conn.fetch(query, *args)
        
        has_more = len(rows) > limit
        activities = rows[:limit]
        
        next_cursor = str(activities[-1]["id"]) if activities else None
        
        return DataEnvelope(
            data=[CanonicalActivityResponse(**dict(row)) for row in activities],
            meta=MetaResponse(cursor=next_cursor, has_more=has_more)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Unexpected error: {e}')
        raise HTTPException(status_code=400, detail='An unexpected error occurred')
