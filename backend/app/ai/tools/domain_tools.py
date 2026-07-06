from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from app.ai.tools.base import BaseTool
from app.services.task_service import TaskService
from app.schemas.task import TaskCreate, TaskUpdate

# -----------------
# Task Tools
# -----------------

class CreateTaskParams(BaseModel):
    board_id: int = Field(..., description="ID of the board to create the task in")
    title: str = Field(..., description="Title of the task")
    description: Optional[str] = Field(None, description="Detailed description of the task")
    status: str = Field("TODO", description="Status of the task (e.g. TODO, IN_PROGRESS, DONE)")
    priority: str = Field("MEDIUM", description="Priority of the task (e.g. LOW, MEDIUM, HIGH)")

class CreateTaskTool(BaseTool):
    name: str = "create_task"
    description: str = "Creates a new task in a specific board"
    schema = CreateTaskParams

    async def execute(self, params: BaseModel, current_user: dict, services: Dict[str, Any]) -> Any:
        task_service: TaskService = services["task_service"]
        
        task_in = TaskCreate(
            title=params.title,
            description=params.description,
            status=params.status,
            priority=params.priority
        )
        
        # We pass board_id separately based on how task_service is implemented
        # Actually TaskCreate doesn't have board_id by default, it might. Let's check.
        # Assuming TaskCreate is correct, if not, we adapt.
        
        result = await task_service.create_task(params.board_id, task_in, current_user)
        return result


class GetTasksParams(BaseModel):
    board_id: int = Field(..., description="ID of the board to list tasks for")

class GetTasksTool(BaseTool):
    name: str = "get_tasks"
    description: str = "Gets a list of all tasks in a specific board"
    schema = GetTasksParams

    async def execute(self, params: BaseModel, current_user: dict, services: Dict[str, Any]) -> Any:
        task_service: TaskService = services["task_service"]
        tasks = await task_service.get_tasks(params.board_id, current_user)
        return tasks

class UpdateTaskParams(BaseModel):
    task_id: int = Field(..., description="ID of the task to update")
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None

class UpdateTaskTool(BaseTool):
    name: str = "update_task"
    description: str = "Updates an existing task"
    schema = UpdateTaskParams

    async def execute(self, params: BaseModel, current_user: dict, services: Dict[str, Any]) -> Any:
        task_service: TaskService = services["task_service"]
        
        task_update = TaskUpdate(
            title=params.title,
            description=params.description,
            status=params.status,
            priority=params.priority
        )
        
        result = await task_service.update_task(params.task_id, task_update, current_user)
        return result

# Register tools automatically when imported (or can be done manually in registry.py)
from app.ai.tools.registry import tool_registry

tool_registry.register(CreateTaskTool())
tool_registry.register(GetTasksTool())
tool_registry.register(UpdateTaskTool())
