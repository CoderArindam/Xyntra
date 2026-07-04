from pydantic import BaseModel, field_validator
from typing import Optional, Any, Dict
import json
from datetime import datetime

class CanonicalActivityResponse(BaseModel):
    id: int
    organization_id: int
    entity_type: str
    entity_id: int
    activity_type: str
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    actor_id: Optional[int] = None
    actor_first_name: Optional[str] = None
    actor_last_name: Optional[str] = None
    actor_avatar_url: Optional[str] = None
    actor_email: Optional[str] = None
    
    target_reference: Optional[str] = None

    @field_validator('old_value', 'new_value', 'metadata', mode='before')
    @classmethod
    def parse_json(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v
        return v
