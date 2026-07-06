from typing import Any, Dict, List
from pydantic import BaseModel, Field
from app.ai.tools.base import BaseTool

# --- List Boards Tool ---
class ListBoardsInput(BaseModel):
    include_archived: bool = Field(default=False, description="Whether to include archived boards")

class ListBoardsTool(BaseTool):
    name = "list_boards"
    description = "List all boards (projects) the current user has access to."
    input_schema = ListBoardsInput
    output_schema = Any # Dict/List is fine for output
    category = "workspace"
    action = "list_projects"
    
    async def execute(self, params: ListBoardsInput, current_user: dict, services: Dict[str, Any]) -> Any:
        board_service = services.get("board_service")
        boards = await board_service.get_user_boards(
            include_archived=params.include_archived,
            current_user=current_user
        )
        return [{"id": b.id, "name": b.name, "description": getattr(b, "description", None)} for b in boards]

# --- List Tasks Tool ---
class ListTasksInput(BaseModel):
    board_id: int = Field(description="The ID of the board to list tasks for")

class ListTasksTool(BaseTool):
    name = "list_tasks"
    description = "List tasks for a specific board."
    input_schema = ListTasksInput
    output_schema = Any
    category = "workspace"
    action = "list_tasks"
    
    async def execute(self, params: ListTasksInput, current_user: dict, services: Dict[str, Any]) -> Any:
        task_service = services.get("task_service")
        board_data = await task_service.get_board_tasks(board_id=params.board_id, assigned_to=None, current_user=current_user)
        # Return a summarized dictionary to save tokens
        return [{"id": t.id, "title": t.title, "column_name": t.column_name, "assignee_id": t.assignee_id} for t in board_data.tasks]

# --- Get Workspace Users Tool ---
class GetWorkspaceUsersInput(BaseModel):
    pass

class GetWorkspaceUsersTool(BaseTool):
    name = "get_workspace_users"
    description = "Get a list of all users in the organization."
    input_schema = GetWorkspaceUsersInput
    output_schema = Any
    category = "workspace"
    action = "get_users"
    
    async def execute(self, params: GetWorkspaceUsersInput, current_user: dict, services: Dict[str, Any]) -> Any:
        user_service = services.get("user_service")
        users = await user_service.get_all_users(current_user=current_user)
        return [{"id": u.id, "first_name": u.first_name, "last_name": u.last_name, "email": u.email} for u in users]

# --- Get Task Tool ---
class GetTaskInput(BaseModel):
    task_id: int = Field(description="The ID of the task to retrieve")

class GetTaskTool(BaseTool):
    name = "get_task"
    description = "Retrieve full details for a specific task."
    input_schema = GetTaskInput
    output_schema = Any
    category = "workspace"
    action = "get_task_details"

    async def execute(self, params: GetTaskInput, current_user: dict, services: Dict[str, Any]) -> Any:
        task_service = services.get("task_service")
        task = await task_service.get_task(task_id=params.task_id, current_user=current_user)
        return task.model_dump() if hasattr(task, "model_dump") else task
