"""
Architectural Rule:
Every success message presented to the user must originate from verified backend state 
rather than planner arguments or user input. Mutation tools must return standardized 
outputs containing `status`, `action`, `message`, `verified`, and `warnings`.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.ai.tools.base import BaseTool
from app.services.task_service import TaskService
from app.schemas.task import TaskCreate, TaskUpdate, TaskAssigneeUpdate
from app.ai.schemas.planning import RiskLevel
from app.ai.tools.fuzzy import resolve_board, resolve_user, resolve_column

def _serialize(data: Any) -> Any:
    from datetime import datetime, date
    if hasattr(data, "model_dump"):
        return data.model_dump(mode="json")
    if isinstance(data, dict):
        return {k: _serialize(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_serialize(v) for v in data]
    if isinstance(data, (datetime, date)):
        return data.isoformat()
    return data


# -----------------
# Shared Helpers
# -----------------

async def resolve_board_id(board_id: Optional[int], board_name: Optional[str],
                           current_user: dict, services: Dict[str, Any]) -> int:
    """Helper to resolve a board by ID or name"""
    board_service = services["board_service"]
    
    if board_id:
        return board_id
        
    if not board_name:
        raise ValueError("Either board_id or board_name must be provided")
        
    # Intercept pronouns
    if board_name.lower() in ["here", "this project", "that board", "it", "this"]:
        recent_entities = services.get("recent_entities", {})
        if "board" in recent_entities:
            return recent_entities["board"]["entity_id"]
        
    boards = await board_service.get_user_boards(include_archived=False, current_user=current_user)
    match = resolve_board(board_name, boards)
    if not match:
        if not boards:
            raise ValueError(f"You don't have access to any projects. Please create one or request access first.")
        available = ", ".join(b.name for b in boards[:10])
        raise ValueError(f"Could not resolve board '{board_name}'. Available boards: {available if available else '(empty)'}")
        
    return match.id


async def resolve_assignee_id(assignee_name: str, current_user: dict,
                              services: Dict[str, Any]) -> int:
    """Resolve assignee name to user ID using fuzzy matching."""
    if assignee_name.lower() in ["me", "my", "mine", "myself", "i"]:
        return current_user.get("id")
        
    user_service = services.get("user_service")
    users = await user_service.get_all_users(current_user=current_user)
    match = resolve_user(assignee_name, users)
    if not match:
        available = ", ".join(f"{u.get('first_name', '')} {u.get('last_name', '')}".strip() for u in users[:10])
        raise ValueError(f"Could not resolve assignee '{assignee_name}'. Available users: {available}")
    return match.get("id")


async def resolve_column_id(status: str, board_id: int, current_user: dict,
                            services: Dict[str, Any]) -> int:
    """Resolve status string to column_id using fuzzy matching."""
    task_service = services.get("task_service")
    board_data = await task_service.get_board_tasks(board_id=board_id, assigned_to=None, current_user=current_user)
    
    match = resolve_column(status, board_data.columns)
    if match:
        return match.id
    
    # Fallback to first column
    if board_data.columns:
        return board_data.columns[0].id
    
    raise ValueError(f"Could not find any columns for board_id {board_id}")


def parse_due_date(due_date_str: str):
    """Parse ISO date string to datetime."""
    from datetime import datetime
    try:
        return datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"Invalid due_date format: '{due_date_str}'. Please provide in ISO format (e.g. 2026-12-31T23:59:59Z)")


async def resolve_task_id(params, current_user: dict, services: Dict[str, Any]) -> int:
    """Resolve a task by ID or by fuzzy name search across boards."""
    if getattr(params, "task_id", None):
        return params.task_id
    
    task_name = getattr(params, "task_name", None) or getattr(params, "title", None) or getattr(params, "task_title", None)
    if not task_name:
        raise ValueError("Must provide either task_id or task_name")
        
    # Intercept pronouns
    if task_name.lower() in ["it", "this", "that", "this task", "that one", "the task"]:
        recent_entities = services.get("recent_entities", {})
        if "task" in recent_entities:
            return recent_entities["task"]["entity_id"]
    
    board_service = services.get("board_service")
    task_service = services.get("task_service")
    
    # If board context is provided, search within that board
    board_id = getattr(params, "board_id", None)
    board_name = getattr(params, "board_name", None)
    
    if not board_id and board_name:
        boards = await board_service.get_user_boards(include_archived=False, current_user=current_user)
        match = resolve_board(board_name, boards)
        if match:
            board_id = match.id
    
    if board_id:
        board_data = await task_service.get_board_tasks(board_id=board_id, assigned_to=None, current_user=current_user)
        from app.ai.tools.fuzzy import fuzzy_score
        best_task = None
        best_score = 0.0
        for t in board_data.tasks:
            score = fuzzy_score(task_name, t.title)
            # Tie breaker: if scores are equal, prefer the task with the higher ID (more recently created)
            if score > best_score or (score == best_score and best_score >= 0.5 and best_task and t.id > best_task.id):
                best_score = score
                best_task = t
        if best_task and best_score >= 0.5:
            return best_task.id
        raise ValueError(f"Could not find task '{task_name}' in the specified board")
    
    # Search across all boards
    boards = await board_service.get_user_boards(include_archived=False, current_user=current_user)
    from app.ai.tools.fuzzy import fuzzy_score
    best_task = None
    best_score = 0.0
    for b in boards:
        board_data = await task_service.get_board_tasks(board_id=b.id, assigned_to=None, current_user=current_user)
        for t in board_data.tasks:
            score = fuzzy_score(task_name, t.title)
            if score > best_score or (score == best_score and best_score >= 0.5 and best_task and t.id > best_task.id):
                best_score = score
                best_task = t
                
    if best_task and best_score >= 0.5:
        return best_task.id
    raise ValueError(f"Could not find task '{task_name}' in any board.")


# -----------------
# Task Tools
# -----------------

class CreateTaskParams(BaseModel):
    model_config = {"populate_by_name": True}
    board_id: Optional[int] = Field(None, description="The ID of the board")
    board_name: Optional[str] = Field(None, alias="name", description="The name of the board (if ID is unknown)")
    title: str = Field(..., description="The title of the task")
    description: Optional[str] = Field(None, description="Detailed description")
    status: Optional[str] = Field(None, description="Status (e.g., TODO, IN_PROGRESS, DONE)")
    priority: Optional[str] = Field(None, description="Priority (LOW, MEDIUM, HIGH)")
    assignee_id: Optional[int] = Field(None, description="The ID of the user to assign the task to")
    assignee_name: Optional[str] = Field(None, alias="assignee", description="The name or email of the user to assign (if ID is unknown)")
    due_date: Optional[str] = Field(None, description="Due date in ISO 8601 format (e.g., 2026-12-31T00:00:00Z)")


class CreateTaskTool(BaseTool):
    name: str = "create_task"
    description: str = "Creates a new task in a specific board/project. Provide either board_id or board_name."
    input_schema = CreateTaskParams
    output_schema = Any
    category = "domain"
    action = "create_task"
    required_roles = ["MANAGER", "SUPER_ADMIN"]
    risk_level = RiskLevel.SAFE
    is_write_action = True

    async def execute(self, params: BaseModel, current_user: dict, services: Dict[str, Any]) -> Any:
        board_id = await resolve_board_id(params.board_id, params.board_name, current_user, services)
        column_id = await resolve_column_id(params.status or "TODO", board_id, current_user, services)
        
        assigned_to = None
        if params.assignee_name:
            assigned_to = await resolve_assignee_id(params.assignee_name, current_user, services)
        
        parsed_due_date = parse_due_date(params.due_date) if params.due_date else None
        
        task_service: TaskService = services["task_service"]
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
        return {
            "status": "success",
            "action": "created",
            "message": f"Task '{result.title}' created successfully",
            "verified": _serialize(dict(result)),
            "warnings": []
        }


class UpdateTaskParams(BaseModel):
    model_config = {"populate_by_name": True}
    task_id: Optional[int] = Field(None, description="ID of the task to update (if known)")
    task_name: Optional[str] = Field(None, description="The EXISTING name of the task (use this to find the task if ID is unknown)")
    board_id: Optional[int] = Field(None, description="ID of the board containing the task")
    board_name: Optional[str] = Field(None, description="Name of the board containing the task")
    title: Optional[str] = Field(None, alias="new_name", description="The NEW title of the task (if you want to rename it)")
    description: Optional[str] = Field(None, description="The NEW description of the task")
    status: Optional[str] = Field(None, description="The NEW status (column) of the task (e.g. To Do, In Progress, Done)")
    priority: Optional[str] = Field(None, description="Priority of the task (e.g. Low, Medium, High, Urgent)")
    assignee_name: Optional[str] = Field(None, alias="assignee", description="The first name, last name, or email of the person to assign the task to")
    due_date: Optional[str] = Field(None, description="ISO format date string for when the task is due")


class UpdateTaskTool(BaseTool):
    name: str = "update_task"
    description: str = "Updates an existing task. Can rename, change priority, status, assignee, due date."
    input_schema = UpdateTaskParams
    output_schema = Any
    category = "domain"
    action = "update_task"
    required_roles = ["MANAGER", "SUPER_ADMIN"]
    risk_level = RiskLevel.SAFE
    is_write_action = True

    async def execute(self, params: BaseModel, current_user: dict, services: Dict[str, Any]) -> Any:
        task_service: TaskService = services["task_service"]
        real_task_id = await resolve_task_id(params, current_user, services)
        
        # Resolve column if status change requested
        column_id = None
        if params.status:
            task = await task_service.get_task(real_task_id, current_user)
            column_id = await resolve_column_id(params.status, task.board_id, current_user, services)
        
        parsed_due_date = parse_due_date(params.due_date) if params.due_date else None
        
        update_kwargs = {}
        if params.title is not None:
            update_kwargs["title"] = params.title
        if params.description is not None:
            update_kwargs["description"] = params.description
        if column_id is not None:
            update_kwargs["column_id"] = column_id
        if params.priority is not None:
            update_kwargs["priority"] = params.priority.capitalize()
        if parsed_due_date is not None:
            update_kwargs["due_date"] = parsed_due_date
        
        task_update = TaskUpdate(**update_kwargs)
        
        # Handle assignee update
        if params.assignee_name:
            assigned_to = await resolve_assignee_id(params.assignee_name, current_user, services)
            await task_service.update_task_assignee(
                real_task_id,
                TaskAssigneeUpdate(assigned_to=assigned_to),
                current_user
            )
        
        result, old_dict, new_dict = await task_service.update_task(real_task_id, task_update, current_user)
        
        # Build descriptive message
        changes = []
        if params.title:
            changes.append(f"renamed to '{new_dict.get('title')}'")
        if params.status:
            changes.append(f"moved to '{new_dict.get('column_name')}'")
        if params.priority:
            changes.append(f"priority set to '{new_dict.get('priority')}'")
        if params.assignee_name:
            assignee_disp = f"{new_dict.get('assignee_first_name') or ''} {new_dict.get('assignee_last_name') or ''}".strip()
            changes.append(f"assigned to '{assignee_disp}'" if assignee_disp else "unassigned")
        if params.due_date:
            changes.append(f"due date set to '{new_dict.get('due_date')}'")
        if params.description:
            changes.append("description updated")
        
        change_desc = ", ".join(changes) if changes else "updated"
        
        return {
            "status": "success",
            "action": "updated",
            "message": f"Task {change_desc} successfully",
            "verified": _serialize(new_dict),
            "warnings": []
        }


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
    required_roles = ["MANAGER", "SUPER_ADMIN"]
    risk_level = RiskLevel.HIGH
    is_write_action = True

    async def execute(self, params: DeleteTaskParams, current_user: dict, services: Dict[str, Any]) -> Any:
        task_service = services["task_service"]
        real_task_id = await resolve_task_id(params, current_user, services)
        await task_service.delete_task(real_task_id, current_user)
        return {
            "status": "success",
            "action": "deleted",
            "message": "Task deleted successfully",
            "verified": {"task_id": real_task_id},
            "warnings": []
        }


# -----------------
# Board Tools
# -----------------

class CreateBoardParams(BaseModel):
    model_config = {"populate_by_name": True}
    name: str = Field(..., alias="board_name", description="The name of the new board")
    project_key: Optional[str] = Field(None, description="Optional short key for the board (e.g. 'PRJ')")
    description: Optional[str] = Field(None, description="Optional description of the board")


class CreateBoardTool(BaseTool):
    name: str = "create_board"
    description: str = "Creates a new board/project in the current organization."
    input_schema = CreateBoardParams
    output_schema = Any
    category = "domain"
    action = "create_board"
    required_roles = ["MANAGER", "SUPER_ADMIN"]
    risk_level = RiskLevel.SAFE
    is_write_action = True

    async def execute(self, params: BaseModel, current_user: dict, services: Dict[str, Any]) -> Any:
        from app.schemas.board import BoardCreate
        board_service = services.get("board_service")
        board_in = BoardCreate(name=params.name, description=params.description)
        result = await board_service.create_board(board_in, current_user)
        return {
            "status": "success",
            "action": "created",
            "message": f"Project '{result.name}' created successfully",
            "verified": _serialize({"board_id": result.id, "name": result.name}),
            "warnings": []
        }


class ArchiveBoardParams(BaseModel):
    board_id: Optional[int] = Field(None, description="ID of the board to archive")
    board_name: Optional[str] = Field(None, description="Name of the board to archive")


class ArchiveBoardTool(BaseTool):
    name: str = "archive_board"
    description: str = "Archives a board/project. Provide board_id or board_name."
    input_schema = ArchiveBoardParams
    output_schema = Any
    category = "domain"
    action = "archive_board"
    required_roles = ["MANAGER", "SUPER_ADMIN"]
    risk_level = RiskLevel.HIGH
    is_write_action = True

    async def execute(self, params: BaseModel, current_user: dict, services: Dict[str, Any]) -> Any:
        board_id = await resolve_board_id(params.board_id, params.board_name, current_user, services)
        board_service = services.get("board_service")
        await board_service.archive_project(board_id, current_user)
        return {
            "status": "success",
            "action": "archived",
            "message": f"Project archived successfully",
            "verified": {"board_id": board_id},
            "warnings": []
        }


class DeleteBoardParams(BaseModel):
    board_id: Optional[int] = Field(None, description="ID of the board to delete")
    board_name: Optional[str] = Field(None, description="Name of the board to delete")


class DeleteBoardTool(BaseTool):
    name: str = "delete_board"
    description: str = "Permanently deletes a board/project. Provide board_id or board_name."
    input_schema = DeleteBoardParams
    output_schema = Any
    category = "domain"
    action = "delete_board"
    required_roles = ["MANAGER", "SUPER_ADMIN"]
    risk_level = RiskLevel.HIGH
    is_write_action = True

    async def execute(self, params: BaseModel, current_user: dict, services: Dict[str, Any]) -> Any:
        board_id = await resolve_board_id(params.board_id, params.board_name, current_user, services)
        board_service = services.get("board_service")
        await board_service.delete_board(board_id, current_user)
        return {
            "status": "success",
            "action": "deleted",
            "message": f"Project deleted successfully",
            "verified": {"board_id": board_id},
            "warnings": []
        }


# -----------------
# Comment Tools
# -----------------


class AddCommentParams(BaseModel):
    model_config = {"populate_by_name": True}
    task_id: Optional[int] = Field(None, description="The ID of the task")
    task_name: Optional[str] = Field(None, alias="title", description="The name of the task (if ID is unknown)")
    board_name: Optional[str] = Field(None, description="Name of the board")
    content: str = Field(..., alias="comment", description="The comment content")

class AddCommentTool(BaseTool):
    name: str = "add_comment"
    description: str = "Adds a comment to a task. Provide task_id or task_name with board_name."
    input_schema = AddCommentParams
    output_schema = Any
    category = "domain"
    action = "add_comment"
    risk_level = RiskLevel.SAFE
    is_write_action = True

    async def execute(self, params: AddCommentParams, current_user: dict, services: Dict[str, Any]) -> Any:
        comment_service = services.get("comment_service")
        real_task_id = await resolve_task_id(params, current_user, services)
        
        from app.schemas.comments import CommentCreate
        comment_in = CommentCreate(content=params.content)
        result, task_row, parent_user = await comment_service.create_comment(real_task_id, comment_in, current_user)
        
        return {
            "status": "success",
            "action": "comment_added",
            "message": f"Comment added to task successfully",
            "verified": _serialize(dict(result)),
            "warnings": []
        }

class GetCommentsParams(BaseModel):
    task_id: Optional[int] = Field(None, description="ID of the task (if known)")
    task_name: Optional[str] = Field(None, description="Name of the task")
    board_name: Optional[str] = Field(None, description="Name of the board containing the task")

class GetCommentsTool(BaseTool):
    name: str = "get_comments"
    description: str = "Retrieves all comments for a specific task."
    input_schema = GetCommentsParams
    output_schema = Any
    category = "domain"
    action = "get_comments"
    risk_level = RiskLevel.SAFE
    is_write_action = False

    async def execute(self, params: GetCommentsParams, current_user: dict, services: Dict[str, Any]) -> Any:
        comment_service = services.get("comment_service")
        real_task_id = await resolve_task_id(params, current_user, services)
        
        comments = await comment_service.get_task_comments(real_task_id, current_user)
        return {
            "status": "success",
            "action": "comments_retrieved",
            "message": f"Retrieved {len(comments)} comments",
            "verified": {"comments": _serialize([dict(c) for c in comments])},
            "warnings": []
        }


