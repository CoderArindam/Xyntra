from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class InviteUserRequest(BaseModel):
    email: EmailStr
    role: str = "MEMBER"


class InvitationResponse(BaseModel):
    id: int
    email: str
    role: str
    expires_at: datetime
    created_at: datetime
    accepted_at: Optional[datetime] = None
    is_pending: Optional[bool] = None


class AcceptInvitationRequest(BaseModel):
    token: str
    password: str
    confirm_password: str
    first_name: str
    last_name: str


class InvitationDetailResponse(BaseModel):
    id: int
    organization_id: int
    org_name: str
    email: str
    role: str
    expires_at: datetime
    accepted_at: Optional[datetime] = None
