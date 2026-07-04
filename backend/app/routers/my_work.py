import logging
import asyncpg
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas.my_work import MyWorkSummaryResponse
from app.schemas.task import CanonicalTaskResponse
from app.schemas.common import DataEnvelope
from app.auth.dependencies import get_current_user
from app.database.connection import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["My Work"])

@router.get("/my-work/summary", response_model=DataEnvelope[MyWorkSummaryResponse])
async def get_my_work_summary(
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        user_id = current_user["id"]
        
        # We can query v_tasks_canonical
        summary_query = """
        SELECT
            COUNT(*) AS assigned,
            COUNT(*) FILTER (WHERE due_date::date = CURRENT_DATE AND is_completed = false) AS due_today,
            COUNT(*) FILTER (WHERE due_date::date < CURRENT_DATE AND is_completed = false) AS overdue,
            COUNT(*) FILTER (WHERE is_completed = true AND completed_at >= date_trunc('week', CURRENT_TIMESTAMP)) AS completed_this_week
        FROM v_tasks_canonical
        WHERE assigned_to = $1
        """
        
        row = await conn.fetchrow(summary_query, user_id)
        
        data = MyWorkSummaryResponse(
            assigned=row["assigned"] or 0,
            due_today=row["due_today"] or 0,
            overdue=row["overdue"] or 0,
            completed_this_week=row["completed_this_week"] or 0
        )
        return DataEnvelope(data=data)
    except Exception as e:
        logger.error(f"Error getting my work summary: {e}")
        raise HTTPException(status_code=400, detail="An unexpected error occurred")

@router.get("/my-work/tasks", response_model=DataEnvelope[List[CanonicalTaskResponse]])
async def get_my_work_tasks(
    due: Optional[str] = Query('all', description="Filter by due date"),
    sort: Optional[str] = Query('due', description="Sort by field"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        query = "SELECT * FROM v_tasks_canonical WHERE assigned_to = $1"
        args = [current_user["id"]]
        
        if due == 'today':
            query += " AND due_date::date = CURRENT_DATE AND is_completed = false"
        elif due == 'overdue':
            query += " AND due_date::date < CURRENT_DATE AND is_completed = false"
        elif due == 'upcoming':
            query += " AND due_date::date > CURRENT_DATE AND is_completed = false"
            
        if sort == 'due':
            query += " ORDER BY due_date ASC NULLS LAST"
        elif sort == 'priority':
            # Basic sort, in reality priority is enum, but here we can just order by it
            query += " ORDER BY priority DESC NULLS LAST"
        else:
            query += " ORDER BY created_at DESC"
            
        # Paging
        args.append(limit)
        query += f" LIMIT ${len(args)}"
        args.append(offset)
        query += f" OFFSET ${len(args)}"
        
        rows = await conn.fetch(query, *args)
        
        return DataEnvelope(data=[CanonicalTaskResponse(**dict(row)) for row in rows])
    except Exception as e:
        logger.error(f"Error getting my work tasks: {e}")
        raise HTTPException(status_code=400, detail=str(e))
