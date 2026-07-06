from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from app.ai.tools.base import BaseTool
from app.services.task_service import TaskService
from app.schemas.task import TaskCreate, TaskUpdate
from app.ai.schemas.planning import RiskLevel


# -----------------
# Task Tools
# -----------------

class CreateTaskParams(BaseModel):
    board_id: Optional[int] = Field(None, description="ID of the board to create the task in")
    board_name: Optional[str] = Field(None, description="The exact name of the board (if ID is unknown)")
    title: str = Field(..., description="Title of the task")
    description: Optional[str] = Field(None, description="Detailed description of the task")
    status: str = Field("TODO", description="Status of the task (e.g. TODO, IN_PROGRESS, DONE)")
    priority: str = Field("Medium", description="Priority of the task (e.g. Low, Medium, High)")
    assignee_name: Optional[str] = Field(None, description="The first name, last name, or email of the person to assign the task to")
    due_date: Optional[str] = Field(None, description="ISO format date string for when the task is due (e.g. 2026-12-31T23:59:59Z)")

class CreateTaskTool(BaseTool):
    name: str = "create_task"
    description: str = "Creates a new task in a specific board. Provide either board_id or board_name."
    input_schema = CreateTaskParams
    output_schema = Any
    category = "domain"
    action = "create_task"
    risk_level = RiskLevel.MEDIUM
    is_write_action = True

    async def execute(self, params: BaseModel, current_user: dict, services: Dict[str, Any]) -> Any:
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
            
        task_service: TaskService = services["task_service"]
        
        # Fetch columns to map status to column_id
        board_data = await task_service.get_board_tasks(board_id=board_id, assigned_to=None, current_user=current_user)
        
        column_id = None
        requested_status = params.status.lower().replace("_", " ") if params.status else "to do"
        
        # First try to match by exact name
        for col in board_data.columns:
            if col.name.lower() == requested_status:
                column_id = col.id
                break
                
        # If no match, try to match by column_type
        if not column_id:
            for col in board_data.columns:
                if col.column_type.lower() == params.status.lower():
                    column_id = col.id
                    break
                    
        # Fallback to the first column
        if not column_id and board_data.columns:
            column_id = board_data.columns[0].id
            
        if not column_id:
            raise ValueError(f"Could not find any columns for board_id {board_id}")
        
        # Resolve assignee_name to user_id
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

        from datetime import datetime
        parsed_due_date = None
        if params.due_date:
            try:
                # Handle basic ISO format parsing
                parsed_due_date = datetime.fromisoformat(params.due_date.replace("Z", "+00:00"))
            except ValueError:
                raise ValueError(f"Invalid due_date format: '{params.due_date}'. Please provide in ISO format (e.g. 2026-12-31T23:59:59Z)")

        task_in = TaskCreate(
            board_id=board_id,
            column_id=column_id,
            title=params.title,
            description=params.description,
            priority=params.priority.capitalize() if params.priority else "Medium",
            assigned_to=assigned_to,
            due_date=parsed_due_date
        )
        
        result = await task_service.create_task(task_in, current_user)
        return {"status": "success", "task_id": result.id if hasattr(result, "id") else None, "message": "Task created successfully"}




async def resolve_task_id(params, current_user: dict, services: Dict[str, Any]) -> int:
    if getattr(params, "task_id", None):
        return params.task_id
        
    task_name = getattr(params, "task_name", None)
    if not task_name:
        raise ValueError("Must provide either task_id or task_name")
        
    board_id = getattr(params, "board_id", None)
    board_name = getattr(params, "board_name", None)
    
    board_service = services.get("board_service")
    task_service = services.get("task_service")

    if not board_id and board_name:
        boards = await board_service.get_user_boards(include_archived=False, current_user=current_user)
        for b in boards:
            if b.name.lower() == board_name.lower():
                board_id = b.id
                break
                
    if not board_id:
        # Search across all boards
        boards = await board_service.get_user_boards(include_archived=False, current_user=current_user)
        for b in boards:
            board_data = await task_service.get_board_tasks(board_id=b.id, assigned_to=None, current_user=current_user)
            for t in board_data.tasks:
                if t.title.lower() == task_name.lower() or task_name.lower() in t.title.lower():
                    return t.id
        raise ValueError(f"Could not find task '{task_name}' in any board.")
        
    board_data = await task_service.get_board_tasks(board_id=board_id, assigned_to=None, current_user=current_user)
    
    for t in board_data.tasks:
        if t.title.lower() == task_name.lower() or task_name.lower() in t.title.lower():
            return t.id
            
    raise ValueError(f"Could not find task '{task_name}' in the specified board")

class UpdateTaskParams(BaseModel):
    task_id: Optional[int] = Field(None, description="ID of the task to update")
    task_name: Optional[str] = Field(None, description="Name/title of the task (if ID is unknown)")
    board_id: Optional[int] = Field(None, description="ID of the board containing the task (required if using task_name)")
    board_name: Optional[str] = Field(None, description="Name of the board containing the task (required if using task_name)")
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = Field(None, description="Priority of the task (e.g. Low, Medium, High)")
    assignee_name: Optional[str] = Field(None, description="The first name, last name, or email of the person to assign the task to")
    due_date: Optional[str] = Field(None, description="ISO format date string for when the task is due")

class UpdateTaskTool(BaseTool):
    name: str = "update_task"
    description: str = "Updates an existing task"
    input_schema = UpdateTaskParams
    output_schema = Any
    category = "domain"
    action = "update_task"
    risk_level = RiskLevel.MEDIUM
    is_write_action = True

    async def execute(self, params: BaseModel, current_user: dict, services: Dict[str, Any]) -> Any:
        task_service: TaskService = services["task_service"]
        
        real_task_id = await resolve_task_id(params, current_user, services)
        
        column_id = None
        if params.status:
            task = await task_service.get_task(real_task_id, current_user)
                
            board_id = task.board_id
            board_data = await task_service.get_board_tasks(board_id=board_id, assigned_to=None, current_user=current_user)
            
            requested_status = params.status.lower().replace("_", " ")
            for col in board_data.columns:
                if col.name.lower() == requested_status or col.column_type.lower() == params.status.lower():
                    column_id = col.id
                    break
                    
            if not column_id:
                raise ValueError(f"Could not find column matching status '{params.status}'")
        
        from datetime import datetime
        parsed_due_date = None
        if params.due_date:
            try:
                parsed_due_date = datetime.fromisoformat(params.due_date.replace("Z", "+00:00"))
            except ValueError:
                raise ValueError(f"Invalid due_date format: '{params.due_date}'. Please provide in ISO format (e.g. 2026-12-31T23:59:59Z)")

        update_kwargs = {}
        if params.title is not None: update_kwargs["title"] = params.title
        if params.description is not None: update_kwargs["description"] = params.description
        if column_id is not None: update_kwargs["column_id"] = column_id
        if params.priority is not None: update_kwargs["priority"] = params.priority.capitalize()
        if parsed_due_date is not None: update_kwargs["due_date"] = parsed_due_date
        
        task_update = TaskUpdate(**update_kwargs)
        
        # If assignee was updated, we need to handle that via TaskAssigneeUpdate or TaskService
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
                
            from app.schemas.task import TaskAssigneeUpdate
            await task_service.assign_task(params.task_id, TaskAssigneeUpdate(assigned_to=assigned_to), current_user)
        
        result = await task_service.update_task(real_task_id, task_update, current_user)
        return {"status": "success", "task_id": params.task_id, "message": "Task updated successfully"}

# Register tools automatically when imported (or can be done manually in registry.py)
from app.ai.tools.registry import tool_registry

tool_registry.register(CreateTaskTool())
tool_registry.register(UpdateTaskTool())


class DeleteTaskParams(BaseModel):
    task_id: Optional[int] = Field(None, description="ID of the task to delete (if known)")
    task_name: Optional[str] = Field(None, description="Name/title of the task (if ID is unknown)")
    board_id: Optional[int] = Field(None, description="ID of the board containing the task")
    board_name: Optional[str] = Field(None, description="Name of the board containing the task")

class DeleteTaskTool(BaseTool):
    name: str = "delete_task"
    description: str = "Deletes a task. Provide task_id, or task_name along with board_name."
    input_schema = DeleteTaskParams
    output_schema = Any
    category = "domain"
    action = "delete_task"
    risk_level = RiskLevel.HIGH
    is_write_action = True

    async def execute(self, params: DeleteTaskParams, current_user: dict, services: Dict[str, Any]) -> Any:
        task_service = services["task_service"]
        real_task_id = await resolve_task_id(params, current_user, services)
        await task_service.delete_task(real_task_id, current_user)
        return {"status": "success", "message": f"Task deleted successfully"}
