from pydantic import BaseModel
from typing import Optional

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None

class ChangePassword(BaseModel):
    current_password: str
    new_password: str
