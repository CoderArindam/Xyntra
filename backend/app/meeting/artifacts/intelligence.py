from typing import List, Optional
from .base import MeetingArtifact


class MeetingInsights(MeetingArtifact):
    """The canonical AI output detailing structured meeting insights."""
    summary: str
    decisions: List[str]
    action_items: List[str]
    risks: List[str]
    blockers: List[str]
    deadlines: List[str]
    follow_ups: List[str]
    discussion_topics: List[str]
    provider: str
