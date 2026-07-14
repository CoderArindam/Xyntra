from abc import ABC, abstractmethod
from typing import List
from app.meeting.artifacts import RawTranscript, NormalizedTranscript, SpeakerSegment, MeetingTranscript


class TranscriptNormalizer(ABC):
    """Contract for normalizing transcripts (e.g., stripping hallucinations, cleaning encoding)."""

    @abstractmethod
    async def normalize(self, raw: RawTranscript) -> NormalizedTranscript:
        """Clean and normalize the raw transcript."""
        raise NotImplementedError


class TranscriptBuilder(ABC):
    """Contract for merging normalized transcripts with speaker diarization."""

    @abstractmethod
    async def build(
        self, normalized: NormalizedTranscript, speakers: List[SpeakerSegment]
    ) -> MeetingTranscript:
        """Merge text segments with speaker identities to build the final meeting transcript."""
        raise NotImplementedError
