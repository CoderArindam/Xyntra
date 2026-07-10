from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from enum import Enum

class ThemeEnum(str, Enum):
    LIGHT = 'light'
    DARK = 'dark'
    SYSTEM = 'system'

class UserPreferencesBase(BaseModel):
    theme: ThemeEnum
    accent_color: str
    sidebar_theme: str

class UserPreferencesUpdate(BaseModel):
    theme: Optional[ThemeEnum] = None
    accent_color: Optional[str] = None
    sidebar_theme: Optional[str] = None
    sidebar_collapsed: Optional[bool] = None

class UserPreferencesResponse(UserPreferencesBase):
    id: int
    user_id: int
    sidebar_collapsed: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, extra="ignore")
