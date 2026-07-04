from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserCreateAdmin(BaseModel):
    email: EmailStr
    password: str
    role: Optional[str] = "MEMBER"

class UserRoleUpdate(BaseModel):
    role: str

class AdminUserResponse(BaseModel):
    id: int
    email: str
    role: str
    created_at: datetime

class AdminBoardResponse(BaseModel):
    id: int
    name: str
    owner_id: int
    created_at: datetime
    member_count: int

class BoardMemberAssign(BaseModel):
    user_id: int
    permission: str

class AdminBoardMemberResponse(BaseModel):
    id: int
    email: str
    role: str
    permission: str
    joined_at: datetime
