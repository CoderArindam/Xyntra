from typing import Any, Dict, List, Optional
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
        return {"projects": [{"id": b.id, "name": b.name, "description": getattr(b, "description", None)} for b in boards]}

# --- List Tasks Tool ---
class ListTasksInput(BaseModel):
    board_id: Optional[int] = Field(None, description="The ID of the board to list tasks for")
    board_name: Optional[str] = Field(None, description="The exact name of the board (if ID is unknown)")
    status: Optional[str] = Field(None, description="Filter tasks by status (e.g. 'In Progress', 'Done', 'To Do')")
    assignee_name: Optional[str] = Field(None, description="Filter tasks by assignee name")

class ListTasksTool(BaseTool):
    name = "list_tasks"
    description = "List tasks for a specific board. Provide either board_id or board_name. Can optionally filter by status or assignee_name. Use this tool for ANY queries requiring you to filter, list, or count tasks (do not invent a 'filter_tasks' action)."
    input_schema = ListTasksInput
    output_schema = Any
    category = "workspace"
    action = "list_tasks"
    
    async def execute(self, params: ListTasksInput, current_user: dict, services: Dict[str, Any]) -> Any:
        board_id = params.board_id
        if not board_id and params.board_name:
            board_service = services.get("board_service")
            boards = await board_service.get_user_boards(include_archived=False, current_user=current_user)
            for b in boards:
                if b.name.lower() == params.board_name.lower():
                    board_id = b.id
                    break
            if not board_id:
                raise ValueError(f"Could not find board with name '{params.board_name}'")
                
        if not board_id:
            raise ValueError("Either board_id or board_name must be provided")
            
        assigned_to = None
        if params.assignee_name:
            user_service = services.get("user_service")
            users = await user_service.get_all_users(current_user=current_user)
            name_lower = params.assignee_name.lower()
            for u in users:
                u_first = u.get("first_name") or ""
                u_last = u.get("last_name") or ""
                u_email = u.get("email") or ""
                full_name = f"{u_first} {u_last}".strip().lower()
                if (u_first and name_lower in u_first.lower()) or \
                   (u_last and name_lower in u_last.lower()) or \
                   (u_email and name_lower in u_email.lower()) or \
                   (name_lower in full_name) or (full_name and full_name in name_lower):
                    assigned_to = u.get("id")
                    break
            if not assigned_to:
                raise ValueError(f"Could not resolve assignee '{params.assignee_name}' to a valid user in this workspace.")

        task_service = services.get("task_service")
        board_data = await task_service.get_board_tasks(board_id=board_id, assigned_to=assigned_to, current_user=current_user)
        
        filtered_tasks = board_data.tasks
        if params.status:
            status_clean = params.status.lower().replace("_", "").replace(" ", "").replace("-", "")
            filtered_tasks = [t for t in filtered_tasks if status_clean in (t.column_name or "").lower().replace("_", "").replace(" ", "").replace("-", "")]
            
        return {"tasks": [{
            "id": t.id, 
            "title": t.title, 
            "column_name": t.column_name, 
            "assignee_id": t.assigned_to,
            "assignee_name": f"{t.assignee_first_name or ''} {t.assignee_last_name or ''}".strip() if t.assigned_to else None,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "is_completed": t.is_completed
        } for t in filtered_tasks]}

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
        return {"users": [{"id": u.get("id"), "first_name": u.get("first_name"), "last_name": u.get("last_name"), "email": u.get("email")} for u in users]}

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
        return {"task": task.model_dump() if hasattr(task, "model_dump") else task}
