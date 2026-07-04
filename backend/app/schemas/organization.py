from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime

class OrganizationProfileResponse(BaseModel):
    id: int
    name: str
    logo_url: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    created_at: datetime
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    members_count: int
    projects_count: int

class OrganizationProfileUpdate(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
