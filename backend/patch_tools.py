import sys
import re

file_path = r"d:\kanban-project\backend\app\ai\tools\domain_tools.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add resolve_task_id function right before UpdateTaskParams
resolve_func = """
async def resolve_task_id(params, current_user: dict, services: Dict[str, Any]) -> int:
    if getattr(params, "task_id", None):
        return params.task_id
        
    task_name = getattr(params, "task_name", None)
    if not task_name:
        raise ValueError("Must provide either task_id or task_name")
        
    board_id = getattr(params, "board_id", None)
    board_name = getattr(params, "board_name", None)
    
    if not board_id and board_name:
        board_service = services.get("board_service")
        boards = await board_service.get_user_boards(include_archived=False, current_user=current_user)
        for b in boards:
            if b.name.lower() == board_name.lower():
                board_id = b.id
                break
                
    if not board_id:
        raise ValueError("Must provide board_id or board_name to find task by name")
        
    task_service = services.get("task_service")
    board_data = await task_service.get_board_tasks(board_id=board_id, assigned_to=None, current_user=current_user)
    
    for t in board_data.tasks:
        if t.title.lower() == task_name.lower() or task_name.lower() in t.title.lower():
            return t.id
            
    raise ValueError(f"Could not find task '{task_name}' in the specified board")

class UpdateTaskParams"""
content = content.replace("class UpdateTaskParams", resolve_func)

# 2. Update UpdateTaskParams schema
update_params_new = """class UpdateTaskParams(BaseModel):
    task_id: Optional[int] = Field(None, description="ID of the task to update")
    task_name: Optional[str] = Field(None, description="Name/title of the task (if ID is unknown)")
    board_id: Optional[int] = Field(None, description="ID of the board containing the task (required if using task_name)")
    board_name: Optional[str] = Field(None, description="Name of the board containing the task (required if using task_name)")
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = Field(None, description="Priority of the task (e.g. Low, Medium, High)")
    assignee_name: Optional[str] = Field(None, description="The first name, last name, or email of the person to assign the task to")
    due_date: Optional[str] = Field(None, description="ISO format date string for when the task is due")"""

# We use regex to replace the entire class UpdateTaskParams definition
content = re.sub(r'class UpdateTaskParams\(BaseModel\):.*?due_date: Optional\[str\] = Field\(None, description="ISO format date string for when the task is due"\)', update_params_new, content, flags=re.DOTALL)

# 3. Update UpdateTaskTool execute method to use resolve_task_id
update_exec_old = """    async def execute(self, params: BaseModel, current_user: dict, services: Dict[str, Any]) -> Any:
        task_service: TaskService = services["task_service"]
        
        column_id = None
        if params.status:
            task = await task_service.get_task(params.task_id, current_user)"""

update_exec_new = """    async def execute(self, params: BaseModel, current_user: dict, services: Dict[str, Any]) -> Any:
        task_service: TaskService = services["task_service"]
        
        real_task_id = await resolve_task_id(params, current_user, services)
        
        column_id = None
        if params.status:
            task = await task_service.get_task(real_task_id, current_user)"""
content = content.replace(update_exec_old, update_exec_new)

# Replace params.task_id with real_task_id in UpdateTaskTool
content = content.replace("await task_service.update_task(params.task_id, task_update, current_user)", "await task_service.update_task(real_task_id, task_update, current_user)")
content = content.replace("await task_service.update_task_assignee(params.task_id, assignee_update, current_user)", "await task_service.update_task_assignee(real_task_id, assignee_update, current_user)")

# 4. Append DeleteTaskTool
delete_tool = """

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
"""
content += delete_tool

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied to domain_tools.py")
