"""Pipeline lifecycle events for monitoring and UIs."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, Dict, Optional


class PipelineEvent(BaseModel):
    """Base class for all pipeline events."""
    event_id: str = Field(default_factory=lambda: "evt_" + datetime.utcnow().timestamp().hex())
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    meeting_id: str


class PipelineStarted(PipelineEvent):
    """Fired when the entire pipeline begins."""
    pass


class PipelineCompleted(PipelineEvent):
    """Fired when the entire pipeline finishes successfully."""
    total_duration_ms: int


class StageStarted(PipelineEvent):
    """Fired when a pipeline stage begins execution."""
    stage_name: str


class StageCompleted(PipelineEvent):
    """Fired when a pipeline stage finishes successfully."""
    stage_name: str
    duration_ms: int
    generated_artifacts: Dict[str, str] = Field(default_factory=dict)


class StageSkipped(PipelineEvent):
    """Fired when a pipeline stage is skipped (e.g., artifacts already exist)."""
    stage_name: str
    reason: str = "Artifacts already present."


class StageFailed(PipelineEvent):
    """Fired when a pipeline stage fails."""
    stage_name: str
    error: str
    will_continue: bool
