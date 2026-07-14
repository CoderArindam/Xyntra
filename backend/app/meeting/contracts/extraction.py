from abc import ABC, abstractmethod
from typing import List
from app.meeting.artifacts import MeetingInsights, ExtractedTask


class TaskExtractor(ABC):
    """Contract for extracting discrete tasks from meeting insights."""

    @abstractmethod
    async def extract(self, insights: MeetingInsights) -> List[ExtractedTask]:
        """Extract task items from the canonical meeting insights."""
        raise NotImplementedError
