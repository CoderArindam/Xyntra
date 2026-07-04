import logging
from typing import Optional, List
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from app.schemas.task import TaskCreate, TaskUpdate, TaskAssigneeUpdate, CanonicalTaskResponse, BoardDataResponse
from app.schemas.common import DataEnvelope
from app.services.notification_service import dispatch_task_email
from app.auth.dependencies import get_current_user
from app.database.connection import get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Tasks"])

async def execute_with_actor(conn: asyncpg.Connection, actor_id: int, query: str, *args):
    """Executes a query setting the app.current_user_id for triggers."""
    async with conn.transaction():
        await conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(actor_id))
        return await conn.fetchval(query, *args)


@router.post("/tasks", response_model=DataEnvelope[CanonicalTaskResponse])
async def create_task(
    task_in: TaskCreate,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    role = current_user.get("role", "MEMBER")
    if role not in ("MANAGER", "SUPER_ADMIN"):
        raise HTTPException(status_code=403, detail="Only MANAGER or SUPER_ADMIN can create tasks")

    try:
        # AuthZ
        has_access = await conn.fetchval("SELECT can_view_board($1, $2)", current_user["id"], task_in.board_id)
        if not has_access:
            raise HTTPException(status_code=403, detail="Board not found or access denied")

        async with conn.transaction():
            await conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(current_user["id"]))
            task_id = await conn.fetchval(
                """
                INSERT INTO tasks (board_id, column_id, title, description, priority, assigned_to, created_by, due_date, reminder_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
                """,
                task_in.board_id, task_in.column_id, task_in.title, task_in.description,
                task_in.priority, task_in.assigned_to, current_user["id"], task_in.due_date, task_in.reminder_at
            )
            
            row = await conn.fetchrow("SELECT * FROM v_tasks_canonical WHERE id = $1", task_id)
            return DataEnvelope(data=CanonicalTaskResponse(**dict(row)))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=400, detail="An unexpected error occurred")


@router.get("/boards/{board_id}/tasks", response_model=DataEnvelope[BoardDataResponse])
async def get_board_tasks(
    board_id: int,
    assigned_to: Optional[int] = Query(default=None),
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        has_access = await conn.fetchval("SELECT can_view_board($1, $2)", current_user["id"], board_id)
        if not has_access:
            raise HTTPException(status_code=403, detail="Board not found or access denied")

        columns_rows = await conn.fetch(
            "SELECT id, name, position, column_type, (column_type = 'DONE') AS is_completed FROM board_columns WHERE board_id = $1 ORDER BY position",
            board_id
        )
        
        query = "SELECT * FROM v_tasks_canonical WHERE board_id = $1"
        args = [board_id]
        
        if assigned_to is not None:
            query += " AND assigned_to = $2"
            args.append(assigned_to)
            
        tasks_rows = await conn.fetch(query, *args)
        
        data = BoardDataResponse(
            columns=[dict(c) for c in columns_rows],
            tasks=[CanonicalTaskResponse(**dict(t)) for t in tasks_rows]
        )
        return DataEnvelope(data=data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting board tasks: {e}")
        raise HTTPException(status_code=400, detail="An unexpected error occurred")


@router.patch("/tasks/{task_id}", response_model=DataEnvelope[CanonicalTaskResponse])
async def update_task(
    task_id: int,
    task_in: TaskUpdate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        has_access = await conn.fetchval("SELECT can_edit_task($1, $2)", current_user["id"], task_id)
        if not has_access:
            raise HTTPException(status_code=403, detail="Task not found or access denied")

        async with conn.transaction():
            await conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(current_user["id"]))
            
            # Build dynamic update query
            update_fields = []
            args = []
            idx = 1
            for field, value in task_in.model_dump(exclude_unset=True).items():
                update_fields.append(f"{field} = ${idx}")
                args.append(value)
                idx += 1
                
            if not update_fields:
                row = await conn.fetchrow("SELECT * FROM v_tasks_canonical WHERE id = $1", task_id)
                return DataEnvelope(data=CanonicalTaskResponse(**dict(row)))

            old_task = await conn.fetchrow("SELECT * FROM v_tasks_canonical WHERE id = $1", task_id)

            args.append(task_id)
            update_query = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = ${idx} RETURNING id"
            
            updated_id = await conn.fetchval(update_query, *args)
            if not updated_id:
                raise HTTPException(status_code=404, detail="Task not found")

            new_task = await conn.fetchrow("SELECT * FROM v_tasks_canonical WHERE id = $1", task_id)
            
            actor_name = current_user.get("first_name") or current_user.get("email")

            if old_task["assigned_to"] != new_task["assigned_to"]:
                background_tasks.add_task(
                    dispatch_task_email,
                    activity_type="ASSIGNEE_CHANGED",
                    task_title=new_task["title"],
                    board_name=new_task["board_name"],
                    actor_name=actor_name,
                    assignee_email=new_task["assignee_email"],
                    assignee_name=new_task["assignee_first_name"],
                    old_assignee_email=old_task["assignee_email"],
                    old_assignee_name=old_task["assignee_first_name"],
                )

            if old_task["due_date"] != new_task["due_date"]:
                background_tasks.add_task(
                    dispatch_task_email,
                    activity_type="DUE_DATE_CHANGED",
                    task_title=new_task["title"],
                    board_name=new_task["board_name"],
                    actor_name=actor_name,
                    assignee_email=new_task["assignee_email"],
                    assignee_name=new_task["assignee_first_name"],
                )

            if old_task["column_id"] != new_task["column_id"]:
                background_tasks.add_task(
                    dispatch_task_email,
                    activity_type="STATUS_CHANGED",
                    task_title=new_task["title"],
                    board_name=new_task["board_name"],
                    actor_name=actor_name,
                    assignee_email=new_task["assignee_email"],
                    assignee_name=new_task["assignee_first_name"],
                    old_status=old_task["column_name"],
                    new_status=new_task["column_name"],
                )

            return DataEnvelope(data=CanonicalTaskResponse(**dict(new_task)))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        raise HTTPException(status_code=400, detail="An unexpected error occurred")


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    role = current_user.get("role", "MEMBER")
    if role not in ("MANAGER", "SUPER_ADMIN"):
        raise HTTPException(status_code=403, detail="Only MANAGER or SUPER_ADMIN can delete tasks")

    try:
        has_access = await conn.fetchval("SELECT can_edit_task($1, $2)", current_user["id"], task_id)
        if not has_access:
            raise HTTPException(status_code=403, detail="Task not found or access denied")

        async with conn.transaction():
            await conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(current_user["id"]))
            # Soft delete
            result = await conn.execute("UPDATE tasks SET deleted_at = CURRENT_TIMESTAMP WHERE id = $1 AND deleted_at IS NULL", task_id)
            if result == "UPDATE 0":
                raise HTTPException(status_code=404, detail="Task not found")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        raise HTTPException(status_code=400, detail="An unexpected error occurred")


@router.get("/boards/{board_id}/my-tasks", response_model=DataEnvelope[List[CanonicalTaskResponse]])
async def get_my_board_tasks(
    board_id: int,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        has_access = await conn.fetchval("SELECT can_view_board($1, $2)", current_user["id"], board_id)
        if not has_access:
            raise HTTPException(status_code=403, detail="Board not found or access denied")

        rows = await conn.fetch(
            "SELECT * FROM v_tasks_canonical WHERE board_id = $1 AND assigned_to = $2",
            board_id, current_user["id"]
        )
        return DataEnvelope(data=[CanonicalTaskResponse(**dict(row)) for row in rows])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting my tasks: {e}")
        raise HTTPException(status_code=400, detail="An unexpected error occurred")


@router.get("/boards/{board_id}/assigned-by-me", response_model=DataEnvelope[List[CanonicalTaskResponse]])
async def get_tasks_assigned_by_me(
    board_id: int,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        has_access = await conn.fetchval("SELECT can_view_board($1, $2)", current_user["id"], board_id)
        if not has_access:
            raise HTTPException(status_code=403, detail="Board not found or access denied")

        rows = await conn.fetch(
            "SELECT * FROM v_tasks_canonical WHERE board_id = $1 AND created_by = $2 AND assigned_to != $2",
            board_id, current_user["id"]
        )
        return DataEnvelope(data=[CanonicalTaskResponse(**dict(row)) for row in rows])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tasks assigned by me: {e}")
        raise HTTPException(status_code=400, detail="An unexpected error occurred")


@router.patch("/tasks/{task_id}/assignee", response_model=DataEnvelope[CanonicalTaskResponse])
async def update_task_assignee(
    task_id: int,
    body: TaskAssigneeUpdate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db_connection)
):
    try:
        has_access = await conn.fetchval("SELECT can_edit_task($1, $2)", current_user["id"], task_id)
        if not has_access:
            raise HTTPException(status_code=403, detail="Task not found or access denied")

        async with conn.transaction():
            await conn.execute("SELECT set_config('app.current_user_id', $1, true)", str(current_user["id"]))
            old_task = await conn.fetchrow("SELECT * FROM v_tasks_canonical WHERE id = $1", task_id)

            updated_id = await conn.fetchval(
                "UPDATE tasks SET assigned_to = $1 WHERE id = $2 RETURNING id",
                body.assigned_to, task_id
            )
            if not updated_id:
                raise HTTPException(status_code=404, detail="Task not found")

            new_task = await conn.fetchrow("SELECT * FROM v_tasks_canonical WHERE id = $1", task_id)
            
            actor_name = current_user.get("first_name") or current_user.get("email")

            if old_task["assigned_to"] != new_task["assigned_to"]:
                background_tasks.add_task(
                    dispatch_task_email,
                    activity_type="ASSIGNEE_CHANGED",
                    task_title=new_task["title"],
                    board_name=new_task["board_name"],
                    actor_name=actor_name,
                    assignee_email=new_task["assignee_email"],
                    assignee_name=new_task["assignee_first_name"],
                    old_assignee_email=old_task["assignee_email"],
                    old_assignee_name=old_task["assignee_first_name"],
                )

            data = CanonicalTaskResponse(**dict(new_task))

            return DataEnvelope(data=data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task assignee: {e}")
        raise HTTPException(status_code=400, detail="An unexpected error occurred")
