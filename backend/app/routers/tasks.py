import logging
from typing import Optional, List
import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks

from app.schemas.task import TaskCreate, TaskUpdate, TaskAssigneeUpdate, CanonicalTaskResponse, BoardDataResponse
from app.schemas.envelope import DataEnvelope
from app.services.notification_service import dispatch_task_email
from app.auth.dependencies import get_current_user
from app.database.connection import get_db_connection
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Tasks"])

def get_task_service(conn: asyncpg.Connection = Depends(get_db_connection)) -> TaskService:
    return TaskService(conn)

@router.post("/tasks", response_model=DataEnvelope[CanonicalTaskResponse])
async def create_task(
    task_in: TaskCreate,
    current_user: dict = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    task = await task_service.create_task(task_in, current_user)
    return DataEnvelope(data=task)


@router.get("/boards/{board_id}/tasks", response_model=DataEnvelope[BoardDataResponse])
async def get_board_tasks(
    board_id: str,
    assigned_to: Optional[int] = Query(default=None),
    current_user: dict = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    b_str = str(board_id).strip()
    try:
        int_board_id = int(b_str.split('-')[-1]) if '-' in b_str else int(b_str)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid board ID format: {board_id}")

    data = await task_service.get_board_tasks(int_board_id, assigned_to, current_user)
    return DataEnvelope(data=data)



@router.patch("/tasks/{task_id}", response_model=DataEnvelope[CanonicalTaskResponse])
async def update_task(
    task_id: int,
    task_in: TaskUpdate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    new_task, old_dict, new_dict = await task_service.update_task(task_id, task_in, current_user)
    
    if old_dict and new_dict:
        actor_name = current_user.get("first_name") or current_user.get("email")

        if old_dict.get("assigned_to") != new_dict.get("assigned_to"):
            background_tasks.add_task(
                dispatch_task_email,
                activity_type="ASSIGNEE_CHANGED",
                task_title=new_dict["title"],
                board_name=new_dict["board_name"],
                actor_name=actor_name,
                assignee_email=new_dict["assignee_email"],
                assignee_name=new_dict["assignee_first_name"],
                old_assignee_email=old_dict["assignee_email"],
                old_assignee_name=old_dict["assignee_first_name"],
            )

        if old_dict.get("due_date") != new_dict.get("due_date"):
            background_tasks.add_task(
                dispatch_task_email,
                activity_type="DUE_DATE_CHANGED",
                task_title=new_dict["title"],
                board_name=new_dict["board_name"],
                actor_name=actor_name,
                assignee_email=new_dict["assignee_email"],
                assignee_name=new_dict["assignee_first_name"],
            )

        if old_dict.get("column_id") != new_dict.get("column_id"):
            background_tasks.add_task(
                dispatch_task_email,
                activity_type="STATUS_CHANGED",
                task_title=new_dict["title"],
                board_name=new_dict["board_name"],
                actor_name=actor_name,
                assignee_email=new_dict["assignee_email"],
                assignee_name=new_dict["assignee_first_name"],
                old_status=old_dict["column_name"],
                new_status=new_dict["column_name"],
            )

    return DataEnvelope(data=new_task)


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    current_user: dict = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    await task_service.delete_task(task_id, current_user)
    return None


@router.get("/boards/{board_id}/my-tasks", response_model=DataEnvelope[List[CanonicalTaskResponse]])
async def get_my_board_tasks(
    board_id: int,
    current_user: dict = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    tasks = await task_service.get_my_board_tasks(board_id, current_user)
    return DataEnvelope(data=tasks)


@router.get("/boards/{board_id}/assigned-by-me", response_model=DataEnvelope[List[CanonicalTaskResponse]])
async def get_tasks_assigned_by_me(
    board_id: int,
    current_user: dict = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    tasks = await task_service.get_tasks_assigned_by_me(board_id, current_user)
    return DataEnvelope(data=tasks)


@router.patch("/tasks/{task_id}/assignee", response_model=DataEnvelope[CanonicalTaskResponse])
async def update_task_assignee(
    task_id: int,
    body: TaskAssigneeUpdate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    task_service: TaskService = Depends(get_task_service)
):
    new_task, old_dict, new_dict = await task_service.update_task_assignee(task_id, body, current_user)

    if old_dict and new_dict:
        actor_name = current_user.get("first_name") or current_user.get("email")
        if old_dict.get("assigned_to") != new_dict.get("assigned_to"):
            background_tasks.add_task(
                dispatch_task_email,
                activity_type="ASSIGNEE_CHANGED",
                task_title=new_dict["title"],
                board_name=new_dict["board_name"],
                actor_name=actor_name,
                assignee_email=new_dict["assignee_email"],
                assignee_name=new_dict["assignee_first_name"],
                old_assignee_email=old_dict["assignee_email"],
                old_assignee_name=old_dict["assignee_first_name"],
            )

    return DataEnvelope(data=new_task)
