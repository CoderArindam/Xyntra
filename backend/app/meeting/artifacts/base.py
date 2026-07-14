from pydantic import BaseModel, Field
from datetime import datetime
import uuid
from typing import Dict, Any


class MeetingArtifact(BaseModel):
    """Base immutable artifact for all pipeline stages."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    meeting_id: str
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    status: str = "created"

    class Config:
        frozen = True
