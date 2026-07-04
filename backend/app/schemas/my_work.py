from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.schemas.task import CanonicalTaskResponse

class MyWorkSummaryResponse(BaseModel):
    assigned: int
    due_today: int
    overdue: int
    completed_this_week: int
