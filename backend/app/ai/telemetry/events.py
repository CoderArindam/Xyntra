from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import time
import uuid

class EventType(str, Enum):
    REQUEST_STARTED = "RequestStarted"
    REQUEST_COMPLETED = "RequestCompleted"
    SPAN_STARTED = "SpanStarted"
    SPAN_COMPLETED = "SpanCompleted"
    LLM_CALL_STARTED = "LLMCallStarted"
    LLM_CALL_COMPLETED = "LLMCallCompleted"
    TOOL_EXECUTION_STARTED = "ToolExecutionStarted"
    TOOL_EXECUTION_COMPLETED = "ToolExecutionCompleted"
    SERVICE_EXECUTION_STARTED = "ServiceExecutionStarted"
    SERVICE_EXECUTION_COMPLETED = "ServiceExecutionCompleted"
    RETRY_OCCURRED = "RetryOccurred"
    ERROR_OCCURRED = "ErrorOccurred"
    STATE_TRANSITION = "state_transition"
    TIMEOUT_OCCURRED = "timeout_occurred"
    CANCELLATION_OCCURRED = "cancellation_occurred"
    PARTIAL_EXECUTION = "partial_execution"

class TelemetryEvent(BaseModel):
    """Base class for all telemetry events."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    timestamp: float = Field(default_factory=time.time)
    request_id: Optional[str] = None
    execution_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

# Specific Event Payloads can be added as specialized metadata, 
# or we can create subclasses if we need strict schema validation for sinks.
