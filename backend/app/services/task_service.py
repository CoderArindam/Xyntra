import logging
from typing import Optional, List, Dict, Any
import asyncpg
from fastapi import HTTPException

from app.schemas.task import TaskCreate, TaskUpdate, TaskAssigneeUpdate, CanonicalTaskResponse, BoardDataResponse

logger = logging.getLogger(__name__)

class TaskService:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def create_task(self, task_in: TaskCreate, current_user: dict) -> CanonicalTaskResponse:
        role = current_user.get("role", "MEMBER")
        if role not in ("MANAGER", "SUPER_ADMIN"):
            raise HTTPException(status_code=403, detail="Only MANAGER or SUPER_ADMIN can create tasks")

        try:
            has_access = await self.conn.fetchval("SELECT can_view_board($1, $2)", current_user["id"], task_in.board_id)
            if not has_access:
                raise HTTPException(status_code=403, detail="Board not found or access denied")

            async with self.conn.transaction():
                await self.conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(current_user["id"]))
                task_id = await self.conn.fetchval(
                    """
                    INSERT INTO tasks (board_id, column_id, title, description, priority, assigned_to, created_by, due_date, reminder_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    RETURNING id
                    """,
                    task_in.board_id, task_in.column_id, task_in.title, task_in.description,
                    task_in.priority, task_in.assigned_to, current_user["id"], task_in.due_date, task_in.reminder_at
                )
                
                row = await self.conn.fetchrow("SELECT * FROM v_tasks_canonical WHERE id = $1", task_id)
                return CanonicalTaskResponse(**dict(row))
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            raise HTTPException(status_code=400, detail="An unexpected error occurred")

    async def get_board_tasks(self, board_id: int, assigned_to: Optional[int], current_user: dict) -> BoardDataResponse:
        try:
            has_access = await self.conn.fetchval("SELECT can_view_board($1, $2)", current_user["id"], board_id)
            if not has_access:
                raise HTTPException(status_code=403, detail="Board not found or access denied")

            columns_rows = await self.conn.fetch(
                "SELECT id, name, position, column_type, (column_type = 'DONE') AS is_completed FROM board_columns WHERE board_id = $1 ORDER BY position",
                board_id
            )
            
            query = "SELECT * FROM v_tasks_canonical WHERE board_id = $1"
            args = [board_id]
            
            if assigned_to is not None:
                query += " AND assigned_to = $2"
                args.append(assigned_to)
                
            tasks_rows = await self.conn.fetch(query, *args)
            
            return BoardDataResponse(
                columns=[dict(c) for c in columns_rows],
                tasks=[CanonicalTaskResponse(**dict(t)) for t in tasks_rows]
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting board tasks: {e}")
            raise HTTPException(status_code=400, detail="An unexpected error occurred")

    async def update_task(self, task_id: int, task_in: TaskUpdate, current_user: dict) -> tuple[CanonicalTaskResponse, Optional[dict], dict]:
        # Returns (updated_task, old_task_dict, new_task_dict) for notifications later
        try:
            has_access = await self.conn.fetchval("SELECT can_edit_task($1, $2)", current_user["id"], task_id)
            if not has_access:
                raise HTTPException(status_code=403, detail="Task not found or access denied")

            async with self.conn.transaction():
                await self.conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(current_user["id"]))
                
                update_fields = []
                args = []
                idx = 1
                for field, value in task_in.model_dump(exclude_unset=True).items():
                    update_fields.append(f"{field} = ${idx}")
                    args.append(value)
                    idx += 1
                    
                if not update_fields:
                    row = await self.conn.fetchrow("SELECT * FROM v_tasks_canonical WHERE id = $1", task_id)
                    return CanonicalTaskResponse(**dict(row)), None, dict(row)

                old_task = await self.conn.fetchrow("SELECT * FROM v_tasks_canonical WHERE id = $1", task_id)

                args.append(task_id)
                update_query = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = ${idx} RETURNING id"
                
                updated_id = await self.conn.fetchval(update_query, *args)
                if not updated_id:
                    raise HTTPException(status_code=404, detail="Task not found")

                new_task = await self.conn.fetchrow("SELECT * FROM v_tasks_canonical WHERE id = $1", task_id)
                return CanonicalTaskResponse(**dict(new_task)), dict(old_task), dict(new_task)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating task: {e}")
            raise HTTPException(status_code=400, detail="An unexpected error occurred")

    async def delete_task(self, task_id: int, current_user: dict):
        role = current_user.get("role", "MEMBER")
        if role not in ("MANAGER", "SUPER_ADMIN"):
            raise HTTPException(status_code=403, detail="Only MANAGER or SUPER_ADMIN can delete tasks")

        try:
            has_access = await self.conn.fetchval("SELECT can_edit_task($1, $2)", current_user["id"], task_id)
            if not has_access:
                raise HTTPException(status_code=403, detail="Task not found or access denied")

            async with self.conn.transaction():
                await self.conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(current_user["id"]))
                result = await self.conn.execute("UPDATE tasks SET deleted_at = CURRENT_TIMESTAMP WHERE id = $1 AND deleted_at IS NULL", task_id)
                if result == "UPDATE 0":
                    raise HTTPException(status_code=404, detail="Task not found")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            raise HTTPException(status_code=400, detail="An unexpected error occurred")

    async def get_my_board_tasks(self, board_id: int, current_user: dict) -> List[CanonicalTaskResponse]:
        try:
            has_access = await self.conn.fetchval("SELECT can_view_board($1, $2)", current_user["id"], board_id)
            if not has_access:
                raise HTTPException(status_code=403, detail="Board not found or access denied")

            rows = await self.conn.fetch(
                "SELECT * FROM v_tasks_canonical WHERE board_id = $1 AND assigned_to = $2",
                board_id, current_user["id"]
            )
            return [CanonicalTaskResponse(**dict(row)) for row in rows]
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting my tasks: {e}")
            raise HTTPException(status_code=400, detail="An unexpected error occurred")

    async def get_tasks_assigned_by_me(self, board_id: int, current_user: dict) -> List[CanonicalTaskResponse]:
        try:
            has_access = await self.conn.fetchval("SELECT can_view_board($1, $2)", current_user["id"], board_id)
            if not has_access:
                raise HTTPException(status_code=403, detail="Board not found or access denied")

            rows = await self.conn.fetch(
                "SELECT * FROM v_tasks_canonical WHERE board_id = $1 AND created_by = $2 AND assigned_to != $2",
                board_id, current_user["id"]
            )
            return [CanonicalTaskResponse(**dict(row)) for row in rows]
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting tasks assigned by me: {e}")
            raise HTTPException(status_code=400, detail="An unexpected error occurred")

    async def update_task_assignee(self, task_id: int, body: TaskAssigneeUpdate, current_user: dict) -> tuple[CanonicalTaskResponse, Optional[dict], dict]:
        try:
            has_access = await self.conn.fetchval("SELECT can_edit_task($1, $2)", current_user["id"], task_id)
            if not has_access:
                raise HTTPException(status_code=403, detail="Task not found or access denied")

            async with self.conn.transaction():
                await self.conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(current_user["id"]))
                old_task = await self.conn.fetchrow("SELECT * FROM v_tasks_canonical WHERE id = $1", task_id)

                updated_id = await self.conn.fetchval(
                    "UPDATE tasks SET assigned_to = $1 WHERE id = $2 RETURNING id",
                    body.assigned_to, task_id
                )
                if not updated_id:
                    raise HTTPException(status_code=404, detail="Task not found")

                new_task = await self.conn.fetchrow("SELECT * FROM v_tasks_canonical WHERE id = $1", task_id)
                return CanonicalTaskResponse(**dict(new_task)), dict(old_task), dict(new_task)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating task assignee: {e}")
            raise HTTPException(status_code=400, detail="An unexpected error occurred")