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
                    """
                    INSERT INTO task_comments (task_id, user_id, parent_comment_id, content)
                    VALUES ($1, $2, $3, $4) RETURNING id
                    """,
                    task_id, current_user["id"], comment_in.parent_comment_id, comment_in.content
                )

                activity_id = await self.conn.fetchval(
                    """
                    INSERT INTO activities (organization_id, entity_type, entity_id, user_id, activity_type, new_value)
                    VALUES ($1, 'COMMENT', $2, $3, 'COMMENT_ADDED', $4) RETURNING id
                    """,
                    current_user["organization_id"], task_id, current_user["id"], '{"content": "New comment added"}'
                )

                task_row = await self.conn.fetchrow("SELECT * FROM v_tasks_canonical WHERE id = $1", task_id)
                parent_user = None

                if comment_in.parent_comment_id:
                    parent_user = await self.conn.fetchrow(
                        """
                        SELECT u.id, u.email, u.first_name 
                        FROM task_comments c 
                        JOIN users u ON c.user_id = u.id 
                        WHERE c.id = $1
                        """,
                        comment_in.parent_comment_id
                    )
                    if parent_user and parent_user["id"] != current_user["id"]:
                        if not task_row or parent_user["id"] != task_row["assigned_to"]:
                            await self.conn.execute(
                                "INSERT INTO notifications (user_id, activity_id) VALUES ($1, $2)",
                                parent_user["id"], activity_id
                            )

                row = await self.conn.fetchrow(
                    """
                    SELECT c.*, u.first_name as user_first_name, u.last_name as user_last_name, u.avatar_url as user_avatar_url, u.email as user_email
                    FROM task_comments c
                    JOIN users u ON c.user_id = u.id
                    WHERE c.id = $1
                    """,
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
                SELECT c.*, u.first_name as user_first_name, u.last_name as user_last_name, u.avatar_url as user_avatar_url, u.email as user_email
                FROM task_comments c
                JOIN users u ON c.user_id = u.id
                WHERE c.task_id = $1 AND c.deleted_at IS NULL
                ORDER BY c.created_at ASC
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
            row = await self.conn.fetchrow(
                """
                SELECT c.user_id, t.board_id, b.organization_id 
                FROM task_comments c
                JOIN tasks t ON c.task_id = t.id
                JOIN boards b ON t.board_id = b.id
                WHERE c.id = $1 AND c.deleted_at IS NULL
                """,
                comment_id
            )
            if not row:
                raise HTTPException(status_code=404, detail="Comment not found")
                
            if row["organization_id"] != current_user["organization_id"]:
                raise HTTPException(status_code=403, detail="Access denied")

            if row["user_id"] != current_user["id"] and current_user.get("role") not in ("SUPER_ADMIN", "MANAGER"):
                raise HTTPException(status_code=403, detail="Not authorized to delete this comment")

            async with self.conn.transaction():
                await self.conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(current_user["id"]))
                await self.conn.execute("UPDATE task_comments SET deleted_at = CURRENT_TIMESTAMP WHERE id = $1", comment_id)
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Unexpected error: {e}')
            raise HTTPException(status_code=400, detail='An unexpected error occurred')