from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class BoardCreate(BaseModel):
    name: str
    project_key: Optional[str] = None

class CanonicalBoardResponse(BaseModel):
    id: int
    organization_id: int
    name: str
    project_key: str
    owner_id: Optional[int] = None
    created_at: datetime
    member_count: int
    task_count: int
