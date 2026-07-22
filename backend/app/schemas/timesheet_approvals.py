from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.timesheets import TimesheetResponse


class ApprovalQueueItemResponse(TimesheetResponse):
    days_since_submitted: int
    is_overdue: bool
    boards_involved: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class ApprovalQueueSummaryResponse(BaseModel):
    pending_count: int
    approved_this_week: int
    rejected_this_week: int
    avg_hours_approved: float
    oldest_pending_days: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ApproveTimesheetRequest(BaseModel):
    comment: Optional[str] = None


class RejectTimesheetRequest(BaseModel):
    comment: str = Field(..., min_length=1, description="Mandatory rejection reason")

    @field_validator("comment")
    @classmethod
    def validate_comment_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Comment cannot be empty or blank")
        return v.strip()
