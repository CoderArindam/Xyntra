from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CommentCreate(BaseModel):
    content: str
    parent_comment_id: Optional[int] = None

class CommentResponse(BaseModel):
    id: int
    task_id: int
    content: str
    parent_comment_id: Optional[int] = None
    created_at: datetime
    
    user_id: int
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None
    user_avatar_url: Optional[str] = None
