import logging
from typing import List, Tuple, Optional, Dict
import asyncpg
from fastapi import HTTPException

from app.schemas.comments import CommentCreate, CommentResponse

logger = logging.getLogger(__name__)

class CommentService:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def create_comment(self, task_id: int, comment_in: CommentCreate, current_user: dict) -> Tuple[CommentResponse, Optional[Dict], Optional[Dict]]:
        try:
            has_access = await self.conn.fetchval("SELECT can_view_task($1, $2)", current_user["id"], task_id)
            if not has_access:
                raise HTTPException(status_code=403, detail="Task not found or access denied")

            async with self.conn.transaction():
                await self.conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(current_user["id"]))
                comment_id = await self.conn.fetchval(
                    "SELECT fn_create_comment($1, $2, $3, $4, $5)",
                    task_id, current_user["id"], comment_in.parent_comment_id, comment_in.content, current_user["organization_id"]
                )

                task_row = await self.conn.fetchrow("SELECT * FROM v_tasks_canonical WHERE id = $1", task_id)
                parent_user = None

                if comment_in.parent_comment_id:
                    parent_user = await self.conn.fetchrow(
                        """
                        SELECT u.id, u.email, u.first_name 
                        FROM v_comments_canonical c 
                        JOIN users u ON c.user_id = u.id 
                        WHERE c.id = $1
                        """,
                        comment_in.parent_comment_id
                    )

                row = await self.conn.fetchrow(
                    "SELECT * FROM v_comments_canonical WHERE id = $1",
                    comment_id
                )

                return CommentResponse(**dict(row)), dict(task_row) if task_row else None, dict(parent_user) if parent_user else None
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Unexpected error: {e}')
            raise HTTPException(status_code=400, detail='An unexpected error occurred')

    async def get_task_comments(self, task_id: int, current_user: dict) -> List[CommentResponse]:
        try:
            has_access = await self.conn.fetchval("SELECT can_view_task($1, $2)", current_user["id"], task_id)
            if not has_access:
                raise HTTPException(status_code=403, detail="Task not found or access denied")

            rows = await self.conn.fetch(
                """
                SELECT * FROM v_comments_canonical
                WHERE task_id = $1
                ORDER BY created_at ASC
                """,
                task_id
            )
            return [CommentResponse(**dict(row)) for row in rows]
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Unexpected error: {e}')
            raise HTTPException(status_code=400, detail='An unexpected error occurred')

    async def delete_comment(self, comment_id: int, current_user: dict):
        try:
            async with self.conn.transaction():
                await self.conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(current_user["id"]))
                await self.conn.execute(
                    "SELECT fn_delete_comment($1, $2, $3, $4)",
                    comment_id, current_user["id"], current_user.get("role", "MEMBER"), current_user["organization_id"]
                )
        except HTTPException:
            raise
        except Exception as e:
            err_msg = str(e)
            logger.error(f'Error deleting comment: {err_msg}')
            if 'Comment not found' in err_msg:
                raise HTTPException(status_code=404, detail="Comment not found")
            elif 'Access denied' in err_msg or 'Not authorized' in err_msg:
                raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
            raise HTTPException(status_code=400, detail=err_msg if isinstance(e, asyncpg.exceptions.PostgresError) else 'An unexpected error occurred')