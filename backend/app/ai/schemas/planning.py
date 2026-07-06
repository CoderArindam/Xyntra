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
    
    # New execution lifecycle fields
    current_state: str = Field(default="CREATED")
    is_cancelled: bool = Field(default=False)
    idempotency_key: Optional[str] = None
    recovery_metadata: Dict[str, Any] = Field(default_factory=dict)
    timeout_metadata: Dict[str, float] = Field(default_factory=dict)
    workspace_context_str: str = Field(default="")
    tool_cache: Dict[str, Any] = Field(default_factory=dict)
    
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
    confidence_score: float = Field(default=1.0, description="Planner's confidence score (0.0 to 1.0) in this plan")
    clarification_needed: Optional[str] = Field(None, description="If critical information is missing to create a safe plan, provide the exact question to ask the user here.")

class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"

class ExecutionStatus(str, Enum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    VALIDATING = "VALIDATING"
    WAITING_FOR_CONFIRMATION = "WAITING_FOR_CONFIRMATION"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class StepExecutionResult(BaseModel):
    step_id: str
    tool_name: str
    action: str
    status: StepStatus
    output: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ExecutionResult(BaseModel):
    execution_id: str
    status: ExecutionStatus
    step_results: List[StepExecutionResult] = Field(default_factory=list)
    completed_steps: List[str] = Field(default_factory=list)
    failed_steps: List[str] = Field(default_factory=list)
    generated_resource_ids: Dict[str, List[Any]] = Field(default_factory=dict)
    summary: str
    tool_metrics: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: int = 0
