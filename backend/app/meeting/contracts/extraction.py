from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict
from app.meeting.artifacts import MeetingInsights, ExtractedTask


class TaskExtractor(ABC):
    """Contract for extracting discrete tasks from meeting insights."""

    @abstractmethod
    async def extract(
        self,
        insights: Any,
        roster: Optional[Any] = None,
        boards: Optional[List[Dict[str, Any]]] = None
    ) -> List[ExtractedTask]:
        """Extract task items from canonical meeting insights, with optional roster and board context."""
        raise NotImplementedError
