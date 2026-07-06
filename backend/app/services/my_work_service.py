import logging
from typing import List, Optional
import asyncpg
from fastapi import HTTPException

from app.schemas.my_work import MyWorkSummaryResponse
from app.schemas.task import CanonicalTaskResponse

logger = logging.getLogger(__name__)

class MyWorkService:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def get_my_work_summary(self, current_user: dict) -> MyWorkSummaryResponse:
        try:
            user_id = current_user["id"]
            summary_query = """
            SELECT
                COUNT(*) AS assigned,
                COUNT(*) FILTER (WHERE due_date::date = CURRENT_DATE AND is_completed = false) AS due_today,
                COUNT(*) FILTER (WHERE due_date::date < CURRENT_DATE AND is_completed = false) AS overdue,
                COUNT(*) FILTER (WHERE is_completed = true AND completed_at >= date_trunc('week', CURRENT_TIMESTAMP)) AS completed_this_week
            FROM v_tasks_canonical
            WHERE assigned_to = $1
            """
            
            row = await self.conn.fetchrow(summary_query, user_id)
            
            return MyWorkSummaryResponse(
                assigned=row["assigned"] or 0,
                due_today=row["due_today"] or 0,
                overdue=row["overdue"] or 0,
                completed_this_week=row["completed_this_week"] or 0
            )
        except Exception as e:
            logger.error(f"Error getting my work summary: {e}")
            raise HTTPException(status_code=400, detail="An unexpected error occurred")

    async def get_my_work_tasks(self, due: Optional[str], sort: Optional[str], limit: int, offset: int, current_user: dict) -> List[CanonicalTaskResponse]:
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
                query += " ORDER BY priority DESC NULLS LAST"
            else:
                query += " ORDER BY created_at DESC"
                
            args.append(limit)
            query += f" LIMIT ${len(args)}"
            args.append(offset)
            query += f" OFFSET ${len(args)}"
            
            rows = await self.conn.fetch(query, *args)
            return [CanonicalTaskResponse(**dict(row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting my work tasks: {e}")
            raise HTTPException(status_code=400, detail=str(e))