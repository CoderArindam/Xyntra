from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid

class ToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any]

class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    role: str = Field(..., description="user, assistant, system, tool")
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[ToolCall]] = None

class UIContext(BaseModel):
    current_page: Optional[str] = None
    board_id: Optional[int] = None
    task_id: Optional[int] = None
    selected_task_ids: Optional[List[int]] = None
    organization_id: Optional[int] = None

class AIChatRequest(BaseModel):
    conversation_id: str
    messages: List[ChatMessage]
    ui_context: Optional[UIContext] = None
    confirmed_plan: Optional[Dict[str, Any]] = None
