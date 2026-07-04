from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class TaskCreate(BaseModel):
    board_id: int
    column_id: int
    title: str
    description: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[int] = None
    due_date: Optional[datetime] = None
    reminder_at: Optional[datetime] = None

class TaskUpdate(BaseModel):
    column_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    reminder_at: Optional[datetime] = None

class TaskAssigneeUpdate(BaseModel):
    assigned_to: Optional[int] = None

class CanonicalTaskResponse(BaseModel):
    id: int
    board_id: int
    board_name: str
    organization_id: int
    task_reference: str
    column_id: int
    column_name: str
    column_type: str
    is_completed: bool
    title: str
    description: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    reminder_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    assigned_to: Optional[int] = None
    assignee_email: Optional[str] = None
    assignee_first_name: Optional[str] = None
    assignee_last_name: Optional[str] = None
    assignee_avatar_url: Optional[str] = None
    
    created_by: Optional[int] = None
    creator_email: Optional[str] = None
    creator_first_name: Optional[str] = None
    creator_last_name: Optional[str] = None
    creator_avatar_url: Optional[str] = None

class ColumnResponse(BaseModel):
    id: int
    name: str
    position: int
    column_type: str
    is_completed: bool

class BoardDataResponse(BaseModel):
    columns: List[ColumnResponse]
    tasks: List[CanonicalTaskResponse]
