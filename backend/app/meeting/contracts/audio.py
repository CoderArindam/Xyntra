from abc import ABC, abstractmethod
from app.meeting.artifacts import MeetingRecording, ProcessedAudio


class AudioProcessor(ABC):
    """Contract for processing raw meeting audio."""

    @abstractmethod
    async def process(self, recording: MeetingRecording) -> ProcessedAudio:
        """Process, clean, and normalize the raw audio recording."""
        raise NotImplementedError
