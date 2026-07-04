from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class MarkBatchReadRequest(BaseModel):
    notification_ids: List[int]

class CanonicalNotificationResponse(BaseModel):
    id: int
    user_id: int
    is_read: bool
    created_at: datetime
    
    activity_id: int
    activity_entity_type: str
    activity_entity_id: int
    activity_type: str
    activity_target_reference: Optional[str] = None
    activity_actor_first_name: Optional[str] = None
    activity_actor_last_name: Optional[str] = None
    activity_actor_avatar_url: Optional[str] = None
