from typing import List, Optional
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
    title: str
    description: str
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    priority: str = "medium"
    tags: List[str] = []


class TaskProposal(MeetingArtifact):
    """A mapped task proposal awaiting approval to be injected into the Kanban board."""
    extracted_task_id: str
    target_board_id: Optional[str] = None
    target_list_id: Optional[str] = None
    target_user_id: Optional[str] = None
    confidence_score: float
