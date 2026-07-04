from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# --- Organization ---

class OrganizationCreate(BaseModel):
    """Used to register a new organization + its first SUPER_ADMIN."""
    org_name: str
    email: EmailStr
    password: str
    first_name: str
    last_name: Optional[str] = None


class OrganizationResponse(BaseModel):
    id: int
    name: str
    created_at: datetime


class OrganizationRegistrationResponse(BaseModel):
    organization: OrganizationResponse
    message: str = "Registration successful"


# --- Auth ---

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class SuccessResponse(BaseModel):
    message: str


class UserResponse(BaseModel):
    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: Optional[str] = None
    organization_id: Optional[int] = None
    is_email_verified: bool = True

class SessionResponse(BaseModel):
    id: int
    browser: Optional[str] = None
    platform: Optional[str] = None
    device_name: Optional[str] = None
    ip_address: Optional[str] = None
    last_active_at: Optional[datetime] = None
    created_at: datetime
    is_current: bool = False

class SecurityEventResponse(BaseModel):
    id: int
    action: str
    ip_address: Optional[str] = None
    details: Optional[dict] = None
    created_at: datetime

class PasswordPolicy(BaseModel):
    min_length: int
    require_uppercase: bool
    require_lowercase: bool
    require_number: bool
    require_special: bool
