from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid

class RiskLevel(str, Enum):
    SAFE = "SAFE"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class ExecutionContext(BaseModel):
    """Encapsulates all scoped info for the current execution."""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    current_user: Dict[str, Any]
    conversation_id: Optional[str] = None
    request_id: Optional[str] = None
    organization_id: Optional[str] = None
    telemetry_context: Dict[str, Any] = Field(default_factory=dict)
    feature_flags: Dict[str, Any] = Field(default_factory=dict)
    
class PlanStep(BaseModel):
    id: str = Field(description="A unique identifier for the step (e.g., 'step_1')")
    description: str = Field(description="Human-readable description of what this step does")
    action: str = Field(description="The high-level abstract action to perform (e.g., 'find_project', 'create_task')")
    arguments: Dict[str, Any] = Field(description="Arguments for the action")
    expected_result: str = Field(description="What is the expected outcome of this step")

class ExecutionPlan(BaseModel):
    goal: str = Field(description="The overall goal of this execution plan")
    steps: List[PlanStep] = Field(description="Sequential steps to achieve the goal")
    estimated_duration: str = Field(description="Estimated time to complete")

class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class ExecutionStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class ExecutionResult(BaseModel):
    execution_id: str
    status: ExecutionStatus
    completed_steps: List[str] = Field(default_factory=list)
    failed_steps: List[str] = Field(default_factory=list)
    generated_resource_ids: Dict[str, List[Any]] = Field(default_factory=dict)
    summary: str
    tool_metrics: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: int = 0
