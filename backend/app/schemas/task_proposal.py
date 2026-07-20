import uuid
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator


class TaskProposalOut(BaseModel):
    """Canonical DTO representing a meeting task proposal."""
    id: str = Field(..., description="Proposal UUID")

    @field_validator("id", "meeting_session_id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v: Any) -> Any:
        if isinstance(v, uuid.UUID):
            return str(v)
        return v
    org_id: int = Field(..., description="Organization ID")
    org_name: Optional[str] = Field(default=None, description="Organization Name")
    board_id: Optional[int] = Field(default=None, description="Board ID (nullable if unassigned)")
    board_name: Optional[str] = Field(default=None, description="Board Name")
    board_confidence: Optional[float] = Field(default=None, description="Board Resolution Confidence (0-1)")
    board_source: Optional[str] = Field(default=None, description="Board Resolution Source (llm_matched, meeting_default, manager_assigned)")
    meeting_session_id: str = Field(..., description="Meeting Session UUID")
    meeting_url: Optional[str] = Field(default=None, description="Source Meeting URL")
    meeting_started_at: Optional[datetime] = Field(default=None, description="Meeting Start Time")
    title: str = Field(..., description="Proposed Task Title")
    description: Optional[str] = Field(default="", description="Proposed Task Description")
    priority: Optional[str] = Field(default="MEDIUM", description="Proposed Priority")
    due_date: Optional[datetime] = Field(default=None, description="Proposed Due Date")
    confidence_score: Optional[float] = Field(default=None, description="Extraction Confidence Score (0-1)")
    source_transcript_quote: Optional[str] = Field(default=None, description="Supporting Transcript Quote")
    status: str = Field(..., description="Proposal Status (pending, approved, rejected)")
    raw_llm_payload: Optional[Any] = Field(default=None, description="Raw LLM Payload")
    created_at: datetime = Field(..., description="Creation Timestamp")

    # Suggested Assignee Metadata
    suggested_assignee_id: Optional[int] = Field(default=None, description="Suggested Assignee User ID")
    suggested_assignee_email: Optional[str] = Field(default=None, description="Suggested Assignee Email")
    suggested_assignee_first_name: Optional[str] = Field(default=None, description="Suggested Assignee First Name")
    suggested_assignee_last_name: Optional[str] = Field(default=None, description="Suggested Assignee Last Name")
    suggested_assignee_display_name: Optional[str] = Field(default=None, description="Suggested Assignee Display Name")
    suggested_assignee_avatar_url: Optional[str] = Field(default=None, description="Suggested Assignee Avatar URL")

    # Reviewer Metadata
    reviewed_by: Optional[int] = Field(default=None, description="Reviewer User ID")
    reviewer_email: Optional[str] = Field(default=None, description="Reviewer Email")
    reviewer_first_name: Optional[str] = Field(default=None, description="Reviewer First Name")
    reviewer_last_name: Optional[str] = Field(default=None, description="Reviewer Last Name")
    reviewer_display_name: Optional[str] = Field(default=None, description="Reviewer Display Name")
    reviewer_avatar_url: Optional[str] = Field(default=None, description="Reviewer Avatar URL")
    reviewed_at: Optional[datetime] = Field(default=None, description="Review Timestamp")

    # Resulting Task Link
    created_task_id: Optional[int] = Field(default=None, description="ID of created Kanban Task Card")

    class Config:
        from_attributes = True


class TaskProposalUpdateIn(BaseModel):
    """Input payload for editing a pending proposal."""
    title: Optional[str] = Field(default=None, min_length=1, description="Updated proposal title")
    description: Optional[str] = Field(default=None, description="Updated proposal description")
    priority: Optional[str] = Field(default=None, description="Updated priority (LOW, MEDIUM, HIGH, URGENT)")
    due_date: Optional[datetime] = Field(default=None, description="Updated due date")
    suggested_assignee_id: Optional[int] = Field(default=None, description="Updated suggested assignee user ID")
    board_id: Optional[int] = Field(default=None, description="Updated target board ID override")


class TaskProposalApproveIn(BaseModel):
    """Input payload for approving a proposal."""
    note: Optional[str] = Field(default=None, description="Optional reviewer approval note")
    board_id: Optional[int] = Field(default=None, description="Target board ID override if unassigned")


class TaskProposalRejectIn(BaseModel):
    """Input payload for rejecting a proposal."""
    reason: Optional[str] = Field(default=None, description="Optional rejection reason")

