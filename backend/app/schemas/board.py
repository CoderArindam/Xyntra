from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class BoardCreate(BaseModel):
    name: str
    project_key: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    cover_gradient: Optional[str] = None
    default_assignee_id: Optional[int] = None
    project_lead_id: Optional[int] = None

class CanonicalBoardResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    project_key: str
    owner_id: Optional[int] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    cover_gradient: Optional[str] = None
    default_assignee_id: Optional[int] = None
    project_lead_id: Optional[int] = None
    created_at: datetime
    archived_at: Optional[datetime] = None
    member_count: int
    task_count: int

class ProjectSettingsUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    cover_gradient: Optional[str] = None
    default_assignee_id: Optional[int] = None
    project_lead_id: Optional[int] = None

class ProjectStatistics(BaseModel):
    total_tasks: int
    completed_tasks: int
    overdue_tasks: int
    members_count: int
    columns_count: int
    last_activity: Optional[datetime] = None

class ProjectSettingsResponse(BaseModel):
    settings: CanonicalBoardResponse
    statistics: ProjectStatistics

