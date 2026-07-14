from abc import ABC, abstractmethod
from app.meeting.artifacts import MeetingTranscript, MeetingInsights


class MeetingIntelligenceProvider(ABC):
    """Contract for extracting canonical meeting insights from the transcript."""

    @abstractmethod
    async def analyze(self, transcript: MeetingTranscript) -> MeetingInsights:
        """Analyze the transcript and generate structured meeting insights."""
        raise NotImplementedError
