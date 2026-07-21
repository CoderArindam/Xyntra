from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.schemas.activity import CanonicalActivityResponse

class DashboardTasksByStatus(BaseModel):
    todo: int = 0
    in_progress: int = 0
    review: int = 0
    done: int = 0

class DashboardKPIs(BaseModel):
    total_tasks: int = 0
    tasks_by_status: DashboardTasksByStatus
    overdue_tasks: int = 0
    total_boards: int = 0
    team_size: int = 0
    pending_proposals_count: int = 0
    active_meetings_count: int = 0

class DashboardBoardSummary(BaseModel):
    id: int
    name: str
    project_key: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    cover_gradient: Optional[str] = None
    task_count: int = 0
    completed_task_count: int = 0
    completion_percentage: float = 0.0
    overdue_count: int = 0
    member_count: int = 0
    created_at: Optional[datetime] = None

class DashboardSummaryResponse(BaseModel):
    kpis: DashboardKPIs
    boards: List[DashboardBoardSummary]
    recent_activity: List[CanonicalActivityResponse]
