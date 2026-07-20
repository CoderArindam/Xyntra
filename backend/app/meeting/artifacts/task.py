from typing import List, Optional, Any
from .base import MeetingArtifact


class DecisionItem(MeetingArtifact):
    """A formal decision made during the meeting."""
    description: str
    context: Optional[str] = None


class ActionItem(MeetingArtifact):
    """A raw action item extracted from the meeting."""
    description: str
    assignee_guess: Optional[str] = None
    deadline_guess: Optional[str] = None


class ExtractedTask(MeetingArtifact):
    """A well-formed task extracted by AI intended for Kanban mapping."""
    meeting_id: str = ""
    title: str
    description: str = ""
    assignee: Optional[str] = None
    suggested_assignee_id: Optional[int] = None
    due_date: Optional[str] = None
    priority: str = "medium"
    tags: List[str] = []
    confidence_score: float = 0.8
    source_transcript_quote: Optional[str] = None
    suggested_speaker_label: Optional[str] = None
    suggested_board_name: Optional[str] = None
    suggested_board_id: Optional[int] = None
    board_confidence: Optional[float] = None
    board_source: Optional[str] = None
    raw_llm_payload: Optional[Any] = None



class TaskProposal(MeetingArtifact):
    """A mapped task proposal awaiting approval to be injected into the Kanban board."""
    extracted_task_id: str
    target_board_id: Optional[str] = None
    target_list_id: Optional[str] = None
    target_user_id: Optional[str] = None
    confidence_score: float
