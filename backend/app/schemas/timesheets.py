from datetime import date, datetime
from typing import List, Literal, Optional, Union
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator



class TimesheetResponse(BaseModel):
    id: UUID
    org_id: UUID
    user_id: UUID
    submitter_name: str
    submitter_email: str
    week_start_date: date
    week_end_date: date
    status: str
    total_hours: float
    standard_hours_per_week: float
    entry_count: int
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    approver_id: Optional[UUID] = None
    approver_name: Optional[str] = None
    approver_comment: Optional[str] = None
    member_note: Optional[str] = None

    @field_validator('id', 'org_id', 'user_id', 'approver_id', mode='before')
    @classmethod
    def parse_uuid_fields(cls, v):
        if v is None or v == '':
            return None
        if isinstance(v, UUID):
            return v
        s_val = str(v).strip()
        if s_val.isdigit():
            return UUID(f"00000000-0000-0000-0000-{int(s_val):012d}")
        try:
            return UUID(s_val)
        except Exception:
            return None

    model_config = ConfigDict(from_attributes=True)


class TimesheetEntryResponse(BaseModel):
    id: UUID
    timesheet_id: UUID
    board_id: Optional[UUID] = None
    board_name: Optional[str] = None
    task_id: Optional[UUID] = None
    task_title: Optional[str] = None
    entry_date: date
    hours: float
    entry_type: str
    description: Optional[str] = None
    is_overtime: bool

    model_config = ConfigDict(from_attributes=True)


class TimesheetAuditResponse(BaseModel):
    id: UUID
    actor_name: str
    actor_email: str
    from_status: Optional[str] = None
    to_status: str
    comment: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TimesheetDetailResponse(TimesheetResponse):
    entries: List[TimesheetEntryResponse] = []
    audit_log: List[TimesheetAuditResponse] = []


class CreateTimesheetRequest(BaseModel):
    week_start_date: date


class UpsertTimesheetEntryRequest(BaseModel):

    board_id: Optional[Union[UUID, str, int]] = None
    task_id: Optional[Union[UUID, str, int]] = None
    entry_date: date
    hours: float = Field(ge=0, le=24)
    entry_type: Literal['task', 'meeting', 'general', 'leave', 'holiday'] = 'task'
    description: Optional[str] = None

    @field_validator('board_id', 'task_id', mode='before')
    @classmethod
    def parse_optional_uuid(cls, v):
        if v is None or v == '' or v == 'general':
            return None
        if isinstance(v, UUID):
            return v
        s_val = str(v).strip()
        if s_val.isdigit():
            return UUID(f"00000000-0000-0000-0000-{int(s_val):012d}")
        try:
            return UUID(s_val)
        except Exception:
            return None




class SubmitTimesheetRequest(BaseModel):
    member_note: Optional[str] = None
    approver_id: Optional[UUID] = None

    @field_validator('approver_id', mode='before')
    @classmethod
    def parse_approver_uuid(cls, v):
        if v is None or v == '' or v == 'auto':
            return None
        if isinstance(v, UUID):
            return v
        s_val = str(v).strip()
        if s_val.isdigit():
            return UUID(f"00000000-0000-0000-0000-{int(s_val):012d}")
        try:
            return UUID(s_val)
        except Exception:
            return None


class RecallTimesheetRequest(BaseModel):
    reason: str
