from uuid import UUID
from typing import Optional, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator


def _parse_uuid_val(v):
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


class TimesheetPolicyResponse(BaseModel):
    org_id: UUID
    week_start_day: Literal['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    standard_hours_per_day: float
    standard_hours_per_week: float
    max_hours_per_day: float
    overtime_policy: Literal['none', 'flag_only', 'block_submission']
    submission_deadline_days: int
    allow_future_entry: bool
    allow_past_entry_days: int
    require_task_link: bool
    allow_member_recall: bool
    org_name: str
    org_slug: str

    @field_validator('org_id', mode='before')
    @classmethod
    def parse_uuids(cls, v):
        return _parse_uuid_val(v)

    model_config = ConfigDict(from_attributes=True)


class TimesheetPolicyUpdateRequest(BaseModel):
    week_start_day: Optional[Literal['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']] = None
    standard_hours_per_day: Optional[float] = Field(None, ge=0.5, le=24)
    standard_hours_per_week: Optional[float] = Field(None, ge=1, le=168)
    max_hours_per_day: Optional[float] = Field(None, ge=1, le=24)
    overtime_policy: Optional[Literal['none', 'flag_only', 'block_submission']] = None
    submission_deadline_days: Optional[int] = Field(None, ge=0, le=30)
    allow_future_entry: Optional[bool] = None
    allow_past_entry_days: Optional[int] = Field(None, ge=0, le=365)
    require_task_link: Optional[bool] = None
    allow_member_recall: Optional[bool] = None


class ApproverAssignmentResponse(BaseModel):
    id: UUID
    org_id: UUID
    approver_user_id: UUID
    approver_name: str
    approver_email: str
    assigned_by_name: str

    @field_validator('id', 'org_id', 'approver_user_id', mode='before')
    @classmethod
    def parse_uuids(cls, v):
        return _parse_uuid_val(v)

    model_config = ConfigDict(from_attributes=True)


class AssignApproverRequest(BaseModel):
    approver_user_id: UUID

    @field_validator('approver_user_id', mode='before')
    @classmethod
    def parse_uuids(cls, v):
        return _parse_uuid_val(v)


class EligibleApproverResponse(BaseModel):
    user_id: UUID
    display_name: str
    email: str
    role: str
    is_approver: Optional[bool] = False

    @field_validator('user_id', mode='before')
    @classmethod
    def parse_uuids(cls, v):
        return _parse_uuid_val(v)

    model_config = ConfigDict(from_attributes=True)


class TimesheetOrgSummaryResponse(BaseModel):
    org_id: UUID
    week_start_date: str
    total_members_who_submitted: int
    total_timesheets_submitted: int
    total_timesheets_approved: int
    total_timesheets_rejected: int
    total_timesheets_pending: int
    total_hours_logged: float
    avg_hours_per_member: float
    compliance_rate: float

    @field_validator('org_id', mode='before')
    @classmethod
    def parse_uuids(cls, v):
        return _parse_uuid_val(v)

    model_config = ConfigDict(from_attributes=True)


class TimesheetBoardHoursResponse(BaseModel):
    board_id: UUID
    board_name: str
    org_id: UUID
    week_start_date: str
    total_hours_logged: float
    member_count: int

    @field_validator('board_id', 'org_id', mode='before')
    @classmethod
    def parse_uuids(cls, v):
        return _parse_uuid_val(v)

    model_config = ConfigDict(from_attributes=True)


class TimesheetMemberSummaryResponse(BaseModel):
    user_id: UUID
    org_id: UUID
    display_name: str
    email: str
    week_start_date: str
    status: str
    total_hours: float
    is_on_time: bool

    @field_validator('user_id', 'org_id', mode='before')
    @classmethod
    def parse_uuids(cls, v):
        return _parse_uuid_val(v)

    model_config = ConfigDict(from_attributes=True)


