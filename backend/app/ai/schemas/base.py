from pydantic import BaseModel

class AIResponseBase(BaseModel):
    """Base schema for all AI responses."""
    pass

class TaskExtractionResponse(AIResponseBase):
    """Example schema for extracting tasks."""
    title: str
    description: str
    priority: str
    assigned_to: str | None = None
