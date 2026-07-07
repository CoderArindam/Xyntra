from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.ai.tools.base import BaseTool
from app.ai.tools.fuzzy import resolve_board, resolve_user
from app.ai.tools.registry import tool_registry


# --- List Boards Tool ---
class ListBoardsInput(BaseModel):
    include_archived: bool = Field(default=False, description="Whether to include archived boards")


class ListBoardsTool(BaseTool):
    name = "list_boards"
    description = "List all boards/projects the current user has access to."
    input_schema = ListBoardsInput
    output_schema = Any
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
    board_name: Optional[str] = Field(None, description="The name of the board (if ID is unknown)")
    status: Optional[str] = Field(None, description="Filter tasks by status (e.g. 'In Progress', 'Done', 'To Do')")
    assignee_name: Optional[str] = Field(None, description="Filter tasks by assignee name. Use the current user's name to filter 'my tasks'.")
    priority: Optional[str] = Field(None, description="Filter tasks by priority (e.g. 'High', 'Medium', 'Low')")
    overdue: Optional[bool] = Field(None, description="If true, only return tasks that are overdue (due_date is in the past and task is not completed).")


class ListTasksTool(BaseTool):
    name = "list_tasks"
    description = "List tasks for a specific board, or across all boards if no board is specified. Can filter by status, assignee_name, priority, or overdue. Use this for ANY queries requiring listing, filtering, counting, or searching tasks."
    input_schema = ListTasksInput
    output_schema = Any
    category = "workspace"
    action = "list_tasks"
    
    async def execute(self, params: ListTasksInput, current_user: dict, services: Dict[str, Any]) -> Any:
        board_service = services.get("board_service")
        task_service = services.get("task_service")
        
        # Resolve assignee
        assigned_to = None
        if params.assignee_name:
            user_service = services.get("user_service")
            users = await user_service.get_all_users(current_user=current_user)
            match = resolve_user(params.assignee_name, users)
            if match:
                assigned_to = match.get("id")
            else:
                raise ValueError(f"Could not resolve assignee '{params.assignee_name}' to a valid user in this workspace.")
        
        # Resolve board
        board_id = params.board_id
        if not board_id and params.board_name:
            boards = await board_service.get_user_boards(include_archived=False, current_user=current_user)
            match = resolve_board(params.board_name, boards)
            if match:
                board_id = match.id
            else:
                available = ", ".join(b.name for b in boards[:10])
                raise ValueError(f"Could not find board '{params.board_name}'. Available: {available}")
        
        all_tasks = []
        
        if board_id:
            # Single board
            board_data = await task_service.get_board_tasks(board_id=board_id, assigned_to=assigned_to, current_user=current_user)
            all_tasks = board_data.tasks
        else:
            # Cross-board listing
            boards = await board_service.get_user_boards(include_archived=False, current_user=current_user)
            for b in boards:
                try:
                    board_data = await task_service.get_board_tasks(board_id=b.id, assigned_to=assigned_to, current_user=current_user)
                    for t in board_data.tasks:
                        t._board_name = b.name  # Tag with board name for display
                    all_tasks.extend(board_data.tasks)
                except Exception:
                    continue
        
        # Filter by status
        if params.status:
            from app.ai.tools.fuzzy import normalize
            status_norm = normalize(params.status)
            all_tasks = [t for t in all_tasks if status_norm in normalize(t.column_name or "")]
            
        # Filter by priority
        if params.priority:
            from app.ai.tools.fuzzy import normalize
            prio_norm = normalize(params.priority)
            all_tasks = [t for t in all_tasks if t.priority and prio_norm in normalize(t.priority)]
            
        # Filter by overdue
        if params.overdue:
            from datetime import datetime
            now = datetime.utcnow()
            all_tasks = [t for t in all_tasks if not t.is_completed and t.due_date and t.due_date.replace(tzinfo=None) < now]
        
        return {"tasks": [{
            "id": t.id,
            "title": t.title,
            "column_name": t.column_name,
            "board_name": getattr(t, '_board_name', None),
            "priority": getattr(t, 'priority', None),
            "assignee_id": t.assigned_to,
            "assignee_name": f"{t.assignee_first_name or ''} {t.assignee_last_name or ''}".strip() if t.assigned_to else None,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "is_completed": t.is_completed
        } for t in all_tasks]}


# --- Get Workspace Users Tool ---
class GetWorkspaceUsersInput(BaseModel):
    pass


class GetWorkspaceUsersTool(BaseTool):
    name = "get_workspace_users"
    description = "Get a list of all users/members in the organization."
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
    task_id: Optional[int] = Field(None, description="The ID of the task to retrieve (if known)")
    task_name: Optional[str] = Field(None, description="The name of the task to retrieve")
    board_name: Optional[str] = Field(None, description="The name of the board containing the task")


class GetTaskTool(BaseTool):
    name = "get_task"
    description = "Retrieve full details for a specific task."
    input_schema = GetTaskInput
    output_schema = Any
    category = "workspace"
    action = "get_task_details"

    async def execute(self, params: GetTaskInput, current_user: dict, services: Dict[str, Any]) -> Any:
        from app.ai.tools.domain_tools import resolve_task_id
        task_service = services.get("task_service")
        real_task_id = await resolve_task_id(params, current_user, services)
        task = await task_service.get_task(task_id=real_task_id, current_user=current_user)
        
        from app.ai.tools.domain_tools import _serialize
        return {"task": _serialize(task)}


# --- Board Summary Tool ---
class GetBoardSummaryInput(BaseModel):
    board_id: Optional[int] = Field(None, description="The ID of the board to summarize")
    board_name: Optional[str] = Field(None, description="The name of the board to summarize")


class GetBoardSummaryTool(BaseTool):
    name = "get_board_summary"
    description = "Get a summary of a board/project including task counts by status, member count, and progress."
    input_schema = GetBoardSummaryInput
    output_schema = Any
    category = "workspace"
    action = "get_board_summary"

    async def execute(self, params: GetBoardSummaryInput, current_user: dict, services: Dict[str, Any]) -> Any:
        board_service = services.get("board_service")
        task_service = services.get("task_service")
        
        board_id = params.board_id
        if not board_id and params.board_name:
            boards = await board_service.get_user_boards(include_archived=False, current_user=current_user)
            match = resolve_board(params.board_name, boards)
            if match:
                board_id = match.id
            else:
                raise ValueError(f"Could not find board '{params.board_name}'")
        
        if not board_id:
            raise ValueError("Either board_id or board_name must be provided")
        
        board_data = await task_service.get_board_tasks(board_id=board_id, assigned_to=None, current_user=current_user)
        
        # Compute stats
        total = len(board_data.tasks)
        by_status = {}
        by_priority = {}
        assigned_count = 0
        overdue_count = 0
        completed_count = 0
        
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        
        for t in board_data.tasks:
            col = t.column_name or "Unknown"
            by_status[col] = by_status.get(col, 0) + 1
            
            prio = getattr(t, 'priority', 'Medium') or 'Medium'
            by_priority[prio] = by_priority.get(prio, 0) + 1
            
            if t.assigned_to:
                assigned_count += 1
            if t.is_completed:
                completed_count += 1
            if t.due_date and t.due_date.replace(tzinfo=timezone.utc) < now and not t.is_completed:
                overdue_count += 1
        
        progress_pct = round((completed_count / total * 100), 1) if total > 0 else 0.0
        
        # Get members
        try:
            members = await board_service.get_board_members(board_id, current_user)
            member_count = len(members)
        except Exception:
            member_count = 0
        
        return {
            "board_id": board_id,
            "total_tasks": total,
            "completed_tasks": completed_count,
            "progress_percent": progress_pct,
            "overdue_tasks": overdue_count,
            "assigned_tasks": assigned_count,
            "unassigned_tasks": total - assigned_count,
            "tasks_by_status": by_status,
            "tasks_by_priority": by_priority,
            "member_count": member_count
        }


# --- Register all workspace tools ---
tool_registry.register(ListBoardsTool())
tool_registry.register(ListTasksTool())
tool_registry.register(GetWorkspaceUsersTool())
tool_registry.register(GetTaskTool())
tool_registry.register(GetBoardSummaryTool())
