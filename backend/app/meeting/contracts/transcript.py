from abc import ABC, abstractmethod
from app.meeting.artifacts import RawTranscript, NormalizedTranscript


class TranscriptNormalizer(ABC):
    """Contract for normalizing transcripts (e.g., stripping hallucinations, cleaning encoding)."""

    @abstractmethod
    async def normalize(self, raw: RawTranscript) -> NormalizedTranscript:
        """Clean and normalize the raw transcript."""
        raise NotImplementedError
