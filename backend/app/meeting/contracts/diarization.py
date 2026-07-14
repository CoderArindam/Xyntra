from abc import ABC, abstractmethod
from typing import List
from app.meeting.artifacts import ProcessedAudio, SpeakerSegment


class DiarizationProvider(ABC):
    """Contract for speaker diarization."""

    @abstractmethod
    async def diarize(self, audio: ProcessedAudio) -> List[SpeakerSegment]:
        """Identify speakers and their active timestamps in the audio."""
        raise NotImplementedError
