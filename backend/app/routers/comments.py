import logging
import asyncpg
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.schemas.comments import CommentCreate, CommentResponse
from app.schemas.common import DataEnvelope
from app.services.notification_service import dispatch_task_email
from app.auth.dependencies import get_current_user
from app.database.connection import get_db_connection

router = APIRouter(tags=["Comments"])

@router.post("/tasks/{task_id}/comments", response_model=DataEnvelope[CommentResponse])
async def create_comment(
    task_id: int,
    comment_in: CommentCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        has_access = await conn.fetchval("SELECT can_view_task($1, $2)", current_user["id"], task_id)
        if not has_access:
            raise HTTPException(status_code=403, detail="Task not found or access denied")

        async with conn.transaction():
            await conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(current_user["id"]))
            comment_id = await conn.fetchval(
                """
                INSERT INTO task_comments (task_id, user_id, parent_comment_id, content)
                VALUES ($1, $2, $3, $4) RETURNING id
                """,
                task_id, current_user["id"], comment_in.parent_comment_id, comment_in.content
            )

            # Manual event generation since comments don't have triggers for it in 007_triggers yet
            activity_id = await conn.fetchval(
                """
                INSERT INTO activities (organization_id, entity_type, entity_id, user_id, activity_type, new_value)
                VALUES ($1, 'COMMENT', $2, $3, 'COMMENT_ADDED', $4) RETURNING id
                """,
                current_user["organization_id"], task_id, current_user["id"], '{"content": "New comment added"}'
            )

            # Fetch task data to notify the assignee
            task_row = await conn.fetchrow("SELECT * FROM v_tasks_canonical WHERE id = $1", task_id)
            actor_name = current_user.get("first_name") or current_user.get("email")

            if task_row and task_row["assigned_to"] and task_row["assigned_to"] != current_user["id"]:
                background_tasks.add_task(
                    dispatch_task_email,
                    activity_type="COMMENT_ADDED",
                    task_title=task_row["title"],
                    board_name=task_row["board_name"],
                    actor_name=actor_name,
                    assignee_email=task_row["assignee_email"],
                    assignee_name=task_row["assignee_first_name"],
                    comment=comment_in.content
                )

            # Notify parent comment author if it's a reply
            if comment_in.parent_comment_id:
                parent_user = await conn.fetchrow(
                    """
                    SELECT u.id, u.email, u.first_name 
                    FROM task_comments c 
                    JOIN users u ON c.user_id = u.id 
                    WHERE c.id = $1
                    """,
                    comment_in.parent_comment_id
                )
                if parent_user and parent_user["id"] != current_user["id"]:
                    # Insert in-app notification for parent author ONLY if they aren't the assignee (who already got it via trigger)
                    if not task_row or parent_user["id"] != task_row["assigned_to"]:
                        await conn.execute(
                            "INSERT INTO notifications (user_id, activity_id) VALUES ($1, $2)",
                            parent_user["id"], activity_id
                        )
                        background_tasks.add_task(
                            dispatch_task_email,
                            activity_type="COMMENT_ADDED",
                            task_title=task_row["title"] if task_row else "a task",
                            board_name=task_row["board_name"] if task_row else "your board",
                            actor_name=actor_name,
                            assignee_email=parent_user["email"],
                            assignee_name=parent_user["first_name"],
                            comment=comment_in.content
                        )

            row = await conn.fetchrow(
                """
                SELECT c.*, u.first_name as user_first_name, u.last_name as user_last_name, u.avatar_url as user_avatar_url, u.email as user_email
                FROM task_comments c
                JOIN users u ON c.user_id = u.id
                WHERE c.id = $1
                """,
                comment_id
            )

            return DataEnvelope(data=CommentResponse(**dict(row)))
    except HTTPException:
        raise
    except Exception as e:
        import logging; logging.getLogger(__name__).error(f'Unexpected error: {e}')
        raise HTTPException(status_code=400, detail='An unexpected error occurred')

@router.get("/tasks/{task_id}/comments", response_model=DataEnvelope[List[CommentResponse]])
async def get_task_comments(
    task_id: int,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        has_access = await conn.fetchval("SELECT can_view_task($1, $2)", current_user["id"], task_id)
        if not has_access:
            raise HTTPException(status_code=403, detail="Task not found or access denied")

        rows = await conn.fetch(
            """
            SELECT c.*, u.first_name as user_first_name, u.last_name as user_last_name, u.avatar_url as user_avatar_url, u.email as user_email
            FROM task_comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.task_id = $1 AND c.deleted_at IS NULL
            ORDER BY c.created_at ASC
            """,
            task_id
        )
        return DataEnvelope(data=[CommentResponse(**dict(row)) for row in rows])
    except HTTPException:
        raise
    except Exception as e:
        import logging; logging.getLogger(__name__).error(f'Unexpected error: {e}')
        raise HTTPException(status_code=400, detail='An unexpected error occurred')

@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: int,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        # User can delete their own comment, or if they are SUPER_ADMIN/MANAGER in the org
        row = await conn.fetchrow(
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

        async with conn.transaction():
            await conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(current_user["id"]))
            await conn.execute("UPDATE task_comments SET deleted_at = CURRENT_TIMESTAMP WHERE id = $1", comment_id)
            
        return None
    except HTTPException:
        raise
    except Exception as e:
        import logging; logging.getLogger(__name__).error(f'Unexpected error: {e}')
        raise HTTPException(status_code=400, detail='An unexpected error occurred')
